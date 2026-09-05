import pytest
from pydantic import ValidationError
from app.schemas.equipment_params import PLCEquipmentParamSchema, FanEquipmentParamSchema, MotorEquipmentParamSchema
from app.schemas.fault import FaultResolveRequest

def test_plc_param_validation_success():
    data = {
        "cpu_model": "S7-1200",
        "ip_address": "192.168.1.100",
        "comm_protocol": "PROFINET",
        "io_points_spec": "14DI/10DO"
    }
    schema = PLCEquipmentParamSchema(**data)
    assert schema.ip_address == "192.168.1.100"

def test_plc_param_validation_invalid_ip():
    data = {
        "cpu_model": "S7-1200",
        "ip_address": "999.999.999.999",
        "comm_protocol": "PROFINET",
        "io_points_spec": "14DI/10DO"
    }
    with pytest.raises(ValidationError):
        PLCEquipmentParamSchema(**data)

def test_fan_param_validation_negative_value():
    data = {
        "air_volume_m3h": -500.0, # 负数风量应该被拦截
        "air_pressure_pa": 1200.0,
        "rated_power_kw": 15.0,
        "rated_speed_rpm": 1450,
        "drive_type": "BELT"
    }
    with pytest.raises(ValidationError):
        FanEquipmentParamSchema(**data)

def test_fault_resolve_schema_validation():
    # 缺少详细根因和步骤
    with pytest.raises(ValidationError):
        FaultResolveRequest(root_cause="坏了", solution_steps="换了")
    
    valid = FaultResolveRequest(
        root_cause="由于长期高温运转导致轴承润滑脂变质碳化",
        solution_steps="1. 拆卸清洗轴承箱；2. 更换SKF 6205轴承；3. 重新加注二硫化钼耐高温润滑脂"
    )
    assert len(valid.root_cause) >= 5
    assert len(valid.solution_steps) >= 5
