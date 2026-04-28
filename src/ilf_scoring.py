"""
ILF Scoring Engine — Inverse Latency Function
==============================================
Computes a reliability score R in [0, 1] from:
  1. Absolute latencies per question
  2. Delta latency between twin-pair questions
  3. Catch-trial detection (absurd question)

The Inverse-Gaussian-inspired penalty curve penalises:
  - Very fast responses (< 500ms) — random clicking
  - Very slow responses (> 15s)  — overthinking / distraction
  - Inconsistent twin-pair timing  — suggests inattention
  - Agreeing with an absurd statement — flags entire session
"""

import math
import numpy as np
from typing import List, Dict, Tuple


# ── ILF Questions Definition ─────────────────────────────────────────────────

ILF_QUESTIONS = [
    {
        "id": "q1",
        "text": "I feel confident about handling unexpected expenses.",
        "options": ["Agree", "Disagree"],
        "type": "twin_a",
        "twin_pair": "financial_confidence",
    },
    {
        "id": "q2",
        "text": "I usually know exactly how much money I'll have next week.",
        "options": ["Agree", "Disagree"],
        "type": "twin_b",
        "twin_pair": "financial_confidence",
    },
    {
        "id": "q3",
        "text": "I can hold my breath underwater for 10 minutes.",
        "options": ["Agree", "Disagree"],
        "type": "catch_trial",
        "twin_pair": None,
    },
]


# ── Penalty Functions ─────────────────────────────────────────────────────────

def _inverse_gaussian_penalty(latency_sec: float,
                               mu: float = 3.0,
                               lam: float = 2.0) -> float:
    """
    Inverse-Gaussian-inspired penalty for a single response latency.

    Returns a score in [0, 1]:
      - Peak (~1.0) at latency = mu (natural reading + thinking time)
      - Drops toward 0 for very fast (< 0.5s) or very slow (> 15s) responses

    Parameters
    ----------
    latency_sec : float
        Observed response time in seconds.
    mu : float
        Ideal response time (mode of the distribution). Default 3.0s.
    lam : float
        Shape parameter. Higher = sharper peak. Default 2.0.
    """
    if latency_sec <= 0.01:
        return 0.0  # impossibly fast

    # Hard floor: < 0.5s is too fast to have read the question
    if latency_sec < 0.5:
        return 0.05

    # Inverse Gaussian PDF (unnormalised, scaled to peak at ~1.0)
    x = latency_sec
    exponent = -lam * (x - mu) ** 2 / (2 * mu ** 2 * x)
    raw = math.sqrt(lam / (2 * math.pi * x ** 3)) * math.exp(exponent)

    # Normalise so the peak value = 1.0
    # Peak of IG PDF is at x = mu * (sqrt(1 + (3mu/2lam)^2) - 3mu/(2lam))
    # For simplicity, we compute the peak value and normalise
    peak_x = mu  # approximate peak location
    peak_exp = -lam * (peak_x - mu) ** 2 / (2 * mu ** 2 * peak_x)
    peak_raw = math.sqrt(lam / (2 * math.pi * peak_x ** 3)) * math.exp(peak_exp)

    if peak_raw > 0:
        score = min(raw / peak_raw, 1.0)
    else:
        score = 0.0

    return score


def _delta_latency_penalty(latency_a: float, latency_b: float,
                            max_ratio: float = 3.0) -> float:
    """
    Penalise inconsistent response times between twin-pair questions.

    If the user takes 1.5s on Q1 and 8s on Q2 (same topic), the ratio
    is suspicious. Returns a score in [0, 1].

    Parameters
    ----------
    latency_a, latency_b : float
        Response times for the twin pair (seconds).
    max_ratio : float
        Maximum acceptable ratio before full penalty. Default 3.0.
    """
    if latency_a <= 0.01 or latency_b <= 0.01:
        return 0.0

    ratio = max(latency_a, latency_b) / min(latency_a, latency_b)

    if ratio <= 1.5:
        return 1.0   # very consistent
    elif ratio >= max_ratio:
        return 0.2   # very inconsistent
    else:
        # Linear decay from 1.0 to 0.2 over ratio range [1.5, max_ratio]
        return 1.0 - 0.8 * (ratio - 1.5) / (max_ratio - 1.5)


# ── Main Scoring Function ────────────────────────────────────────────────────

def compute_ilf_score(latencies: List[float],
                      answers: List[str],
                      questions: List[Dict] = None) -> Dict:
    """
    Compute the ILF reliability score.

    Parameters
    ----------
    latencies : list of float
        Response times in seconds for each question (in order).
    answers : list of str
        User's answers for each question (in order).
    questions : list of dict, optional
        Question definitions. Defaults to ILF_QUESTIONS.

    Returns
    -------
    dict with keys:
        - reliability_score : float in [0, 1]
        - reliability_pct   : int (0-100)
        - reliability_label : str ("High" / "Moderate" / "Low")
        - catch_trial_flagged : bool
        - per_question_scores : list of float
        - delta_penalty : float
        - details : dict with breakdown
    """
    if questions is None:
        questions = ILF_QUESTIONS

    n = min(len(latencies), len(answers), len(questions))
    if n == 0:
        return _empty_result()

    # 1) Per-question Inverse Gaussian scores
    per_q_scores = []
    for i in range(n):
        s = _inverse_gaussian_penalty(latencies[i])
        per_q_scores.append(round(s, 4))

    avg_ig_score = np.mean(per_q_scores)

    # 2) Delta latency for twin pair
    twin_a_idx = None
    twin_b_idx = None
    for i, q in enumerate(questions[:n]):
        if q.get("type") == "twin_a":
            twin_a_idx = i
        elif q.get("type") == "twin_b":
            twin_b_idx = i

    if twin_a_idx is not None and twin_b_idx is not None:
        delta_score = _delta_latency_penalty(
            latencies[twin_a_idx], latencies[twin_b_idx]
        )
    else:
        delta_score = 1.0  # no twin pair to compare

    # 3) Catch trial check
    catch_flagged = False
    for i, q in enumerate(questions[:n]):
        if q.get("type") == "catch_trial" and i < len(answers):
            if answers[i] == "Agree":
                catch_flagged = True

    # 4) Combine into final R
    #    R = w1 * avg_IG + w2 * delta_penalty - catch_penalty
    w_ig = 0.60
    w_delta = 0.40
    catch_penalty = 0.50 if catch_flagged else 0.0

    R = w_ig * avg_ig_score + w_delta * delta_score - catch_penalty
    R = max(0.0, min(1.0, R))

    # Label
    if R > 0.85:
        label = "High"
    elif R > 0.60:
        label = "Moderate"
    else:
        label = "Low"

    return {
        "reliability_score": round(R, 4),
        "reliability_pct": int(round(R * 100)),
        "reliability_label": label,
        "catch_trial_flagged": catch_flagged,
        "per_question_scores": per_q_scores,
        "delta_penalty": round(delta_score, 4),
        "avg_ig_score": round(avg_ig_score, 4),
        "latencies_sec": [round(l, 3) for l in latencies[:n]],
        "details": {
            "weight_ig": w_ig,
            "weight_delta": w_delta,
            "catch_penalty_applied": catch_penalty,
            "formula": f"R = {w_ig}*IG({round(avg_ig_score,3)}) + {w_delta}*Delta({round(delta_score,3)}) - catch({catch_penalty})",
        },
    }


def _empty_result() -> Dict:
    return {
        "reliability_score": 0.0,
        "reliability_pct": 0,
        "reliability_label": "Low",
        "catch_trial_flagged": False,
        "per_question_scores": [],
        "delta_penalty": 0.0,
        "avg_ig_score": 0.0,
        "latencies_sec": [],
        "details": {},
    }


# ── Quick self-test ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 55)
    print("  ILF Scoring Engine — Self-Test")
    print("=" * 55)

    # Test 1: Normal honest user (2-4s per question)
    r1 = compute_ilf_score([2.5, 3.0, 2.0], ["Agree", "Agree", "Disagree"])
    print(f"\n  Normal user:     R={r1['reliability_score']:.2f} ({r1['reliability_label']})")

    # Test 2: Very fast clicker (< 0.5s per question)
    r2 = compute_ilf_score([0.3, 0.2, 0.4], ["Agree", "Agree", "Disagree"])
    print(f"  Speed clicker:   R={r2['reliability_score']:.2f} ({r2['reliability_label']})")

    # Test 3: Catch trial failed (agreed to absurd Q3)
    r3 = compute_ilf_score([2.5, 3.0, 2.0], ["Agree", "Agree", "Agree"])
    print(f"  Catch failed:    R={r3['reliability_score']:.2f} ({r3['reliability_label']})")

    # Test 4: Inconsistent twin pair (1s vs 12s)
    r4 = compute_ilf_score([1.0, 12.0, 2.0], ["Agree", "Agree", "Disagree"])
    print(f"  Inconsistent:    R={r4['reliability_score']:.2f} ({r4['reliability_label']})")

    # Test 5: Perfect timing
    r5 = compute_ilf_score([3.0, 3.0, 3.0], ["Agree", "Disagree", "Disagree"])
    print(f"  Perfect timing:  R={r5['reliability_score']:.2f} ({r5['reliability_label']})")

    print("\n  All tests completed.")
    print("=" * 55)
