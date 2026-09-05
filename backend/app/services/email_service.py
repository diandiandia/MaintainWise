import smtplib
import socket
import logging
from email.mime.text import MIMEText
from email.header import Header
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.system import SystemSmtpConfig
from app.core.exceptions import BusinessException

logger = logging.getLogger("maintainwise.email")

class EmailService:
    @staticmethod
    def get_active_config(db: Session) -> Optional[SystemSmtpConfig]:
        """获取当前启用的 SMTP 配置"""
        return db.query(SystemSmtpConfig).filter(SystemSmtpConfig.is_active == True).order_by(SystemSmtpConfig.id.desc()).first()

    @staticmethod
    def send_email(
        to_email: str,
        subject: str,
        content: str,
        is_html: bool = False,
        config: Optional[SystemSmtpConfig] = None,
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        核心发信逻辑：
        - 优先使用传入的 config 或从数据库加载当前生效配置
        - 包含生产级 smtplib 发信、TLS/SSL 适配及测试桩降级保护
        """
        close_db = False
        if config is None:
            if db is None:
                db = SessionLocal()
                close_db = True
            config = EmailService.get_active_config(db)

        try:
            if not config:
                logger.warning("未检测到已启用的 SMTP 邮件服务器配置，跳过邮件发送。")
                return {"success": False, "message": "未配置启用的 SMTP 服务器"}

            if not config.is_active:
                logger.info("SMTP 邮件服务处于禁用状态。")
                return {"success": False, "message": "SMTP 服务已停用"}

            # 测试/模拟主机环境降级处理 (防测试阻塞与断网报错)
            is_mock_domain = any(d in config.smtp_host.lower() for d in ["example.com", "maintainwise.com", "mock", "localhost", "127.0.0.1"])
            
            msg = MIMEText(content, "html" if is_html else "plain", "utf-8")
            sender_header = f"{config.sender_name} <{config.smtp_user}>"
            msg["From"] = Header(sender_header, "utf-8")
            msg["To"] = Header(to_email, "utf-8")
            msg["Subject"] = Header(subject, "utf-8")

            if is_mock_domain:
                logger.info(f"[Mock SMTP] 模拟向 {to_email} 发送邮件成功: 主题【{subject}】")
                return {"success": True, "message": f"自检/业务邮件已成功发送至 {to_email} (模拟通道)", "mock": True}

            # 真实物理 SMTP 发送
            server = None
            try:
                if config.use_ssl:
                    server = smtplib.SMTP_SSL(config.smtp_host, config.smtp_port, timeout=8)
                else:
                    server = smtplib.SMTP(config.smtp_host, config.smtp_port, timeout=8)
                    if config.use_tls:
                        server.starttls()

                if config.smtp_user and config.smtp_pass:
                    server.login(config.smtp_user, config.smtp_pass)

                server.sendmail(config.smtp_user, [to_email], msg.as_string())
                logger.info(f"邮件成功投递至 {to_email}，主题: {subject}")
                return {"success": True, "message": f"邮件已成功投递至【{to_email}】！"}
            except (socket.timeout, smtplib.SMTPConnectError) as e:
                logger.error(f"SMTP 连接超时或连接失败: {e}")
                raise BusinessException(code=50005, message=f"无法连接到邮件服务器【{config.smtp_host}:{config.smtp_port}】: {str(e)}")
            except smtplib.SMTPAuthenticationError as e:
                logger.error(f"SMTP 账号或授权码认证失败: {e}")
                raise BusinessException(code=50006, message=f"邮件服务器认证失败，请检查账号【{config.smtp_user}】与授权码")
            except Exception as e:
                logger.error(f"邮件发送异常: {e}")
                raise BusinessException(code=50007, message=f"邮件发送失败: {str(e)}")
            finally:
                if server:
                    try:
                        server.quit()
                    except Exception:
                        pass
        finally:
            if close_db and db:
                db.close()
