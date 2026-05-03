"""
Integration Test — LLM Assessment Flow (Mock Mode)
====================================================
Tests the full end-to-end flow using mock LLM mode:
  1. Start assessment → get first question
  2. Answer 4 questions via /submit-answer
  3. Verify CONFIDENT_EXTRACTION with auto-scoring
  4. Verify session is finalized in DB
  5. Verify /sessions-summary returns data
"""

import requests
import json
import sys

BASE = "http://127.0.0.1:8000"

def test_health():
    r = requests.get(f"{BASE}/health")
    assert r.status_code == 200
    d = r.json()
    assert d["status"] == "healthy"
    assert "llm_mode" in d
    print(f"  ✓ Health OK — LLM mode: {d['llm_mode']}")
    return d

def test_start_assessment():
    r = requests.post(f"{BASE}/start-assessment", json={
        "name": "Test Applicant",
        "bank_context": "Ravi is a 28-year-old gig worker earning 15k-35k/month."
    })
    assert r.status_code == 200
    d = r.json()
    assert "session_id" in d
    assert d["result"]["status"] == "ASK_QUESTION"
    assert "question_text" in d["result"]
    assert "options" in d["result"]
    print(f"  ✓ Start assessment OK — session: {d['session_id'][:8]}...")
    print(f"    Q1: {d['result']['question_text'][:60]}...")
    return d

def test_submit_answers(session_id, first_question):
    """Submit answers until extraction or max questions."""
    current_q = first_question
    score_result = None
    
    for i in range(8):  # max 8 iterations
        answer = current_q["options"][1] if len(current_q.get("options", [])) > 1 else "B"
        r = requests.post(f"{BASE}/submit-answer", json={
            "session_id": session_id,
            "question": current_q["question_text"],
            "answer": answer,
            "response_latency_sec": 3.0 + i * 0.5,
        })
        assert r.status_code == 200
        d = r.json()
        result = d["result"]
        
        if result["status"] == "ASK_QUESTION":
            print(f"  ✓ Q{i+2}: {result['question_text'][:60]}...")
            current_q = result
        elif result["status"] == "CONFIDENT_EXTRACTION":
            features = result.get("features", {})
            print(f"  ✓ EXTRACTION after {i+1} answers")
            print(f"    Features: {json.dumps(features, indent=None)}")
            
            if "score_result" in d:
                score_result = d["score_result"]
                print(f"    Auto-Score: {score_result['score']} ({score_result['decision']})")
            return result, score_result
        else:
            print(f"  ✗ Unknown status: {result['status']}")
            break
    
    return None, None

def test_session_detail(session_id):
    r = requests.get(f"{BASE}/session/{session_id}")
    assert r.status_code == 200
    d = r.json()
    assert d["session"]["status"] == "COMPLETED"
    assert d["session"]["final_score"] is not None
    assert d["session"]["final_score"] > 0
    print(f"  ✓ Session detail OK — score={d['session']['final_score']}, decision={d['session']['decision']}")
    return d

def test_sessions_summary():
    r = requests.get(f"{BASE}/sessions-summary")
    assert r.status_code == 200
    d = r.json()
    assert d["total_sessions"] >= 1
    assert d["completed_sessions"] >= 1
    print(f"  ✓ Sessions summary — total={d['total_sessions']}, completed={d['completed_sessions']}, avg_q={d['avg_questions_per_session']}")
    return d

def test_dynamic_ilf():
    r = requests.post(f"{BASE}/dynamic-ilf-score", json={
        "latencies": [3.0, 2.5, 4.0, 3.5],
        "answers": ["B. answer1", "A. answer2", "D. answer3", "B. answer4"],
        "questions": ["Q about income", "Q about savings", "I can predict stocks with 100% accuracy", "Q about shocks"]
    })
    assert r.status_code == 200
    d = r.json()
    assert "reliability_score" in d
    print(f"  ✓ Dynamic ILF — R={d['reliability_score']:.2f} ({d['reliability_label']}), catch_flagged={d['catch_trial_flagged']}")
    return d

def main():
    print("=" * 55)
    print("  LLM Assessment Flow — Integration Test")
    print("=" * 55)
    
    try:
        requests.get(f"{BASE}/health", timeout=2)
    except Exception:
        print("\n  ✗ API not running. Start with: py -m uvicorn api.main:app --port 8000")
        sys.exit(1)

    print("\n  --- Health Check ---")
    test_health()

    print("\n  --- Start Assessment ---")
    start_data = test_start_assessment()
    session_id = start_data["session_id"]
    first_q = start_data["result"]

    print("\n  --- Submit Answers (Adaptive Loop) ---")
    extraction, score_result = test_submit_answers(session_id, first_q)
    
    if extraction is None:
        print("\n  ✗ FAILED: Never reached extraction")
        sys.exit(1)

    print("\n  --- Session Detail ---")
    test_session_detail(session_id)

    print("\n  --- Sessions Summary ---")
    test_sessions_summary()

    print("\n  --- Dynamic ILF Score ---")
    test_dynamic_ilf()

    print("\n" + "=" * 55)
    print("  ALL TESTS PASSED ✓")
    print("=" * 55)

if __name__ == "__main__":
    main()
