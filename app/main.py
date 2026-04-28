"""
FutureBank Credit — Streamlit Lending Application
===================================================
Multi-step lending flow: Welcome -> ILF Questions -> Processing -> Results
Run: streamlit run app/main.py
Requires: FastAPI backend running (uvicorn api.main:app)
"""
import sys, time, json, random
from pathlib import Path
from datetime import datetime

import streamlit as st
import requests
import numpy as np

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from src.ilf_scoring import compute_ilf_score, ILF_QUESTIONS

DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"
LOGS_DIR.mkdir(exist_ok=True)
API_URL = "http://127.0.0.1:8000"

# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FutureBank Credit",
    page_icon="logo",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
* { font-family: 'Inter', sans-serif; }
.stApp { background: linear-gradient(170deg, #0A1628 0%, #132238 50%, #0D1B2A 100%); }

/* Header */
.hero-title {
    font-size: 2.8rem; font-weight: 800; text-align: center;
    background: linear-gradient(135deg, #00BFA6, #00E5CC, #00BFA6);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin-bottom: 0.2rem; letter-spacing: -0.5px;
}
.hero-sub {
    text-align: center; color: #8899AA; font-size: 1.1rem;
    margin-bottom: 2rem; font-weight: 300;
}

/* Cards */
.glass-card {
    background: rgba(19, 34, 56, 0.7); border: 1px solid rgba(0,191,166,0.15);
    border-radius: 16px; padding: 2rem; margin: 1rem 0;
    backdrop-filter: blur(12px); box-shadow: 0 8px 32px rgba(0,0,0,0.3);
}
.glass-card-accent {
    background: rgba(0,191,166,0.08); border: 1px solid rgba(0,191,166,0.3);
    border-radius: 16px; padding: 2rem; margin: 1rem 0;
    backdrop-filter: blur(12px);
}

/* Score display */
.score-big {
    font-size: 5rem; font-weight: 800; text-align: center;
    background: linear-gradient(135deg, #00BFA6, #00E5CC);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    line-height: 1.1; margin: 0.5rem 0;
}
.score-label {
    text-align: center; font-size: 1rem; color: #8899AA;
    text-transform: uppercase; letter-spacing: 3px; font-weight: 600;
}

/* Decision badges */
.badge-standard {
    display: inline-block; padding: 0.5rem 1.5rem; border-radius: 50px;
    background: linear-gradient(135deg, #00BFA6, #00E5CC); color: #0A1628;
    font-weight: 700; font-size: 1.1rem; letter-spacing: 1px;
}
.badge-nano {
    display: inline-block; padding: 0.5rem 1.5rem; border-radius: 50px;
    background: linear-gradient(135deg, #F59E0B, #FBBF24); color: #0A1628;
    font-weight: 700; font-size: 1.1rem; letter-spacing: 1px;
}
.badge-decline {
    display: inline-block; padding: 0.5rem 1.5rem; border-radius: 50px;
    background: linear-gradient(135deg, #EF4444, #F87171); color: white;
    font-weight: 700; font-size: 1.1rem; letter-spacing: 1px;
}

/* Question card */
.q-card {
    background: rgba(19,34,56,0.8); border: 1px solid rgba(0,191,166,0.2);
    border-radius: 20px; padding: 2.5rem; margin: 1.5rem 0;
    text-align: center; box-shadow: 0 12px 40px rgba(0,0,0,0.4);
}
.q-text {
    font-size: 1.4rem; color: #E8ECF1; font-weight: 500;
    line-height: 1.6; margin-bottom: 1.5rem;
}
.q-counter {
    color: #00BFA6; font-size: 0.85rem; font-weight: 600;
    letter-spacing: 2px; text-transform: uppercase; margin-bottom: 1rem;
}

/* Product offer */
.offer-amount {
    font-size: 3rem; font-weight: 800; text-align: center;
    color: #00E5CC; margin: 0.5rem 0;
}
.offer-label {
    text-align: center; color: #8899AA; font-size: 0.9rem;
    text-transform: uppercase; letter-spacing: 2px;
}

/* ILF badge */
.ilf-badge {
    display: inline-block; padding: 0.3rem 1rem; border-radius: 50px;
    font-size: 0.85rem; font-weight: 600;
}
.ilf-high { background: rgba(0,191,166,0.15); color: #00E5CC; border: 1px solid rgba(0,191,166,0.3); }
.ilf-moderate { background: rgba(245,158,11,0.15); color: #FBBF24; border: 1px solid rgba(245,158,11,0.3); }
.ilf-low { background: rgba(239,68,68,0.15); color: #F87171; border: 1px solid rgba(239,68,68,0.3); }

/* Contribution bars */
.contrib-bar-pos { background: linear-gradient(90deg, rgba(239,68,68,0.3), rgba(239,68,68,0.7)); border-radius: 4px; padding: 4px 8px; margin: 2px 0; color: #F87171; font-size: 0.85rem; }
.contrib-bar-neg { background: linear-gradient(90deg, rgba(0,191,166,0.3), rgba(0,191,166,0.7)); border-radius: 4px; padding: 4px 8px; margin: 2px 0; color: #00E5CC; font-size: 0.85rem; }

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #00BFA6, #00997D) !important;
    color: #0A1628 !important; font-weight: 700 !important;
    border: none !important; border-radius: 12px !important;
    padding: 0.7rem 2rem !important; font-size: 1rem !important;
    letter-spacing: 0.5px !important; transition: all 0.3s ease !important;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #00E5CC, #00BFA6) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 25px rgba(0,191,166,0.3) !important;
}

/* Hide hamburger */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ── Session State Init ────────────────────────────────────────────────────────
defaults = {
    "step": 0,
    "consent": False,
    "current_q": 0,
    "answers": [],
    "latencies": [],
    "q_render_time": None,
    "selected_user": None,
    "api_result": None,
    "ilf_result": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ── Helper Functions ──────────────────────────────────────────────────────────

def load_demo_users():
    path = DATA_DIR / "demo_users.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return []

def call_scoring_api(features: dict) -> dict:
    try:
        r = requests.post(f"{API_URL}/score", json={"features": features}, timeout=10)
        if r.status_code == 200:
            return r.json()
        return None
    except Exception:
        return None

def log_application(user, result, ilf):
    log_path = LOGS_DIR / "applications.json"
    entry = {
        "timestamp": datetime.now().isoformat(),
        "demo_user": user.get("name", "Unknown"),
        "user_id": user.get("id"),
        "score": result.get("score"),
        "probability": result.get("probability"),
        "decision": result.get("decision"),
        "risk_tier": result.get("risk_tier"),
        "ilf_reliability": ilf.get("reliability_score"),
        "ilf_label": ilf.get("reliability_label"),
        "catch_trial_flagged": ilf.get("catch_trial_flagged"),
        "latencies": ilf.get("latencies_sec"),
    }
    logs = []
    if log_path.exists():
        try:
            logs = json.loads(log_path.read_text())
        except Exception:
            logs = []
    logs.append(entry)
    log_path.write_text(json.dumps(logs, indent=2))

FEATURE_LABELS = {
    "income_mean": ("Income Stability", "Higher income = lower risk"),
    "income_cv": ("Income Volatility", "Higher volatility = higher risk"),
    "utility_rate": ("Bill Payment History", "Consistent payments = lower risk"),
    "dti_final": ("Debt-to-Income Ratio", "More debt relative to income = higher risk"),
    "employment_status": ("Employment Status", "Employment reduces risk"),
    "shock_total": ("Financial Shocks", "More shocks = higher risk"),
}


# ══════════════════════════════════════════════════════════════════════════════
#  STEP 0: Welcome / Consent
# ══════════════════════════════════════════════════════════════════════════════

def render_welcome():
    st.markdown('<p class="hero-title">FutureBank Credit</p>', unsafe_allow_html=True)
    st.markdown('<p class="hero-sub">Instant, fair, recession-proof lending powered by causal AI</p>', unsafe_allow_html=True)

    st.markdown("""
    <div class="glass-card" style="text-align:center;">
        <h3 style="color:#00BFA6; margin-top:0;">How It Works</h3>
        <div style="display:flex; justify-content:space-around; flex-wrap:wrap; gap:1rem; margin:1.5rem 0;">
            <div style="flex:1; min-width:150px;">
                <div style="font-size:2rem;">&#128221;</div>
                <p style="color:#E8ECF1; font-weight:600;">1. Quick Check</p>
                <p style="color:#8899AA; font-size:0.85rem;">3 simple questions<br>about your finances</p>
            </div>
            <div style="flex:1; min-width:150px;">
                <div style="font-size:2rem;">&#129504;</div>
                <p style="color:#E8ECF1; font-weight:600;">2. AI Analysis</p>
                <p style="color:#8899AA; font-size:0.85rem;">Causal model evaluates<br>your financial health</p>
            </div>
            <div style="flex:1; min-width:150px;">
                <div style="font-size:2rem;">&#9989;</div>
                <p style="color:#E8ECF1; font-weight:600;">3. Instant Offer</p>
                <p style="color:#8899AA; font-size:0.85rem;">Get your credit decision<br>in seconds</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    consent = st.checkbox(
        "I consent to this assessment and understand my data will be processed securely.",
        key="consent_check",
    )
    st.markdown('</div>', unsafe_allow_html=True)

    # Demo user selection
    users = load_demo_users()
    if users:
        st.markdown("**Select a demo profile** (each has different financial characteristics):")
        options = [f"{u['name']} - {u['risk_tier']} Risk" for u in users]
        choice = st.selectbox("Choose a profile:", options, key="user_select", label_visibility="collapsed")
        idx = options.index(choice)
        st.session_state.selected_user = users[idx]

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("Start Assessment", use_container_width=True, disabled=not consent):
            st.session_state.step = 1
            st.session_state.consent = True
            st.session_state.current_q = 0
            st.session_state.answers = []
            st.session_state.latencies = []
            st.session_state.q_render_time = time.perf_counter()
            if not st.session_state.selected_user and users:
                st.session_state.selected_user = random.choice(users)
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
#  STEP 1: ILF Questions (one at a time with timing)
# ══════════════════════════════════════════════════════════════════════════════

def render_ilf_questions():
    questions = ILF_QUESTIONS
    q_idx = st.session_state.current_q

    if q_idx >= len(questions):
        st.session_state.step = 2
        st.rerun()
        return

    # Record render time for this question
    if st.session_state.q_render_time is None:
        st.session_state.q_render_time = time.perf_counter()

    q = questions[q_idx]

    # Progress
    progress = (q_idx) / len(questions)
    st.progress(progress, text=f"Question {q_idx + 1} of {len(questions)}")

    st.markdown(f"""
    <div class="q-card">
        <div class="q-counter">Question {q_idx + 1} of {len(questions)}</div>
        <div class="q-text">"{q['text']}"</div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        answer = st.radio(
            "Your response:",
            q["options"],
            key=f"radio_q{q_idx}",
            horizontal=True,
            label_visibility="collapsed",
        )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("Submit Answer", key=f"submit_q{q_idx}", use_container_width=True):
            t_click = time.perf_counter()
            latency = t_click - st.session_state.q_render_time

            st.session_state.latencies.append(latency)
            st.session_state.answers.append(answer)
            st.session_state.current_q += 1
            st.session_state.q_render_time = time.perf_counter()
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
#  STEP 2: Processing (API call + ILF scoring)
# ══════════════════════════════════════════════════════════════════════════════

def render_processing():
    st.markdown('<p class="hero-title" style="font-size:2rem;">Analysing Your Profile</p>', unsafe_allow_html=True)

    progress_bar = st.progress(0)
    status = st.empty()

    # Step 1: Compute ILF
    status.markdown("**Computing response reliability...**")
    progress_bar.progress(25)
    ilf_result = compute_ilf_score(
        st.session_state.latencies,
        st.session_state.answers,
        ILF_QUESTIONS,
    )
    st.session_state.ilf_result = ilf_result
    time.sleep(0.5)

    # Step 2: Call API
    status.markdown("**Running causal credit analysis...**")
    progress_bar.progress(50)
    user = st.session_state.selected_user
    if user:
        api_result = call_scoring_api(user["features"])
    else:
        api_result = None
    time.sleep(0.5)

    # Step 3: Finalise
    status.markdown("**Preparing your offer...**")
    progress_bar.progress(75)
    time.sleep(0.3)

    if api_result:
        st.session_state.api_result = api_result
        # Log the application
        log_application(user, api_result, ilf_result)
        progress_bar.progress(100)
        status.markdown("**Done!**")
        time.sleep(0.3)
        st.session_state.step = 3
        st.rerun()
    else:
        progress_bar.progress(100)
        st.error("Could not reach the scoring API. Make sure it's running: `uvicorn api.main:app`")
        if st.button("Retry"):
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
#  STEP 3: Results + Forensic Mode
# ══════════════════════════════════════════════════════════════════════════════

def render_results():
    result = st.session_state.api_result
    ilf = st.session_state.ilf_result
    user = st.session_state.selected_user

    if not result:
        st.error("No results available.")
        return

    score = result["score"]
    decision = result["decision"]
    risk_tier = result["risk_tier"]
    probability = result["probability"]

    # ── Score Display ─────────────────────────────────────────────────────
    st.markdown('<p class="score-label">Your Credit Score</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="score-big">{score}</p>', unsafe_allow_html=True)

    # Decision badge
    badge_class = {"STANDARD": "badge-standard", "NANO_CREDIT": "badge-nano", "DECLINE": "badge-decline"}
    badge_text = {"STANDARD": "APPROVED - Standard Credit", "NANO_CREDIT": "APPROVED - Nano Credit", "DECLINE": "APPLICATION DECLINED"}
    st.markdown(f'<p style="text-align:center;"><span class="{badge_class[decision]}">{badge_text[decision]}</span></p>', unsafe_allow_html=True)

    # ── Product Offer Card ────────────────────────────────────────────────
    st.markdown("")
    if decision == "STANDARD":
        st.markdown(f"""
        <div class="glass-card-accent" style="text-align:center;">
            <p class="offer-label">Your Credit Line</p>
            <p class="offer-amount">Rs 5,000</p>
            <p style="color:#8899AA;">Standard credit with competitive rates</p>
            <p style="color:#00BFA6; font-weight:600;">No insurance required</p>
        </div>""", unsafe_allow_html=True)
    elif decision == "NANO_CREDIT":
        st.markdown(f"""
        <div class="glass-card-accent" style="text-align:center;">
            <p class="offer-label">Your Credit Line</p>
            <p class="offer-amount">Rs 1,000</p>
            <p style="color:#8899AA;">Nano credit with bundled protection</p>
            <p style="color:#FBBF24; font-weight:600;">Includes micro-insurance for payment protection</p>
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="glass-card" style="text-align:center;">
            <p style="color:#F87171; font-weight:700; font-size:1.2rem;">We're unable to offer credit at this time</p>
            <p style="color:#8899AA;">Your financial profile suggests elevated risk.<br>Consider reducing debt or building payment history.</p>
        </div>""", unsafe_allow_html=True)

    # ── ILF Reliability Badge ─────────────────────────────────────────────
    if ilf:
        ilf_class = {"High": "ilf-high", "Moderate": "ilf-moderate", "Low": "ilf-low"}
        ilf_label = ilf.get("reliability_label", "Low")
        ilf_pct = ilf.get("reliability_pct", 0)
        caught = ilf.get("catch_trial_flagged", False)

        st.markdown(f"""
        <div class="glass-card" style="text-align:center;">
            <p style="color:#8899AA; font-size:0.85rem; text-transform:uppercase; letter-spacing:2px;">Response Consistency</p>
            <p style="font-size:2rem; font-weight:700; color:#E8ECF1; margin:0.3rem 0;">{ilf_pct}%</p>
            <span class="ilf-badge {ilf_class[ilf_label]}">{ilf_label} Reliability</span>
            {'<p style="color:#F87171; font-size:0.85rem; margin-top:0.8rem;">&#9888; Catch trial flagged</p>' if caught else ''}
        </div>""", unsafe_allow_html=True)

    # ── Forensic Mode (Why?) ──────────────────────────────────────────────
    with st.expander("Why this decision?", expanded=False):
        st.markdown("#### Feature Contributions")
        st.markdown("Each factor's influence on your credit score:")
        st.markdown("")

        contribs = result.get("contributions", {})
        if contribs:
            sorted_contribs = sorted(contribs.items(), key=lambda x: abs(x[1]), reverse=True)
            max_abs = max(abs(v) for _, v in sorted_contribs) if sorted_contribs else 1

            for feat, val in sorted_contribs:
                label, desc = FEATURE_LABELS.get(feat, (feat, ""))
                direction = "Risk-increasing" if val > 0 else "Risk-reducing"
                bar_class = "contrib-bar-pos" if val > 0 else "contrib-bar-neg"
                width = int(min(abs(val) / max_abs * 100, 100))
                icon = "&#9650;" if val > 0 else "&#9660;"

                st.markdown(f"""
                <div style="margin-bottom:0.8rem;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="color:#E8ECF1; font-weight:600;">{label}</span>
                        <span style="color:#8899AA; font-size:0.8rem;">{direction} ({val:+.3f})</span>
                    </div>
                    <div class="{bar_class}" style="width:{max(width, 8)}%;">{icon} {desc}</div>
                </div>""", unsafe_allow_html=True)

        # ILF details
        if ilf:
            st.markdown("---")
            st.markdown("#### Response Analysis")
            for i, (lat, sc) in enumerate(zip(ilf.get("latencies_sec", []), ilf.get("per_question_scores", []))):
                q_label = ILF_QUESTIONS[i]["text"][:50] + "..." if i < len(ILF_QUESTIONS) else f"Q{i+1}"
                st.markdown(f"- **Q{i+1}**: {lat:.1f}s (reliability: {sc:.2f})")
            st.markdown(f"- **Twin-pair consistency**: {ilf.get('delta_penalty', 0):.2f}")
            st.markdown(f"- **Formula**: `{ilf.get('details', {}).get('formula', 'N/A')}`")

        st.markdown("---")
        st.markdown(f"**Default probability**: {probability:.4f}")
        st.markdown(f"**Risk tier**: {risk_tier}")
        if user:
            st.markdown(f"**Profile**: {user.get('name', 'Unknown')}")

    # ── Restart ───────────────────────────────────────────────────────────
    st.markdown("")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("Start New Assessment", use_container_width=True):
            for k in defaults:
                st.session_state[k] = defaults[k]
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
#  Router
# ══════════════════════════════════════════════════════════════════════════════

step = st.session_state.step
if step == 0:
    render_welcome()
elif step == 1:
    render_ilf_questions()
elif step == 2:
    render_processing()
elif step == 3:
    render_results()
