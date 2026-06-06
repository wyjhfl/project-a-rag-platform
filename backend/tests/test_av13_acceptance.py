import sys
from pathlib import Path

# Make project-root scripts importable
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.scripts.run_av13_acceptance import (  # noqa: E402
    build_multimodal_components,
    build_provider_detail,
    normalize_provider_status,
    summarize_components,
)
from backend.scripts.run_provider_acceptance import (  # noqa: E402
    build_provider_summary,
    classify_provider_result,
    determine_blocker_type,
    summarize_provider_result,
)


def test_classify_provider_result():
    assert classify_provider_result(direct_passed=True, grounded_passed=True) == "accepted"
    assert classify_provider_result(direct_passed=True, grounded_passed=False) == "unstable"
    assert classify_provider_result(direct_passed=False, grounded_passed=False) == "blocked"


def test_summarize_provider_result_extracts_core_fields():
    payload = {
        "runtime": {"provider": "deepseek", "model": "deepseek-chat"},
        "checks": [
            {"name": "direct_llm_connected", "passed": True, "detail": {}},
            {
                "name": "chat_grounded_llm",
                "passed": False,
                "detail": {"accepted_attempt": None},
            },
        ],
        "critical_failures": [{"name": "chat_grounded_llm", "reason": "fallback"}],
    }

    result = summarize_provider_result(
        {"name": "deepseek_chat"},
        payload,
        returncode=1,
    )

    assert result["name"] == "deepseek_chat"
    assert result["status"] == "unstable"
    assert result["blocker_type"] == "grounded_rejection"
    assert result["direct_llm_connected"] is True
    assert result["chat_grounded_llm"] is False


def test_build_provider_summary_counts_statuses():
    summary = build_provider_summary(
        [
            {"status": "accepted", "blocker_type": "accepted"},
            {"status": "unstable", "blocker_type": "grounded_rejection"},
            {"status": "blocked", "blocker_type": "auth_invalid"},
            {"status": "blocked", "blocker_type": "config_missing"},
        ]
    )

    assert summary == {
        "provider_count": 4,
        "accepted_count": 1,
        "unstable_count": 1,
        "blocked_count": 2,
        "blocker_type_counts": {
            "accepted": 1,
            "grounded_rejection": 1,
            "auth_invalid": 1,
            "config_missing": 1,
        },
    }


def test_determine_blocker_type_distinguishes_root_causes():
    assert determine_blocker_type(status="accepted", critical_failures=[]) == "accepted"
    assert (
        determine_blocker_type(
            status="unstable",
            critical_failures=[
                {"reason": "Current runtime LLM did not produce an accepted grounded answer."}
            ],
        )
        == "grounded_rejection"
    )
    assert (
        determine_blocker_type(
            status="blocked",
            critical_failures=[{"reason": "LLM HTTP 401: invalid_api_key"}],
        )
        == "auth_invalid"
    )
    assert (
        determine_blocker_type(
            status="blocked",
            critical_failures=[{"reason": "LLM is not enabled by current runtime."}],
        )
        == "config_missing"
    )


def test_summarize_provider_result_marks_missing_config():
    payload = {
        "runtime": {"provider": "deepseek", "model": "deepseek-chat"},
        "checks": [
            {"name": "direct_llm_connected", "passed": False, "detail": {}},
            {"name": "chat_grounded_llm", "passed": False, "detail": {}},
        ],
        "critical_failures": [
            {"name": "direct_llm_connected", "reason": "LLM is not enabled by current runtime."}
        ],
    }

    result = summarize_provider_result(
        {"name": "deepseek_chat"},
        payload,
        returncode=1,
    )

    assert result["status"] == "blocked"
    assert result["blocker_type"] == "config_missing"


def test_multimodal_components_detect_blockers():
    text = (
        "milvus_api_ingest_status= 200\n"
        "milvus_api_chat_status= 200\n"
        "502 Bad Gateway\n"
        "NotImplementedError\n"
        "401 Unauthorized\n"
    )

    components = build_multimodal_components(text)
    statuses = {item["name"]: item["status"] for item in components}

    assert statuses["milvus_vector_store"] == "passed"
    assert statuses["mineru_real_pdf_parsing"] == "blocked"
    assert statuses["paddleocr_real_runtime"] == "blocked"
    assert statuses["vision_llm_real_runtime"] == "blocked"


def test_provider_detail_and_component_summary():
    assert normalize_provider_status("accepted") == "passed"
    assert "已通过 grounded 主链验收" in build_provider_detail(
        {"status": "accepted", "runtime": {"provider": "deepseek", "model": "deepseek-chat"}}
    )

    summary = summarize_components(
        [
            {"status": "passed"},
            {"status": "unstable"},
            {"status": "blocked"},
        ]
    )
    assert summary == {
        "component_count": 3,
        "passed_count": 1,
        "unstable_count": 1,
        "blocked_count": 1,
    }
