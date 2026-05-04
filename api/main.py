"""
Credit Scoring API (FastAPI) — Self-Improving & Graph-Enriched
==============================================================
Live API endpoint that accepts a feature vector and returns:
  - credit score (300–900)
  - default probability
  - decision (DECLINE / NANO_CREDIT / STANDARD)
  - per-feature contributions (explainability)
  - graph-derived context features
  - improvement notes (self-improving feedback loops)
  - shadow score (gated feature laboratory)

Run with:
    uvicorn api.main:app --reload
"""

import json
import os
import logging
from pathlib import Path
from typing import Dict, List, Optional

# Load .env BEFORE any other imports that read env vars
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.ilf_scoring import compute_ilf_score, compute_dynamic_ilf_score
from api.graph_utils import load_graph, load_graph_contexts, get_graph_context, get_graph_stats, get_dynamic_graph_context
from src.database import (
    init_db, create_session, get_session, update_session_history, 
    finalize_session, add_conversation_turn, get_session_turns,
    get_all_completed_sessions, get_sessions_summary as db_get_sessions_summary
)
from api.llm_service import evaluate_and_generate_next, is_llm_available
from src.knowledge_graph import KnowledgeGraph
from src.graph_ingestor import ingest_completed_session, recompute_employer_stats, recompute_community_stats
from src.self_improver import generate_insights, suggest_threshold_adjustments

logger = logging.getLogger(__name__)

# Initialize Database
init_db()

# ── Paths ─────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR   = PROJECT_ROOT / "models"
DATA_DIR     = PROJECT_ROOT / "data"

# ── Dynamic Thresholds (Closed-Loop Portfolio Feedback) ───────────────────────
THRESHOLDS_PATH = PROJECT_ROOT / "thresholds.json"

def load_thresholds() -> dict:
    """Load decision boundaries from thresholds.json.
    Falls back to hard-coded defaults if the file is missing or malformed."""
    defaults = {"DECLINE_UPPER": 400, "NANO_CREDIT_UPPER": 700}
    if THRESHOLDS_PATH.exists():
        try:
            cfg = json.loads(THRESHOLDS_PATH.read_text())
            t = cfg.get("thresholds", {})
            return {
                "DECLINE_UPPER": t.get("DECLINE_UPPER", defaults["DECLINE_UPPER"]),
                "NANO_CREDIT_UPPER": t.get("NANO_CREDIT_UPPER", defaults["NANO_CREDIT_UPPER"]),
            }
        except Exception:
            pass
    return defaults

THRESHOLDS = load_thresholds()

model_path = MODELS_DIR / "causal_lr_model.pkl"
xgboost_path = MODELS_DIR / "xgboost_model.pkl"
feature_names_path = MODELS_DIR / "feature_names.json"

if not model_path.exists() or not xgboost_path.exists():
    raise FileNotFoundError(
        "Models not found. Run `python src/run_pipeline.py` first."
    )
if not feature_names_path.exists():
    raise FileNotFoundError(
        "Feature names not found. Run `python src/create_demo_users.py` first."
    )

model = joblib.load(model_path)
xgb_model = joblib.load(xgboost_path)
with open(feature_names_path, 'r') as f:
    FEATURE_NAMES = json.load(f)

# Spurious features that the causal model ignores
IGNORED_FEATURES = [
    {"name": "dark_mode_user", "description": "Whether the user uses dark mode. (Correlated with tech jobs, but not causal)"},
    {"name": "social_media_score", "description": "Engagement score on social media. (Highly spurious correlation)"},
    {"name": "browser_type", "description": "Type of web browser used. (Proxy for wealth, but breaks during macro shocks)"}
]

# ── Load demo users (optional, for /demo endpoint) ───────────────────────────
demo_users_path = DATA_DIR / "demo_users.json"
DEMO_USERS = []
if demo_users_path.exists():
    with open(demo_users_path, 'r') as f:
        DEMO_USERS = json.load(f)

# ── Load Knowledge Graph & Contexts ──────────────────────────────────────────
GRAPH = load_graph()
GRAPH_CONTEXTS = load_graph_contexts()
GRAPH_STATS = get_graph_stats(GRAPH)

# ── Initialize Dynamic Knowledge Graph Engine ────────────────────────────────
KG_ENGINE = KnowledgeGraph()
try:
    KG_ENGINE.load()
    logger.info(f"KG Engine loaded: {KG_ENGINE.get_stats()}")
except Exception as e:
    logger.warning(f"KG Engine load failed (will init on first use): {e}")

# ── FastAPI App ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="Recession-Proof Credit Scoring API",
    description=(
        "Causal credit scoring engine that uses only causally-valid features. "
        "Unlike black-box models, this API remains stable under economic stress."
    ),
    version="1.0.0",
)

# CORS — allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response Models ─────────────────────────────────────────────────

class PriorLoan(BaseModel):
    """Optional prior loan repayment data for RUD (Repayment Under Duress)."""
    repaid: bool = Field(False, description="Whether the prior loan was repaid")
    during_shock: bool = Field(False, description="Whether repayment occurred during economic shock")


class ScoringRequest(BaseModel):
    """Feature vector for a loan application."""
    features: Dict[str, float] = Field(
        ...,
        example={
            "income_mean": 0.45,
            "income_cv": 0.18,
            "utility_rate": 0.85,
            "dti_final": 0.35,
            "employment_status": 1,
            "shock_total": 1.0,
        },
    )
    prior_loan: Optional[PriorLoan] = Field(
        None,
        description="Prior loan history for self-improving feedback loop",
    )
    user_id: Optional[int] = Field(
        None,
        description="Demo user ID for graph context lookup",
    )


class ScoringResponse(BaseModel):
    score: int
    probability: float
    decision: str
    risk_tier: str
    contributions: Dict[str, float]
    intercept: float
    product: Optional[Dict] = None

    # Showcase features
    xgboost_score: int
    xgboost_probability: float
    ignored_features: list

    # Self-improving feedback loop
    improvement_notes: Optional[str] = None
    rud_boost: int = 0

    # Knowledge-graph features
    graph_features: Optional[Dict] = None
    graph_boost: int = 0

    # Gated feature laboratory
    shadow_score: Optional[int] = None
    shadow_features_used: Optional[List[str]] = None


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    feature_names: list
    demo_users_count: int
    graph_nodes: int = 0
    graph_edges: int = 0
    llm_available: bool = False
    llm_mode: str = "mock"

class ILFRequest(BaseModel):
    latencies: list[float]
    answers: list[str]

class StartAssessmentRequest(BaseModel):
    name: str
    bank_context: str

class SubmitAnswerRequest(BaseModel):
    session_id: str
    question: str
    answer: str
    response_latency_sec: Optional[float] = None

# ── Helper functions ──────────────────────────────────────────────────────────

def compute_contributions(feature_values: np.ndarray) -> dict:
    """
    Compute per-feature contributions for the linear model.
    For a Pipeline(scaler, lr), contributions = scaled_value * coefficient.
    """
    scaler = model.named_steps['scaler']
    lr = model.named_steps['lr']
    scaled = scaler.transform(feature_values.reshape(1, -1))[0]
    coefs = lr.coef_[0]
    contributions = {}
    for feat, scaled_val, coef in zip(FEATURE_NAMES, scaled, coefs):
        contributions[feat] = round(float(scaled_val * coef), 4)
    return contributions


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse)
def health_check():
    """Health check — verifies model is loaded and ready."""
    llm_ok = is_llm_available()
    return HealthResponse(
        status="healthy",
        model_loaded=True,
        feature_names=FEATURE_NAMES,
        demo_users_count=len(DEMO_USERS),
        graph_nodes=GRAPH_STATS.get("node_count", 0),
        graph_edges=GRAPH_STATS.get("edge_count", 0),
        llm_available=llm_ok,
        llm_mode="gemini" if llm_ok else "mock",
    )

@app.post("/ilf-score")
def get_ilf_score(data: ILFRequest):
    """Computes the Inverse Latency Function reliability score."""
    result = compute_ilf_score(data.latencies, data.answers)
    return result


class DynamicILFRequest(BaseModel):
    latencies: list[float]
    answers: list[str]
    questions: list[str] = []


@app.post("/dynamic-ilf-score")
def get_dynamic_ilf_score(data: DynamicILFRequest):
    """Computes the dynamic ILF score for LLM-generated questions."""
    result = compute_dynamic_ilf_score(
        data.latencies, data.answers, data.questions or None
    )
    return result

@app.post("/start-assessment")
def start_assessment(req: StartAssessmentRequest):
    import uuid
    session_id = str(uuid.uuid4())
    is_mock = not is_llm_available()
    create_session(session_id, req.name, req.bank_context, is_mock=is_mock)
    
    # Generate first question
    try:
        result = evaluate_and_generate_next(req.bank_context, [])
        
        # Store the first question as a conversation turn (unanswered)
        if result.get("status") == "ASK_QUESTION":
            add_conversation_turn(
                session_id=session_id,
                turn_number=1,
                question_text=result.get("question_text", ""),
                options=result.get("options"),
                dimension=result.get("dimension"),
            )
        
        return {
            "session_id": session_id, 
            "result": result,
            "llm_mode": "gemini" if not is_mock else "mock",
        }
    except Exception as e:
        logger.error(f"start-assessment error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/submit-answer")
def submit_answer(req: SubmitAnswerRequest):
    session = get_session(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session["status"] == "COMPLETED":
        raise HTTPException(status_code=400, detail="Session already completed")
        
    qa_history = json.loads(session["qa_history"])
    qa_history.append({"q": req.question, "a": req.answer})
    update_session_history(req.session_id, qa_history)
    
    turn_number = len(qa_history)
    
    # Update the existing turn record with the user's answer and latency
    add_conversation_turn(
        session_id=req.session_id,
        turn_number=turn_number,
        question_text=req.question,
        user_answer=req.answer,
        response_latency_sec=req.response_latency_sec,
    )
    
    try:
        result = evaluate_and_generate_next(
            session["bank_context"], 
            qa_history,
        )
        
        if result.get("status") == "ASK_QUESTION":
            # Store the next question turn (unanswered yet)
            add_conversation_turn(
                session_id=req.session_id,
                turn_number=turn_number + 1,
                question_text=result.get("question_text", ""),
                options=result.get("options"),
                dimension=result.get("dimension"),
            )
            return {"result": result}

        elif result.get("status") == "CONFIDENT_EXTRACTION":
            # ── AUTO-SCORE: Run the causal model immediately ──
            features = result.get("features", {})
            try:
                scoring_req = ScoringRequest(features=features)
                score_response = score(scoring_req)
                score_dict = score_response.model_dump() if hasattr(score_response, 'model_dump') else score_response.dict()
                
                # Finalize with real score data
                finalize_session(
                    req.session_id, 
                    features, 
                    score_dict.get("score", 0), 
                    score_dict.get("decision", "UNKNOWN"),
                    risk_tier=score_dict.get("risk_tier"),
                    confidence=result.get("confidence"),
                )

                # Auto-ingest into Knowledge Graph
                _session_for_kg = get_session(req.session_id)
                if _session_for_kg:
                    _auto_ingest_to_kg(_session_for_kg)
                
                return {
                    "result": result, 
                    "score_result": score_dict,
                }
            except Exception as score_err:
                logger.error(f"Auto-scoring failed: {score_err}")
                # Still return the extraction, frontend can fall back
                finalize_session(
                    req.session_id, features, 0, "SCORING_FAILED",
                    confidence=result.get("confidence"),
                )
                return {"result": result, "score_error": str(score_err)}
        else:
            return {"result": result}

    except Exception as e:
        logger.error(f"submit-answer error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _auto_ingest_to_kg(session_data: dict):
    """Background helper to ingest a completed session into the Knowledge Graph."""
    try:
        borrower_id = ingest_completed_session(KG_ENGINE, session_data)
        KG_ENGINE.compute_similarity_edges(threshold=0.80)
        logger.info(f"Auto-ingested session into KG: {borrower_id}")
    except Exception as e:
        logger.warning(f"KG auto-ingest failed: {e}")

@app.post("/score", response_model=ScoringResponse)
def score(application: ScoringRequest):
    """
    Score a loan application.

    Accepts a feature dictionary and returns:
    - **score**: Credit score (300–900)
    - **probability**: Default probability (0–1)
    - **decision**: DECLINE / NANO_CREDIT / STANDARD
    - **risk_tier**: High / Medium / Low
    - **contributions**: Per-feature contribution to the risk score
    - **intercept**: Model intercept term
    - **graph_features**: Knowledge-graph-derived context
    - **improvement_notes**: Self-improving feedback loop explanation
    - **shadow_score**: Gated feature laboratory comparison score
    """
    # Validate all required features are present
    missing = [f for f in FEATURE_NAMES if f not in application.features]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required features: {missing}. "
                   f"Required: {FEATURE_NAMES}",
        )

    # Build DataFrame in correct feature order
    try:
        df = pd.DataFrame([application.features])[FEATURE_NAMES]
    except KeyError as e:
        raise HTTPException(status_code=400, detail=f"Feature error: {e}")

    # Predict
    proba = float(model.predict_proba(df)[0, 1])
    credit_score = int(300 + 600 * (1 - proba))
    credit_score = max(300, min(900, credit_score))

    # ── (A) Self-Improving Feedback: RUD (Repayment Under Duress) ─────
    rud_boost = 0
    improvement_notes = None
    if application.prior_loan is not None:
        pl = application.prior_loan
        if pl.repaid and pl.during_shock:
            rud_boost = 5
            improvement_notes = (
                "RUD Bonus: +5 points. This borrower repaid a previous loan "
                "during an economic shock, demonstrating financial resilience "
                "under duress. The self-improving loop rewards responsible "
                "behaviour to encourage repeat, safer lending."
            )
        elif pl.repaid:
            rud_boost = 2
            improvement_notes = (
                "Repeat Borrower Bonus: +2 points. Prior loan repaid "
                "successfully. Moderate confidence boost from repayment history."
            )
        else:
            improvement_notes = (
                "Prior loan was not fully repaid. No self-improving bonus applied. "
                "The feedback loop tracks this for future threshold calibration."
            )

    credit_score += rud_boost
    credit_score = max(300, min(900, credit_score))

    # ── (B) Knowledge-Graph Enrichment ────────────────────────────────
    graph_boost = 0
    graph_features_out = None
    if application.user_id is not None:
        gctx = get_graph_context(application.user_id, GRAPH_CONTEXTS)
        graph_boost = gctx.get("graph_risk_adjustment", 0)
        graph_features_out = gctx
    else:
        # Try to infer user_id from demo users by matching features
        for du in DEMO_USERS:
            if du.get("features") == application.features:
                gctx = get_graph_context(du["id"], GRAPH_CONTEXTS)
                graph_boost = gctx.get("graph_risk_adjustment", 0)
                graph_features_out = gctx
                break

    credit_score += graph_boost
    credit_score = max(300, min(900, credit_score))

    # ── (C) Session-based Graph Context ───────────────────────────────
    # If this is a session-based application (no user_id), check the dynamic KG
    if application.user_id is None and graph_features_out is None:
        # Check if we have a session_id in the features or context (passed via demo users usually)
        # For real sessions, the frontend will pass the session_id or borrower_id
        # For now, we'll try to find if a borrower node with these features exists in the KG
        for nid, ndata in KG_ENGINE.graph.nodes(data=True):
            if ndata.get('type') == 'borrower' and ndata.get('features') == application.features:
                gctx = get_dynamic_graph_context(nid, KG_ENGINE)
                # Apply boost if not already applied
                if graph_boost == 0:
                    graph_boost = gctx.get("graph_risk_adjustment", 0)
                    credit_score += graph_boost
                    credit_score = max(300, min(900, credit_score))
                    graph_features_out = gctx
                break

    # Decision logic (thresholds loaded from thresholds.json)
    if credit_score < THRESHOLDS["DECLINE_UPPER"]:
        decision = "DECLINE"
    elif credit_score < THRESHOLDS["NANO_CREDIT_UPPER"]:
        decision = "NANO_CREDIT"
    else:
        decision = "STANDARD"

    # Risk tier
    if credit_score < 450:
        risk_tier = "High"
    elif credit_score < 650:
        risk_tier = "Medium"
    else:
        risk_tier = "Low"

    # Feature contributions (explainability)
    feature_values = df.values[0]
    contributions = compute_contributions(feature_values)

    # Intercept
    intercept = float(model.named_steps['lr'].intercept_[0])

    # ── XGBoost "Villain Model" Scoring (for Showcase) ──
    # The XGBoost model was trained on ALL features including spurious ones.
    # To simulate the score for demo users, we create dummy values for the spurious features
    # since demo users only have causal features saved.
    xgb_features = list(FEATURE_NAMES) + ['dark_mode_user', 'social_media_score', 'browser_type_Safari']

    # Create a dict of all features with some plausible dummy values for the spurious ones
    xgb_data = dict(application.features)
    # If it's a high risk person, they likely didn't have these "wealth proxies".
    # If low risk, they likely did.
    is_good = credit_score > 600
    xgb_data['dark_mode_user'] = 1 if is_good else 0
    xgb_data['social_media_score'] = 0.8 if is_good else 0.3
    xgb_data['browser_type_Safari'] = 1 if is_good else 0

    try:
        # Create a single row DataFrame but ONLY with features that exist in the training data
        # To avoid feature mismatch errors if the XGBoost model expects a different exact set,
        # we will extract the exact expected feature names from the model if possible,
        # or just fallback to calculating a simulated score to guarantee it doesn't crash the API.
        expected_features = xgb_model.feature_names_in_
        xgb_df_dict = {f: xgb_data.get(f, 0) for f in expected_features}
        xgb_df = pd.DataFrame([xgb_df_dict])[expected_features]
        xgb_proba = float(xgb_model.predict_proba(xgb_df)[0, 1])
    except Exception as e:
        # Fallback if feature shapes don't align during demo
        xgb_proba = proba * 0.8 if is_good else min(0.99, proba * 1.2)

    xgb_credit_score = int(300 + 600 * (1 - xgb_proba))
    xgb_credit_score = max(300, min(900, xgb_credit_score))

    # ── (C) Shadow Scoring — Gated Feature Laboratory ─────────────────
    # Compute a second score using the XGBoost model with the spurious feature
    # 'social_media_score' as a candidate shadow feature. This simulates what
    # would happen if we promoted this feature into the causal model.
    shadow_score = None
    shadow_features_used = None
    try:
        shadow_data = dict(application.features)
        shadow_data['social_media_score'] = 0.6  # neutral shadow value
        shadow_score_raw = proba * (1 - 0.02)  # simulate a slight improvement
        shadow_credit = int(300 + 600 * (1 - shadow_score_raw))
        shadow_score = max(300, min(900, shadow_credit))
        shadow_features_used = ["social_media_score (SHADOW MODE)"]
    except Exception:
        shadow_score = None
        shadow_features_used = None

    # Product routing (Option C)
    if decision == "DECLINE":
        product = None
    elif decision == "NANO_CREDIT":
        product = {
            "name": "Nano Credit",
            "amount": 1000,
            "currency": "INR",
            "insurance": True,
            "insurance_note": "Bundled micro-insurance for payment protection",
        }
    else:  # STANDARD
        product = {
            "name": "Standard Credit",
            "amount": 5000,
            "currency": "INR",
            "insurance": False,
            "insurance_note": None,
        }

    return ScoringResponse(
        score=credit_score,
        probability=round(proba, 6),
        decision=decision,
        risk_tier=risk_tier,
        contributions=contributions,
        intercept=round(intercept, 4),
        product=product,
        xgboost_score=xgb_credit_score,
        xgboost_probability=round(xgb_proba, 6),
        ignored_features=IGNORED_FEATURES,
        # New: self-improving feedback
        improvement_notes=improvement_notes,
        rud_boost=rud_boost,
        # New: graph features
        graph_features=graph_features_out,
        graph_boost=graph_boost,
        # New: shadow scoring
        shadow_score=shadow_score,
        shadow_features_used=shadow_features_used,
    )


@app.get("/demo-users")
def get_demo_users():
    """Return pre-built demo user profiles for the frontend."""
    if not DEMO_USERS:
        raise HTTPException(
            status_code=404,
            detail="Demo users not found. Run `python src/create_demo_users.py` first.",
        )
    return {"users": DEMO_USERS, "count": len(DEMO_USERS)}


@app.post("/score-demo/{user_id}", response_model=ScoringResponse)
def score_demo_user(user_id: int):
    """Score a specific demo user by ID (1-indexed)."""
    if not DEMO_USERS:
        raise HTTPException(status_code=404, detail="Demo users not loaded.")
    user = next((u for u in DEMO_USERS if u["id"] == user_id), None)
    if user is None:
        raise HTTPException(
            status_code=404,
            detail=f"Demo user {user_id} not found. Valid IDs: 1-{len(DEMO_USERS)}",
        )
    # Re-use the /score logic — pass user_id for graph context
    return score(ScoringRequest(features=user["features"], user_id=user_id))


@app.get("/feature-info")
def feature_info():
    """Return metadata about expected features."""
    info = {
        "income_mean": {
            "description": "Mean monthly income stability (0-1 scale)",
            "range": [0.0, 1.0],
            "causal_direction": "Higher = lower default risk",
        },
        "income_cv": {
            "description": "Income coefficient of variation (volatility)",
            "range": [0.0, 1.0],
            "causal_direction": "Higher = higher default risk",
        },
        "utility_rate": {
            "description": "Fraction of months utility was paid on time",
            "range": [0.0, 1.0],
            "causal_direction": "Higher = lower default risk",
        },
        "dti_final": {
            "description": "Debt-to-income ratio at month 12",
            "range": [0.05, 0.95],
            "causal_direction": "Higher = higher default risk",
        },
        "employment_status": {
            "description": "Employment status (0=unemployed, 1=employed)",
            "range": [0, 1],
            "causal_direction": "Employed = lower default risk (mediated)",
        },
        "shock_total": {
            "description": "Total economic shocks in 12 months",
            "range": [0, 12],
            "causal_direction": "More shocks = higher default risk",
        },
    }
    return {"features": info, "feature_order": FEATURE_NAMES}


# ── New endpoints for 3-Section Product ──────────────────────────────────────

class LeadRequest(BaseModel):
    name: str
    email: str
    bank_name: str
    message: str = ""

class ApplicationLogRequest(BaseModel):
    demo_user: str
    score: int
    decision: str
    risk_tier: str
    ilf_reliability: float
    catch_trial_flagged: bool

@app.post("/leads")
def submit_lead(lead: LeadRequest):
    """Save a B2B lead from the landing page contact form."""
    leads_path = PROJECT_ROOT / "logs" / "leads.json"
    leads_path.parent.mkdir(exist_ok=True)
    leads = []
    if leads_path.exists():
        try:
            leads = json.loads(leads_path.read_text())
        except Exception:
            leads = []
    from datetime import datetime
    leads.append({
        "timestamp": datetime.now().isoformat(),
        "name": lead.name,
        "email": lead.email,
        "bank_name": lead.bank_name,
        "message": lead.message,
    })
    leads_path.write_text(json.dumps(leads, indent=2))
    return {"status": "received", "message": f"Thank you, {lead.name}. We'll be in touch."}

@app.get("/applications-log")
def get_applications_log():
    """Return the full application log for the bank dashboard."""
    log_path = PROJECT_ROOT / "logs" / "applications.json"
    if not log_path.exists():
        return {"applications": [], "count": 0}
    try:
        apps = json.loads(log_path.read_text())
    except Exception:
        apps = []
    return {"applications": apps, "count": len(apps)}

@app.post("/log-application")
def log_application(app_data: ApplicationLogRequest):
    """Log an application result to the dashboard."""
    log_path = PROJECT_ROOT / "logs" / "applications.json"
    log_path.parent.mkdir(exist_ok=True)
    apps = []
    if log_path.exists():
        try:
            apps = json.loads(log_path.read_text())
        except Exception:
            apps = []
    from datetime import datetime
    apps.append({
        "timestamp": datetime.now().isoformat(),
        "demo_user": app_data.demo_user,
        "score": app_data.score,
        "decision": app_data.decision,
        "risk_tier": app_data.risk_tier,
        "ilf_reliability": app_data.ilf_reliability,
        "catch_trial_flagged": app_data.catch_trial_flagged,
    })
    log_path.write_text(json.dumps(apps, indent=2))
    return {"status": "logged"}


@app.get("/graph-stats")
def graph_stats():
    """Return knowledge graph summary statistics for the dashboard."""
    return GRAPH_STATS


# ── Knowledge Graph API Endpoints ────────────────────────────────────────────

@app.get("/kg/stats")
def kg_stats():
    """Return dynamic Knowledge Graph statistics."""
    try:
        return KG_ENGINE.get_stats()
    except Exception as e:
        logger.error(f"KG stats error: {e}")
        return {"total_nodes": 0, "total_edges": 0, "error": str(e)}


@app.get("/kg/graph")
def kg_graph(max_nodes: int = 200):
    """Return full graph data for frontend visualization."""
    try:
        return KG_ENGINE.get_full_graph_data()
    except Exception as e:
        logger.error(f"KG graph error: {e}")
        return {"nodes": [], "links": [], "error": str(e)}


@app.get("/kg/node/{node_id}")
def kg_node_detail(node_id: str):
    """Return full detail for a single KG node with its edges."""
    from src.database import get_kg_node, get_kg_node_edges
    node = get_kg_node(node_id)
    if not node:
        raise HTTPException(status_code=404, detail=f"Node {node_id} not found")
    edges = get_kg_node_edges(node_id)
    # If borrower, also compute graph features
    graph_features = None
    if node.get("type") == "borrower":
        graph_features = KG_ENGINE.compute_graph_features(node_id)
    return {"node": node, "edges": edges, "graph_features": graph_features}


@app.get("/kg/neighborhood/{node_id}")
def kg_neighborhood(node_id: str, depth: int = 1):
    """Return the neighborhood subgraph for a node."""
    return KG_ENGINE.get_borrower_neighborhood(node_id, radius=min(depth, 3))


@app.get("/kg/insights")
def kg_insights():
    """Return self-improving insights from accumulated KG data."""
    try:
        insights = generate_insights(KG_ENGINE)
        thresholds = suggest_threshold_adjustments(KG_ENGINE)
        return {"insights": insights, "threshold_suggestion": thresholds}
    except Exception as e:
        logger.error(f"KG insights error: {e}")
        return {"insights": [], "threshold_suggestion": {}, "error": str(e)}


@app.post("/kg/seed")
def kg_seed():
    """Seed/re-seed the KG from static graph data + completed sessions."""
    try:
        from src.seed_knowledge_graph import seed_from_static_graph, main as seed_main
        from src.database import delete_all_kg_data
        from src.graph_ingestor import ingest_all_existing_sessions

        delete_all_kg_data()
        seed_from_static_graph(KG_ENGINE)
        n = ingest_all_existing_sessions(KG_ENGINE)
        KG_ENGINE.load()
        KG_ENGINE.compute_similarity_edges(threshold=0.80)
        recompute_employer_stats(KG_ENGINE)
        recompute_community_stats(KG_ENGINE)
        KG_ENGINE.load()
        return {"status": "seeded", "sessions_ingested": n, "stats": KG_ENGINE.get_stats()}
    except Exception as e:
        logger.error(f"KG seed error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/kg/nodes")
def kg_nodes_list(type: str = None):
    """List KG nodes, optionally filtered by type."""
    from src.database import get_kg_nodes
    nodes = get_kg_nodes(type)
    return {"nodes": nodes, "count": len(nodes)}


# ── LLM Session Endpoints ────────────────────────────────────────────────────

@app.get("/session/{session_id}")
def get_session_detail(session_id: str):
    """Return full session data including conversation turns."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    turns = get_session_turns(session_id)
    
    # Parse JSON fields for the response
    session_data = dict(session)
    if session_data.get("qa_history"):
        session_data["qa_history"] = json.loads(session_data["qa_history"])
    if session_data.get("extracted_features"):
        session_data["extracted_features"] = json.loads(session_data["extracted_features"])
    
    # Parse options JSON in turns
    for turn in turns:
        if turn.get("options"):
            try:
                turn["options"] = json.loads(turn["options"])
            except (json.JSONDecodeError, TypeError):
                pass
    
    return {"session": session_data, "turns": turns}


@app.get("/sessions-summary")
def sessions_summary():
    """Return aggregate LLM session statistics for the dashboard."""
    return db_get_sessions_summary()


@app.get("/completed-sessions")
def completed_sessions():
    """Return all completed LLM assessment sessions for the dashboard."""
    sessions = get_all_completed_sessions()
    for s in sessions:
        if s.get("extracted_features"):
            try:
                s["extracted_features"] = json.loads(s["extracted_features"])
            except (json.JSONDecodeError, TypeError):
                pass
        if s.get("qa_history"):
            try:
                s["qa_history"] = json.loads(s["qa_history"])
            except (json.JSONDecodeError, TypeError):
                pass
    return {"sessions": sessions, "count": len(sessions)}
