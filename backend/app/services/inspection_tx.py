import datetime
from sqlalchemy.orm import Session
from app.models.equipment import Equipment
from app.models.maintenance import InspectionRecord, InspectionRecordDetail, MaintenanceTask
from app.models.fault import FaultRecord
from app.core.exceptions import BusinessException
from app.services.state_machine import EquipmentStateMachine

class InspectionAtomicService:
    @staticmethod
    def submit_inspection(db: Session, user_id: int, payload: dict) -> dict:
        """
        单事务原子处理巡检打卡与异常联锁派单:
        1. 锁查询当前设备
        2. 写入巡检主表与逐项明细
        3. 发现异常项强制校验现场照片，并自动生成故障单
        4. 状态机联动更新设备状态为 FAULTY 或 RUNNING
        5. 正常提交推算下次维护日期
        """
        task_id = payload.get("task_id")
        equipment_id = payload["equipment_id"]
        details = payload["details"]

        equipment = db.query(Equipment).filter(
            Equipment.id == equipment_id,
            Equipment.is_deleted == False
        ).first()

        if not equipment:
            raise BusinessException(code=20005, message="目标设备不存在或已被删除")

        has_anomaly = any(item.get("is_normal") is False for item in details)

        # 1. 写入巡检总表
        inspection = InspectionRecord(
            task_id=task_id,
            equipment_id=equipment_id,
            snapshot_location_id=equipment.location_id,
            inspector_id=user_id,
            has_anomaly=has_anomaly,
            execution_start_time=payload.get("execution_start_time") or datetime.datetime.now(datetime.timezone.utc),
            execution_end_time=payload.get("execution_end_time") or datetime.datetime.now(datetime.timezone.utc),
            overall_remarks=payload.get("overall_remarks")
        )
        db.add(inspection)
        db.flush()

        generated_fault_id = None

        # 2. 逐项处理明细
        for item in details:
            is_normal = item["is_normal"]
            check_item_name = item["check_item_name"]
            evidence_file_id = item.get("evidence_file_id")
            anomaly_desc = item.get("anomaly_desc")

            # 异常项严格校验现场照片
            if not is_normal and not evidence_file_id:
                raise BusinessException(
                    code=30002,
                    message=f"检查项【{check_item_name}】判定为异常，必须上传现场照片证据！"
                )

            detail = InspectionRecordDetail(
                record_id=inspection.id,
                plan_item_id=item["plan_item_id"],
                check_item_name_snapshot=check_item_name,
                is_normal=is_normal,
                anomaly_desc=anomaly_desc,
                evidence_file_id=evidence_file_id
            )

            # 3. 联锁自动生成故障单 (如果尚无故障单，生成首个)
            if not is_normal and generated_fault_id is None:
                fault = FaultRecord(
                    fault_code=f"FLT-{equipment.equipment_code}-{int(datetime.datetime.now(datetime.timezone.utc).timestamp())}",
                    source_type="INSPECTION_AUTO",
                    equipment_id=equipment_id,
                    snapshot_location_id=equipment.location_id,
                    fault_title=f"巡检发现异常: {check_item_name}",
                    fault_desc=anomaly_desc or f"巡检打卡发现异常: {check_item_name}",
                    fault_system=equipment.equipment_type,
                    fault_part=check_item_name,
                    severity_level="MAJOR",
                    status="OPEN",
                    reported_by=user_id
                )
                db.add(fault)
                db.flush()
                generated_fault_id = fault.id
                detail.interlocked_fault_id = generated_fault_id

            db.add(detail)

        # 4. 状态联动与下次维护时间推算
        if has_anomaly:
            equipment.status = EquipmentStateMachine.transition(equipment.status, "FAULTY")
        else:
            equipment.status = EquipmentStateMachine.transition(equipment.status, "RUNNING")
            equipment.next_maintenance_date = (
                datetime.date.today() + datetime.timedelta(days=equipment.maintenance_interval_days)
            )
            # 维保完成，重置当前运行工时计数，进入下一轮工时周期
            equipment.current_operating_hours = 0.0

        # 5. 更新任务状态及工单完成记录
        if task_id:
            task = db.query(MaintenanceTask).filter(MaintenanceTask.id == task_id).first()
            if task:
                task.status = "COMPLETED"
                task.completed_at = datetime.datetime.now(datetime.timezone.utc)
                if payload.get("work_order_notes"):
                    task.work_order_notes = payload.get("work_order_notes")
                if payload.get("completion_proof_file_ids"):
                    task.completion_proof_file_ids = payload.get("completion_proof_file_ids")

        db.commit()

        return {
            "inspection_id": inspection.id,
            "has_anomaly": has_anomaly,
            "interlocked_fault_id": generated_fault_id,
            "message": "巡检打卡成功，已联锁生成故障工单" if has_anomaly else "巡检打卡成功，设备运行正常"
        }
