from scripts.run_av24_provider_comparison import rank_providers, summarize_provider_cases


def test_summarize_provider_cases_computes_rates():
    summary = summarize_provider_cases(
        [
            {
                "llm_used": True,
                "citation_count": 2,
                "expected_hit_count": 3,
                "expected_term_count": 4,
                "estimated_tokens": 100,
                "elapsed_ms": 1000,
                "insufficient": False,
                "safety_warning": False,
            },
            {
                "llm_used": False,
                "citation_count": 0,
                "expected_hit_count": 1,
                "expected_term_count": 4,
                "estimated_tokens": 60,
                "elapsed_ms": 500,
                "insufficient": True,
                "safety_warning": False,
            },
        ]
    )

    assert summary["llm_used_rate"] == 0.5
    assert summary["citation_case_rate"] == 0.5
    assert summary["expected_hit_rate"] == 0.5
    assert summary["avg_estimated_tokens"] == 80
    assert summary["insufficient_count"] == 1


def test_rank_providers_prefers_grounded_quality_then_lower_tokens():
    ranking = rank_providers(
        [
            {
                "name": "a",
                "summary": {
                    "llm_used_rate": 1,
                    "expected_hit_rate": 0.8,
                    "citation_case_rate": 1,
                    "avg_estimated_tokens": 300,
                    "avg_latency_ms": 100,
                },
            },
            {
                "name": "b",
                "summary": {
                    "llm_used_rate": 1,
                    "expected_hit_rate": 0.8,
                    "citation_case_rate": 1,
                    "avg_estimated_tokens": 200,
                    "avg_latency_ms": 120,
                },
            },
        ]
    )

    assert ranking[0]["name"] == "b"
