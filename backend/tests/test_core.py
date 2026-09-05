import pytest
from app.core.security import hash_password, verify_password, create_access_token, decode_access_token
from app.core.redis import redis_client
from app.core.exceptions import BusinessException

def test_password_hashing():
    raw = "MaintainWiseAdmin@2026"
    hashed = hash_password(raw)
    assert hashed != raw
    assert verify_password(raw, hashed) is True
    assert verify_password("WrongPassword", hashed) is False

def test_jwt_token_flow():
    payload = {"sub": "1", "role": "ADMIN", "fcp": True}
    token = create_access_token(payload)
    decoded = decode_access_token(token)
    assert decoded["sub"] == "1"
    assert decoded["role"] == "ADMIN"
    assert decoded["fcp"] is True

def test_redis_mock_operations():
    redis_client.set("test_key", "test_value")
    assert redis_client.get("test_key") == "test_value"
    redis_client.delete("test_key")
    assert redis_client.get("test_key") is None

def test_business_exception():
    exc = BusinessException(code=10001, message="账户已锁定", status_code=403)
    assert exc.code == 10001
    assert exc.status_code == 403
    assert exc.message == "账户已锁定"
