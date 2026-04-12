"""
TEST-02: Unit tests for the CapabilityMatcher.

Covers:
- Exact match (single + multi capability)
- Partial match scoring
- No match (below min_score / zero overlap)
- Best-agent selection across competing agents
- Empty-capabilities edge case
- Case-insensitive matching
"""
from uuid import uuid4

import pytest

from app.database.connection import get_database
from app.models.agents import AgentCreate, AgentStatus
from app.services.agent_service import AgentService
from app.services.capability_matcher import CapabilityMatch, CapabilityMatcher


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _unique_name(prefix: str) -> str:
    """Return a name unlikely to collide with other tests (UUID suffix)."""
    return f"{prefix}-{uuid4().hex[:8]}"


def _register_agent(capabilities: list[str], prefix: str = "matcher-agent"):
    """Register an agent through the real AgentService (status=ONLINE)."""
    service = AgentService(get_database())
    return service.register_agent(
        AgentCreate(
            agent_name=_unique_name(prefix),
            capabilities=capabilities,
            description="capability matcher unit test fixture",
        )
    )


@pytest.fixture
def matcher(test_client):
    """CapabilityMatcher backed by the real (tempfile) test database.

    The ``test_client`` fixture is consumed to guarantee that app lifespan
    has run and all tables exist, even though the tests do not make HTTP
    calls. Without it the ``agents`` table is not guaranteed to be present.
    """
    return CapabilityMatcher(get_database())


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_exact_match_single_capability(matcher):
    """Agent with ['python'] matches required ['python'] at score 1.0."""
    agent = _register_agent(["python"])

    result = matcher.find_best_agent(["python"], min_score=0.5)

    assert result is not None
    assert isinstance(result, CapabilityMatch)
    assert result.match_score == 1.0
    assert "python" in result.matched_capabilities
    assert result.missing_capabilities == []
    # The returned agent must be one we just registered or another ONLINE
    # agent with "python" - assert the score is maximal regardless.
    assert result.agent.id is not None


def test_exact_match_multiple_capabilities(matcher):
    """Agent with a superset of the requested caps scores 1.0."""
    _register_agent(["python", "testing", "docker"], prefix="multi-cap")

    result = matcher.find_best_agent(["python", "testing"], min_score=0.5)

    assert result is not None
    assert result.match_score == 1.0
    assert set(result.matched_capabilities) >= {"python", "testing"}
    assert result.missing_capabilities == []


def test_partial_match(matcher):
    """Agent with half the required capabilities scores ~0.5."""
    _register_agent(["rust"], prefix="rust-only")

    # Pick a cap pair where we know only one is covered by the fixture
    # and nothing else registered has 'rust-unique-xyz'.
    result = matcher.find_best_agent(
        ["rust", "rust-unique-xyz"],
        min_score=0.3,
    )

    assert result is not None
    # Partial match must be strictly less than 1.0 and greater than 0.0.
    assert 0.0 < result.match_score < 1.0
    assert "rust" in result.matched_capabilities
    assert "rust-unique-xyz" in result.missing_capabilities


def test_no_match_returns_none(matcher):
    """When no registered agent has any requested capability, result is None."""
    # Register an agent with unrelated capabilities only.
    _register_agent(["totally-isolated-cap-aaa"], prefix="isolated")

    # Ask for a capability string no fixture could ever have registered.
    result = matcher.find_best_agent(
        [f"nonexistent-cap-{uuid4().hex[:10]}"],
        min_score=0.5,
    )

    assert result is None


def test_best_agent_selection(matcher):
    """When two agents match with different scores, the higher scorer wins."""
    # Use unique capability strings so prior-test fixtures cannot compete.
    tag = uuid4().hex[:6]
    cap_a = f"skill-{tag}-a"
    cap_b = f"skill-{tag}-b"

    weak = _register_agent([cap_a], prefix="weak")
    strong = _register_agent([cap_a, cap_b], prefix="strong")

    result = matcher.find_best_agent([cap_a, cap_b], min_score=0.3)

    assert result is not None
    # Strong agent matches 2/2, weak agent only 1/2.
    assert result.match_score == 1.0
    assert result.agent.id == strong.id
    assert result.agent.id != weak.id


def test_empty_required_capabilities_returns_none(matcher):
    """Empty required list - matcher has nothing to score and returns None."""
    # Guarantee at least one ONLINE agent exists so the early-exit is
    # the "no required caps" branch, not "no agents".
    _register_agent(["python"], prefix="guard")

    result = matcher.find_best_agent([], min_score=0.0)

    assert result is None


def test_case_insensitive_matching(matcher):
    """Required caps in uppercase still match an agent registered lowercase."""
    tag = uuid4().hex[:6]
    cap_lower = f"pycase{tag}"

    agent = _register_agent([cap_lower], prefix="casefix")

    result = matcher.find_best_agent([cap_lower.upper()], min_score=0.5)

    assert result is not None
    assert result.match_score == 1.0
    # Matched capability is stored lowercase by the matcher.
    assert cap_lower in result.matched_capabilities
    assert result.agent.id == agent.id
