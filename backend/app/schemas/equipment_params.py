from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, Literal
import ipaddress

class BaseEquipmentParamSchema(BaseModel):
    extra_params: Optional[Dict[str, Any]] = Field(default_factory=dict)

# 1. PLC 专有参数强校验
class PLCEquipmentParamSchema(BaseEquipmentParamSchema):
    cpu_model: str = Field(..., min_length=2, max_length=64)
    ip_address: str = Field(..., description="IPv4地址")
    comm_protocol: Literal["PROFINET", "MODBUS_TCP", "ETHERNET_IP", "OPC_UA", "MPI"] = Field(...)
    io_points_spec: str = Field(..., min_length=2, max_length=128)
    firmware_version: Optional[str] = None

    @field_validator("ip_address")
    @classmethod
    def validate_ip(cls, v: str) -> str:
        try:
            ipaddress.IPv4Address(v)
        except ValueError:
            raise ValueError(f"【{v}】不是合法的IPv4地址")
        return v

# 2. 风机专有参数强校验
class FanEquipmentParamSchema(BaseEquipmentParamSchema):
    air_volume_m3h: float = Field(..., gt=0)
    air_pressure_pa: float = Field(..., gt=0)
    rated_power_kw: float = Field(..., gt=0)
    rated_speed_rpm: int = Field(..., gt=0, le=30000)
    drive_type: Literal["DIRECT", "BELT", "COUPLING"] = Field(...)

# 3. 电机专有参数强校验
class MotorEquipmentParamSchema(BaseEquipmentParamSchema):
    rated_power_kw: float = Field(..., gt=0)
    rated_voltage_v: float = Field(..., gt=0)
    rated_current_a: float = Field(..., gt=0)
    rated_speed_rpm: int = Field(..., gt=0, le=10000)
    insulation_class: Literal["A", "E", "B", "F", "H", "C"] = Field(...)
    protection_level: Literal["IP54", "IP55", "IP65", "IP67"] = Field(...)

# 4. 变频器专有参数强校验
class InverterEquipmentParamSchema(BaseEquipmentParamSchema):
    rated_power_kw: float = Field(..., gt=0)
    input_voltage_v: float = Field(..., gt=0)
    rated_output_current_a: float = Field(..., gt=0)
    control_mode: Literal["V_F", "VECTOR_OPEN_LOOP", "VECTOR_CLOSED_LOOP", "TORQUE"] = Field(...)
    comm_interface: Literal["MODBUS", "CANOPEN", "PROFINET", "PROFIBUS_DP"] = Field(...)

# 5. 传感器专有参数强校验
class SensorEquipmentParamSchema(BaseEquipmentParamSchema):
    measurement_type: Literal["TEMPERATURE", "PRESSURE", "FLOW", "LEVEL", "PHOTOELECTRIC", "PROXIMITY"] = Field(...)
    measurement_range: str = Field(..., min_length=1, max_length=64)
    output_signal_type: Literal["4-20mA", "0-10V", "0-5V", "PNP", "NPN", "RS485", "IO-Link"] = Field(...)
    accuracy_class: str = Field(..., min_length=1, max_length=32)

# 6. HMI 触摸屏专有参数
class HMIEquipmentParamSchema(BaseEquipmentParamSchema):
    screen_size_inch: float = Field(..., gt=0, le=50)
    resolution: str = Field(..., min_length=3, max_length=32)
    comm_ports: str = Field(..., min_length=2, max_length=128)

# 7. 伺服驱动器专有参数
class ServoEquipmentParamSchema(BaseEquipmentParamSchema):
    rated_power_kw: float = Field(..., gt=0)
    rated_torque_nm: float = Field(..., gt=0)
    encoder_type: Literal["ABSOLUTE", "INCREMENTAL", "RESOLVER"] = Field(...)
    bus_protocol: Literal["ETHERCAT", "PROFINET", "CANOPEN"] = Field(...)

# 8. 液压元件专有参数
class HydraulicEquipmentParamSchema(BaseEquipmentParamSchema):
    rated_pressure_mpa: float = Field(..., gt=0)
    rated_flow_lmin: float = Field(..., gt=0)
    medium_grade: str = Field(..., min_length=2, max_length=64)

# 9. 气动元件专有参数
class PneumaticEquipmentParamSchema(BaseEquipmentParamSchema):
    pressure_range_mpa: str = Field(..., min_length=2, max_length=32)
    flow_rate_lmin: float = Field(..., gt=0)

# 10. 输送设备专有参数
class ConveyorEquipmentParamSchema(BaseEquipmentParamSchema):
    linear_speed_mmin: float = Field(..., gt=0)
    belt_width_mm: float = Field(..., gt=0)
    max_load_kg: float = Field(..., gt=0)

# 11. 其他通用参数
class OtherEquipmentParamSchema(BaseEquipmentParamSchema):
    pass
