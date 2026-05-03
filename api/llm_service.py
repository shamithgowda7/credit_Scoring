"""
LLM Service — Adaptive Russian Doll Interview Engine
=====================================================
Uses Google Gemini 2.5 Flash to conduct dynamic behavioral interviews.
Falls back to a deterministic mock mode when GEMINI_API_KEY is not set.

Features:
  - Structured JSON output schema enforcement
  - Exponential backoff retry (3 attempts)
  - Hard cap on questions (default 8)
  - Mock mode for offline/CI testing
  - Myers-Briggs inspired dimension mapping
"""

import os
import json
import time
import logging
import requests
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────

MAX_QUESTIONS_DEFAULT = 8
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 1.5  # seconds: 1.5, 3.0, 6.0


def get_gemini_api_key() -> Optional[str]:
    """Return the Gemini API key, or None if not configured."""
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    return key if key else None


def is_llm_available() -> bool:
    """Check whether a real LLM backend is configured."""
    return get_gemini_api_key() is not None


# ── Gemini API Caller with Retry ─────────────────────────────────────────────

def call_gemini(prompt: str) -> str:
    """
    Make a REST call to Gemini 2.5 Flash with retry + backoff.
    
    Raises Exception after MAX_RETRIES failed attempts.
    """
    api_key = get_gemini_api_key()
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set.")

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/"
        f"models/gemini-2.5-flash:generateContent?key={api_key}"
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.4,
            "responseMimeType": "application/json",
        },
    }

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.post(url, json=payload, timeout=30)

            if response.status_code == 200:
                data = response.json()
                try:
                    return data["candidates"][0]["content"]["parts"][0]["text"]
                except (KeyError, IndexError):
                    raise Exception(f"Unexpected Gemini response format: {data}")

            # Retryable errors: 429 (rate limit), 500, 503
            if response.status_code in (429, 500, 503):
                wait = RETRY_BACKOFF_BASE * (2 ** (attempt - 1))
                logger.warning(
                    f"Gemini API returned {response.status_code}, "
                    f"retrying in {wait:.1f}s (attempt {attempt}/{MAX_RETRIES})"
                )
                time.sleep(wait)
                last_error = Exception(
                    f"Gemini API {response.status_code}: {response.text[:300]}"
                )
                continue

            # Non-retryable error
            raise Exception(f"Gemini API Error {response.status_code}: {response.text[:500]}")

        except requests.exceptions.Timeout:
            wait = RETRY_BACKOFF_BASE * (2 ** (attempt - 1))
            logger.warning(f"Gemini API timeout, retrying in {wait:.1f}s")
            time.sleep(wait)
            last_error = Exception("Gemini API request timed out")
        except requests.exceptions.ConnectionError as e:
            wait = RETRY_BACKOFF_BASE * (2 ** (attempt - 1))
            logger.warning(f"Gemini connection error, retrying in {wait:.1f}s")
            time.sleep(wait)
            last_error = Exception(f"Connection error: {e}")

    raise last_error or Exception("Gemini API failed after all retries")


# ── Prompt Builder ────────────────────────────────────────────────────────────

def _build_prompt(bank_context: str, qa_history: list, 
                  question_count: int, max_questions: int,
                  force_extract: bool) -> str:
    """Build the structured prompt for Gemini."""

    history_text = ""
    if not qa_history:
        history_text = "No questions asked yet. Generate the FIRST question."
    else:
        history_text = "Previous Q&A History:\n"
        for i, qa in enumerate(qa_history):
            history_text += f"  Q{i+1}: {qa['q']}\n  A{i+1}: {qa['a']}\n\n"

    # Force extraction on last allowed question
    remaining = max_questions - question_count
    force_clause = ""
    if force_extract or remaining <= 0:
        force_clause = """
    *** MANDATORY: You have reached the maximum interview depth. ***
    You MUST output status "CONFIDENT_EXTRACTION" with your best estimates 
    for all 6 features based on whatever information you have gathered so far.
    Do NOT output another question.
    """
    elif remaining <= 2:
        force_clause = f"""
    *** WARNING: Only {remaining} question(s) remaining before forced extraction. ***
    If you have reasonable confidence, prefer extracting now.
    """

    # Catch-trial injection: every 4th question should be absurd
    catch_trial_clause = ""
    if question_count > 0 and question_count % 4 == 3 and not force_extract:
        catch_trial_clause = """
    *** CATCH-TRIAL REQUIRED FOR THIS TURN ***
    Your next question MUST be an obviously absurd statement that any honest 
    person would disagree with. Examples:
    - "I can accurately predict next week's stock prices."
    - "I have never made a financial mistake in my life."
    - "I believe borrowing money has zero risks."
    Make option A = "Strongly Agree" and option B = "Disagree — that's unrealistic".
    This is a cognitive attention check. Still use 4 options but make the absurd 
    agreement obvious.
    """

    prompt = f"""You are an expert behavioral economist and credit risk assessor conducting 
a dynamic "Russian Doll" interview. Each question peels back a deeper layer of the 
applicant's financial personality.

=== APPLICANT'S RAW BANK CONTEXT ===
"{bank_context}"

=== INTERVIEW STATUS ===
Questions asked so far: {question_count}
Maximum questions allowed: {max_questions}

{history_text}

{force_clause}
{catch_trial_clause}

=== YOUR GOAL ===
Extract EXACTLY these 6 causal features for our credit scoring model:

| Feature            | Range       | Meaning                                      |
|--------------------|-------------|----------------------------------------------|
| income_mean        | 0.0 to 1.0  | Income stability/level (1.0 = very high)     |
| income_cv          | 0.0 to 2.0  | Income volatility (0.0 = very stable)        |
| utility_rate       | 0.0 to 1.0  | Bill payment reliability (1.0 = always on time) |
| dti_final          | 0.0 to 1.0  | Debt-to-income ratio (1.0 = extreme debt)    |
| employment_status  | 0.0 or 1.0  | Employed (1.0) or unemployed (0.0)           |
| shock_total        | 0.0 to 5.0  | Number of recent financial shocks            |

=== HYPER-PERSONALIZATION RULES (CRITICAL) ===
You are NOT a standard bank. You are a highly empathetic AI having a conversational, context-aware interview.
Do NOT ask generic banking questions like "How do you manage your budget?". 
You MUST weave the specific details from the APPLICANT'S RAW BANK CONTEXT into EVERY single question.
- If the context says they are a "delivery driver", frame a question around "your bike breaking down" or "a rainy week with few orders".
- If the context says they "run a tailoring business", frame a question around "a delayed bulk order from a client" or "buying a new sewing machine".
- If they have specific dependents, loans, or income amounts mentioned, use those EXACT details in the scenario.

Example BAD Question: "How do you handle unexpected expenses?"
Example GOOD Question: "Meera, since your tailoring business earns around ₹20k-₹30k but drops during non-festival months, what would you do if your sewing machine broke down in May and cost ₹5,000 to fix?"

Every question should feel like a custom-tailored scenario specifically designed for this individual's exact life situation. If you fail to personalize the question using the context, you have failed your core directive.

=== QUESTIONING STRATEGY (Myers-Briggs Inspired) ===
Map your questions to these behavioral dimensions:
- **Stability vs Volatility** (E/I analog) → income_mean, income_cv
- **Planning vs Spontaneity** (J/P analog) → utility_rate, dti_final  
- **Resilience vs Vulnerability** (T/F analog) → shock_total, employment_status

Each question should have 4 options (A, B, C, D) representing different behavioral 
profiles on a spectrum. Ensure the options sound like natural reactions to the highly personalized scenario, NOT generic textbook answers.

=== DECISION RULES ===
- If fewer than 3 questions asked → MUST ask another question
- If 3+ questions asked AND you can confidently estimate all 6 features → extract
- If approaching the cap ({max_questions}) → extract with best estimates

=== OUTPUT FORMAT (strict JSON) ===
You must output ONLY valid, parseable JSON. Do NOT use double quotes (") inside your strings. Use single quotes (') or omit them to prevent JSON parsing errors.

If generating a new question:
{{
    "status": "ASK_QUESTION",
    "question_text": "Your behavioral question here...",
    "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
    "dimension": "stability|planning|resilience",
    "reasoning": "Brief note on what this question probes"
}}

If confident to extract features:
{{
    "status": "CONFIDENT_EXTRACTION",
    "features": {{
        "income_mean": 0.5,
        "income_cv": 0.2,
        "utility_rate": 0.9,
        "dti_final": 0.4,
        "employment_status": 1.0,
        "shock_total": 0.0
    }},
    "confidence": "high|medium|low",
    "reasoning": "Brief explanation of how you derived each feature"
}}
"""
    return prompt


# ── Mock Mode ─────────────────────────────────────────────────────────────────

MOCK_QUESTIONS = [
    {
        "status": "ASK_QUESTION",
        "question_text": "When you receive your income, what best describes your approach to managing it?",
        "options": [
            "A. I immediately allocate to savings, bills, and investments with a strict budget",
            "B. I pay essential bills first, then save what I can",
            "C. I handle expenses as they come up without a fixed plan",
            "D. I often find myself short before the next paycheck arrives"
        ],
        "dimension": "planning",
        "reasoning": "Probes financial planning behavior → utility_rate, dti_final"
    },
    {
        "status": "ASK_QUESTION",
        "question_text": "How would you describe your income pattern over the past year?",
        "options": [
            "A. Very stable — I earn roughly the same amount every month",
            "B. Mostly stable with occasional bonuses or dips",
            "C. It varies significantly — some months are much better than others",
            "D. Highly unpredictable — I never know what next month will bring"
        ],
        "dimension": "stability",
        "reasoning": "Directly probes income_mean and income_cv"
    },
    {
        "status": "ASK_QUESTION",
        "question_text": "I can accurately predict what the stock market will do next week.",
        "options": [
            "A. Strongly agree — I have excellent financial intuition",
            "B. Somewhat agree — I can usually guess the trends",
            "C. Disagree — markets are too unpredictable for anyone",
            "D. Strongly disagree — that's unrealistic for anyone"
        ],
        "dimension": "resilience",
        "reasoning": "CATCH TRIAL: Tests cognitive attentiveness"
    },
    {
        "status": "ASK_QUESTION",
        "question_text": "If you suddenly lost your primary source of income tomorrow, how long could you sustain your current lifestyle?",
        "options": [
            "A. More than 6 months — I have substantial emergency savings",
            "B. 2-6 months — I have some buffer but would need to adjust",
            "C. About a month — I'd need to find income quickly",
            "D. Less than a week — I'm living paycheck to paycheck"
        ],
        "dimension": "resilience",
        "reasoning": "Probes shock_total resilience and emergency preparedness"
    },
]


def _mock_extract_features(qa_history: list) -> dict:
    """
    Extract features from mock Q&A using simple keyword heuristics.
    Used when no Gemini API key is available.
    """
    # Default mid-range values
    features = {
        "income_mean": 0.3,
        "income_cv": 0.5,
        "utility_rate": 0.5,
        "dti_final": 0.6,
        "employment_status": 0.0,
        "shock_total": 1.0,
    }

    for qa in qa_history:
        answer = qa.get("a", "").upper()

        # Budgeting question (Q1)
        if "allocate to savings" in qa.get("q", "").lower() or "managing it" in qa.get("q", "").lower():
            if "A." in answer or answer.startswith("A"):
                features["utility_rate"] = 0.9
                features["dti_final"] = 0.3
            elif "B." in answer or answer.startswith("B"):
                features["utility_rate"] = 0.7
                features["dti_final"] = 0.5
            elif "C." in answer or answer.startswith("C"):
                features["utility_rate"] = 0.4
                features["dti_final"] = 0.7
            elif "D." in answer or answer.startswith("D"):
                features["utility_rate"] = 0.2
                features["dti_final"] = 0.85

        # Income stability question (Q2)
        if "income pattern" in qa.get("q", "").lower():
            if "A." in answer or answer.startswith("A"):
                features["income_mean"] = 0.7
                features["income_cv"] = 0.1
                features["employment_status"] = 1.0
            elif "B." in answer or answer.startswith("B"):
                features["income_mean"] = 0.5
                features["income_cv"] = 0.4
                features["employment_status"] = 1.0
            elif "C." in answer or answer.startswith("C"):
                features["income_mean"] = 0.3
                features["income_cv"] = 0.8
            elif "D." in answer or answer.startswith("D"):
                features["income_mean"] = 0.1
                features["income_cv"] = 1.5

        # Emergency savings question (Q4)
        if "lost your primary" in qa.get("q", "").lower() or "sustain your current" in qa.get("q", "").lower():
            if "A." in answer or answer.startswith("A"):
                features["shock_total"] = 0.0
            elif "B." in answer or answer.startswith("B"):
                features["shock_total"] = 1.0
            elif "C." in answer or answer.startswith("C"):
                features["shock_total"] = 2.0
            elif "D." in answer or answer.startswith("D"):
                features["shock_total"] = 3.5

    return features


def _mock_evaluate(bank_context: str, qa_history: list, 
                   question_count: int, max_questions: int,
                   force_extract: bool) -> dict:
    """Deterministic mock mode — cycles through pre-built questions."""

    # Force extraction if we've hit the cap or answered all mock questions
    if force_extract or question_count >= min(len(MOCK_QUESTIONS), max_questions):
        features = _mock_extract_features(qa_history)
        return {
            "status": "CONFIDENT_EXTRACTION",
            "features": features,
            "confidence": "medium",
            "reasoning": "Mock mode extraction based on keyword analysis of answers.",
        }

    # Serve the next mock question
    q_idx = min(question_count, len(MOCK_QUESTIONS) - 1)
    return dict(MOCK_QUESTIONS[q_idx])


# ── Main Entry Point ─────────────────────────────────────────────────────────

def evaluate_and_generate_next(
    bank_context: str,
    qa_history: list,
    max_questions: int = MAX_QUESTIONS_DEFAULT,
    force_extract: bool = False,
) -> dict:
    """
    Evaluates the current state of the interview and returns the next step.

    Returns a dict with either:
      - status="ASK_QUESTION" + question_text + options
      - status="CONFIDENT_EXTRACTION" + features dict

    Falls back to mock mode when GEMINI_API_KEY is not set.
    """
    question_count = len(qa_history)

    # ── Mock Mode ──
    if not is_llm_available():
        logger.info("LLM not available, using mock mode")
        return _mock_evaluate(bank_context, qa_history, question_count, max_questions, force_extract)

    # ── Real LLM Mode ──
    prompt = _build_prompt(bank_context, qa_history, question_count, max_questions, force_extract)

    result_text = call_gemini(prompt)

    try:
        clean_json = result_text.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(clean_json)
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Failed to parse LLM JSON: {result_text[:500]}")
        raise Exception(f"Failed to parse LLM response as JSON: {e}")

    # ── Validate the response structure ──
    status = parsed.get("status")

    if status == "ASK_QUESTION":
        # Ensure required fields exist
        if "question_text" not in parsed or "options" not in parsed:
            raise Exception(f"LLM returned ASK_QUESTION without question_text/options: {parsed}")
        # Ensure options is a list
        if not isinstance(parsed["options"], list) or len(parsed["options"]) < 2:
            raise Exception(f"LLM returned invalid options: {parsed['options']}")
        return parsed

    elif status == "CONFIDENT_EXTRACTION":
        features = parsed.get("features", {})
        required = ["income_mean", "income_cv", "utility_rate", "dti_final", "employment_status", "shock_total"]
        missing = [f for f in required if f not in features]
        if missing:
            raise Exception(f"LLM extraction missing features: {missing}")
        # Clamp values to valid ranges
        features["income_mean"] = max(0.0, min(1.0, float(features["income_mean"])))
        features["income_cv"] = max(0.0, min(2.0, float(features["income_cv"])))
        features["utility_rate"] = max(0.0, min(1.0, float(features["utility_rate"])))
        features["dti_final"] = max(0.0, min(1.0, float(features["dti_final"])))
        features["employment_status"] = 1.0 if float(features["employment_status"]) >= 0.5 else 0.0
        features["shock_total"] = max(0.0, min(5.0, float(features["shock_total"])))
        parsed["features"] = features
        return parsed

    else:
        raise Exception(f"LLM returned unknown status: '{status}'. Full response: {parsed}")
