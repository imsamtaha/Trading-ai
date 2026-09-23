from scripts.atlas_test_report import build_report, redact


def test_report_is_partial_when_mt5_is_unavailable_but_required_checks_pass():
    groups = [
        {"name": "repo_tests", "status": "PASS", "required": True},
        {
            "name": "mt5_demo_runtime",
            "status": "NOT_RUN",
            "required": False,
            "reason": "desktop offline",
        },
    ]
    assert build_report("abc", groups)["overall"] == "PARTIAL"


def test_report_fails_on_safety_failure():
    groups = [{"name": "risk_safety", "status": "FAIL", "required": True}]
    assert build_report("abc", groups)["overall"] == "FAIL"


def test_redact_masks_secret_like_keys():
    assert redact({"MT5_PASSWORD": "secret", "status": "ok"}) == {
        "MT5_PASSWORD": "***REDACTED***",
        "status": "ok",
    }
