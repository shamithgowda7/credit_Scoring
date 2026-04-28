"""
API Test Script — validates the scoring API end-to-end.
=======================================================
Run the API first:   uvicorn api.main:app --reload
Then run this:       python api/test_api.py
"""

import json
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("ERROR: 'requests' not installed. Run: pip install requests")
    sys.exit(1)

BASE_URL = "http://localhost:8000"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PASS = 0
FAIL = 0


def check(name: str, condition: bool, detail: str = ""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [PASS] {name}{f'  ({detail})' if detail else ''}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name}{f'  ({detail})' if detail else ''}")


def test_health():
    print("\n--- Test: GET /health ---")
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        check("Status 200", r.status_code == 200, f"got {r.status_code}")
        data = r.json()
        check("model_loaded is True", data.get("model_loaded") is True)
        check("feature_names has 6 items", len(data.get("feature_names", [])) == 6)
        check("demo_users_count > 0", data.get("demo_users_count", 0) > 0)
    except requests.ConnectionError:
        print("  [FAIL] Cannot connect to API. Is it running?")
        return False
    return True


def test_score_valid():
    print("\n--- Test: POST /score (valid input) ---")
    payload = {
        "features": {
            "income_mean": 0.55,
            "income_cv": 0.15,
            "utility_rate": 0.90,
            "dti_final": 0.30,
            "employment_status": 1,
            "shock_total": 0.0,
        }
    }
    r = requests.post(f"{BASE_URL}/score", json=payload, timeout=5)
    check("Status 200", r.status_code == 200, f"got {r.status_code}")
    data = r.json()

    check("score is int", isinstance(data.get("score"), int))
    check("score in 300-900", 300 <= data.get("score", 0) <= 900, f"score={data.get('score')}")
    check("probability in 0-1", 0 <= data.get("probability", -1) <= 1)
    check("decision is valid",
          data.get("decision") in ["DECLINE", "NANO_CREDIT", "STANDARD"],
          f"decision={data.get('decision')}")
    check("risk_tier is valid",
          data.get("risk_tier") in ["High", "Medium", "Low"],
          f"risk_tier={data.get('risk_tier')}")
    check("contributions has 6 keys", len(data.get("contributions", {})) == 6)
    check("intercept is float", isinstance(data.get("intercept"), (int, float)))

    print(f"\n  Response: score={data['score']}, decision={data['decision']}, "
          f"risk={data['risk_tier']}, P(default)={data['probability']:.4f}")


def test_score_missing_feature():
    print("\n--- Test: POST /score (missing feature -> 400) ---")
    payload = {
        "features": {
            "income_mean": 0.55,
            "income_cv": 0.15,
            # missing utility_rate, dti_final, employment_status, shock_total
        }
    }
    r = requests.post(f"{BASE_URL}/score", json=payload, timeout=5)
    check("Status 400", r.status_code == 400, f"got {r.status_code}")
    check("Error mentions missing features", "Missing" in r.json().get("detail", ""))


def test_score_high_risk():
    print("\n--- Test: POST /score (high-risk profile) ---")
    payload = {
        "features": {
            "income_mean": 0.15,
            "income_cv": 0.50,
            "utility_rate": 0.25,
            "dti_final": 0.80,
            "employment_status": 0,
            "shock_total": 5.0,
        }
    }
    r = requests.post(f"{BASE_URL}/score", json=payload, timeout=5)
    data = r.json()
    check("Status 200", r.status_code == 200)
    check("Score < 500 (high risk)", data.get("score", 999) < 500,
          f"score={data.get('score')}")
    check("Decision is DECLINE or NANO_CREDIT",
          data.get("decision") in ["DECLINE", "NANO_CREDIT"])

    print(f"  Response: score={data['score']}, decision={data['decision']}")


def test_score_low_risk():
    print("\n--- Test: POST /score (low-risk profile) ---")
    payload = {
        "features": {
            "income_mean": 0.75,
            "income_cv": 0.08,
            "utility_rate": 0.95,
            "dti_final": 0.15,
            "employment_status": 1,
            "shock_total": 0.0,
        }
    }
    r = requests.post(f"{BASE_URL}/score", json=payload, timeout=5)
    data = r.json()
    check("Status 200", r.status_code == 200)
    check("Score > 650 (low risk)", data.get("score", 0) > 650,
          f"score={data.get('score')}")
    check("Decision is STANDARD or NANO_CREDIT",
          data.get("decision") in ["STANDARD", "NANO_CREDIT"])

    print(f"  Response: score={data['score']}, decision={data['decision']}")


def test_demo_users():
    print("\n--- Test: GET /demo-users ---")
    r = requests.get(f"{BASE_URL}/demo-users", timeout=5)
    check("Status 200", r.status_code == 200, f"got {r.status_code}")
    data = r.json()
    check("Has users list", "users" in data)
    check("12 demo users", data.get("count", 0) == 12, f"count={data.get('count')}")

    if data.get("users"):
        user = data["users"][0]
        check("User has name", "name" in user)
        check("User has features", "features" in user)
        check("User has expected_score", "expected_score" in user)


def test_score_demo_user():
    print("\n--- Test: POST /score-demo/1 ---")
    r = requests.post(f"{BASE_URL}/score-demo/1", timeout=5)
    check("Status 200", r.status_code == 200, f"got {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        check("Returns score", "score" in data)
        check("Returns contributions", "contributions" in data)


def test_feature_info():
    print("\n--- Test: GET /feature-info ---")
    r = requests.get(f"{BASE_URL}/feature-info", timeout=5)
    check("Status 200", r.status_code == 200)
    data = r.json()
    check("Has features dict", "features" in data)
    check("Has 6 feature descriptions", len(data.get("features", {})) == 6)


def main():
    print("=" * 60)
    print("  Credit Scoring API — Integration Tests")
    print("=" * 60)

    # Check connectivity first
    if not test_health():
        print("\n  FATAL: API not reachable. Start it with:")
        print("    uvicorn api.main:app --reload")
        sys.exit(1)

    test_score_valid()
    test_score_missing_feature()
    test_score_high_risk()
    test_score_low_risk()
    test_demo_users()
    test_score_demo_user()
    test_feature_info()

    # Summary
    total = PASS + FAIL
    print(f"\n{'=' * 60}")
    print(f"  RESULTS: {PASS}/{total} passed, {FAIL} failed")
    print(f"{'=' * 60}")

    if FAIL > 0:
        sys.exit(1)
    else:
        print("  ALL TESTS PASSED!")


if __name__ == "__main__":
    main()
