import json
import hashlib
from typing import List, Dict
from sqlalchemy.orm import Session
from app.models.knowledge import KnowledgeArticle
from app.core.redis import redis_client

class RecommendationEngine:
    SIMILARITY_THRESHOLD = 0.60 # 最低置信度阈值 60%

    @classmethod
    def get_similar_cases(
        cls, db: Session, equipment_type: str, model_spec: str, fault_desc: str, fault_part: str = ""
    ) -> List[Dict]:
        clean_text = fault_desc.strip().lower()
        if len(clean_text) < 2:
            return []

        # 1. 检查 Redis 缓存
        cache_key = f"rec:{equipment_type}:{hashlib.md5(clean_text.encode()).hexdigest()}"
        cached = redis_client.get(cache_key)
        if cached is not None:
            try:
                return json.loads(cached)
            except Exception:
                pass

        # 2. 第一阶段：元数据过滤候选集
        candidates = db.query(KnowledgeArticle).filter(
            KnowledgeArticle.is_deleted == False
        )
        if equipment_type:
            candidates = candidates.filter(KnowledgeArticle.equipment_type == equipment_type)
        candidate_list = candidates.limit(50).all()

        # 3. 第二阶段：分词与多维加权打分
        # 提取当前输入词集
        input_tokens = set(clean_text.replace("，", " ").replace("。", " ").replace("、", " ").split())
        scored = []

        for article in candidate_list:
            art_text = (article.fault_phenomenon + " " + article.fault_title).lower()
            art_tokens = set(art_text.replace("，", " ").replace("。", " ").replace("、", " ").split())

            # 计算 Jaccard / Token 重合度作为文本相似度
            if input_tokens and art_tokens:
                intersection = len(input_tokens & art_tokens)
                union = len(input_tokens | art_tokens)
                s_text = intersection / union if union > 0 else 0.0
            else:
                s_text = 0.0

            # 字符级补充相似度 (针对无分词的连贯中文，如包含关键词)
            for tok in input_tokens:
                if len(tok) >= 2 and tok in art_text:
                    s_text = max(s_text, 0.70)

            # 型号完全匹配
            i_model = 1.0 if article.equipment_model.lower() == model_spec.lower() else (
                0.5 if model_spec.lower() in article.equipment_model.lower() else 0.0
            )

            # 故障部件匹配
            i_part = 0.0
            if fault_part and article.fault_system:
                i_part = 1.0 if article.fault_system.lower() == fault_part.lower() else (
                    0.5 if fault_part.lower() in article.fault_system.lower() or article.fault_system.lower() in fault_part.lower() else 0.0
                )

            i_featured = 1.0 if article.is_featured else 0.0

            # 权重打分公式: Score = 0.5*S_text + 0.2*I_model + 0.2*I_part + 0.1*I_featured
            final_score = (0.50 * s_text) + (0.20 * i_model) + (0.20 * i_part) + (0.10 * i_featured)

            if final_score >= cls.SIMILARITY_THRESHOLD:
                scored.append({
                    "article_id": article.id,
                    "title": article.fault_title,
                    "match_score": round(final_score * 100, 1),
                    "root_cause": article.root_cause,
                    "solution_steps": article.solution_steps,
                    "is_featured": article.is_featured
                })

        scored.sort(key=lambda x: x["match_score"], reverse=True)
        top_cases = scored[:3]

        # 4. 写入缓存 (无结果写入空数组防击穿 TTL=60s，有结果 TTL=600s)
        ttl = 600 if top_cases else 60
        redis_client.setex(cache_key, ttl, json.dumps(top_cases))

        return top_cases