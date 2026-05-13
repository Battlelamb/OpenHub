import pytest
from fastapi import HTTPException

from app.api.routes_acn import _authenticated_agent_id, _redact_audit_payload


def test_authenticated_agent_id_uses_api_key_metadata():
    key_info = {"metadata": {"agent_id": "agent-1"}}

    assert _authenticated_agent_id(key_info) == "agent-1"


def test_authenticated_agent_id_rejects_mismatched_query_agent():
    key_info = {"metadata": {"agent_id": "agent-1"}}

    with pytest.raises(HTTPException) as exc:
        _authenticated_agent_id(key_info, "agent-2")

    assert exc.value.status_code == 403


def test_authenticated_agent_id_allows_legacy_query_fallback():
    assert _authenticated_agent_id({"metadata": {}}, "legacy-agent") == "legacy-agent"


def test_authenticated_agent_id_rejects_missing_identity():
    with pytest.raises(HTTPException) as exc:
        _authenticated_agent_id({"metadata": {}})

    assert exc.value.status_code == 403


def test_acn_audit_payload_redacts_secret_like_fields():
    redacted = _redact_audit_payload({
        "agent_id": "agent-1",
        "api_key": "oh_secret",
        "metadata": {
            "token": "turso-token",
            "allowed_capabilities": ["code_edit"],
            "nested": {"password": "hidden"},
        },
    })

    assert redacted["agent_id"] == "agent-1"
    assert redacted["api_key"] == "[REDACTED]"
    assert redacted["metadata"]["token"] == "[REDACTED]"
    assert redacted["metadata"]["nested"]["password"] == "[REDACTED]"
    assert redacted["metadata"]["allowed_capabilities"] == ["code_edit"]
