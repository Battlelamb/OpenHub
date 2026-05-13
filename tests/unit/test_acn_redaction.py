import pytest
from app.api.routes_acn import _redact_audit_payload

def test_redact_audit_payload_dict():
    payload = {
        "agent_name": "test-agent",
        "api_key": "secret-key-123",
        "token": "bearer-1234",
        "github_pat": "ghp_12345",
        "nested": {
            "password": "password123",
            "safe_value": "hello"
        }
    }
    
    redacted = _redact_audit_payload(payload)
    
    assert redacted["agent_name"] == "test-agent"
    assert redacted["api_key"] == "[REDACTED]"
    assert redacted["token"] == "[REDACTED]"
    assert redacted["nested"]["password"] == "[REDACTED]"
    assert redacted["nested"]["safe_value"] == "hello"

def test_redact_audit_payload_list():
    payload = [
        {"token": "my-secret"},
        "normal string",
        {"safe": "data"}
    ]
    
    redacted = _redact_audit_payload(payload)
    
    assert redacted[0]["token"] == "[REDACTED]"
    assert redacted[1] == "normal string"
    assert redacted[2]["safe"] == "data"

def test_redact_audit_payload_values_regex():
    payload = {
        "safe_key1": "Auth is Bearer xyz123-abc",
        "safe_key2": "My key is sk-abcdefghijklmnopqrstuvwxyz12345",
        "safe_key3": "Commit token: ghp_123456789012345678901234567890123456",
        "normal": "This is a normal string without any secrets"
    }
    
    redacted = _redact_audit_payload(payload)
    
    assert "Bearer" not in redacted["safe_key1"]
    assert "[REDACTED]" in redacted["safe_key1"]
    
    assert "sk-" not in redacted["safe_key2"]
    assert "[REDACTED]" in redacted["safe_key2"]
    
    assert "ghp_" not in redacted["safe_key3"]
    assert "[REDACTED]" in redacted["safe_key3"]
    
    assert redacted["normal"] == "This is a normal string without any secrets"

