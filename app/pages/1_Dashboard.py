"""
FutureBank Admin Dashboard
===========================
Bank-side view: application log, model health, CPS alerts, score distribution.
"""
import json
from pathlib import Path
from datetime import datetime

import streamlit as st
import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LOGS_DIR = PROJECT_ROOT / "logs"
REPORTS_DIR = PROJECT_ROOT / "reports"

st.set_page_config(page_title="FutureBank Dashboard", page_icon="chart", layout="wide", initial_sidebar_state="collapsed")

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
* { font-family: 'Inter', sans-serif; }
.stApp { background: linear-gradient(170deg, #0A1628 0%, #132238 50%, #0D1B2A 100%); }
.metric-card {
    background: rgba(19,34,56,0.7); border: 1px solid rgba(0,191,166,0.15);
    border-radius: 14px; padding: 1.5rem; text-align: center;
    backdrop-filter: blur(12px); box-shadow: 0 6px 24px rgba(0,0,0,0.3);
}
.metric-value { font-size: 2.2rem; font-weight: 800; color: #00E5CC; }
.metric-label { font-size: 0.8rem; color: #8899AA; text-transform: uppercase; letter-spacing: 2px; margin-top: 0.3rem; }
.alert-box {
    background: rgba(239,68,68,0.1); border: 1px solid rgba(239,68,68,0.3);
    border-radius: 10px; padding: 1rem 1.2rem; margin: 0.5rem 0;
    color: #F87171; font-size: 0.9rem;
}
.ok-box {
    background: rgba(0,191,166,0.1); border: 1px solid rgba(0,191,166,0.3);
    border-radius: 10px; padding: 1rem 1.2rem; margin: 0.5rem 0;
    color: #00E5CC; font-size: 0.9rem;
}
.dash-title {
    font-size: 2rem; font-weight: 800;
    background: linear-gradient(135deg, #00BFA6, #00E5CC);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin-bottom: 0.2rem;
}
.dash-sub { color: #8899AA; font-size: 0.95rem; margin-bottom: 1.5rem; }
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ── Load Application Logs ─────────────────────────────────────────────────────

def load_logs():
    path = LOGS_DIR / "applications.json"
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            return []
    return []


# ── Header ────────────────────────────────────────────────────────────────────

st.markdown('<p class="dash-title">FutureBank Admin Dashboard</p>', unsafe_allow_html=True)
st.markdown('<p class="dash-sub">Model health, application monitoring, and CPS alerts</p>', unsafe_allow_html=True)

logs = load_logs()

# ── KPI Cards ─────────────────────────────────────────────────────────────────

if logs:
    df = pd.DataFrame(logs)
    total_apps = len(df)
    avg_score = df["score"].mean() if "score" in df.columns else 0
    approval_rate = (df["decision"].isin(["STANDARD", "NANO_CREDIT"]).sum() / total_apps * 100) if total_apps > 0 else 0
    avg_ilf = df["ilf_reliability"].mean() if "ilf_reliability" in df.columns else 0
    catch_rate = (df["catch_trial_flagged"].sum() / total_apps * 100) if "catch_trial_flagged" in df.columns and total_apps > 0 else 0

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{total_apps}</div><div class="metric-label">Applications</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{avg_score:.0f}</div><div class="metric-label">Avg Score</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{approval_rate:.0f}%</div><div class="metric-label">Approval Rate</div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{avg_ilf:.0%}</div><div class="metric-label">Avg ILF Score</div></div>', unsafe_allow_html=True)
    with c5:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{catch_rate:.0f}%</div><div class="metric-label">Catch Flagged</div></div>', unsafe_allow_html=True)
else:
    st.info("No applications logged yet. Complete an assessment in the main app to see data here.")

st.markdown("---")

# ── Two Column Layout ─────────────────────────────────────────────────────────

col_left, col_right = st.columns([3, 2])

with col_left:
    st.markdown("### Recent Applications")
    if logs:
        display_df = df[["timestamp", "demo_user", "score", "decision", "risk_tier", "ilf_reliability", "catch_trial_flagged"]].copy()
        display_df.columns = ["Timestamp", "Applicant", "Score", "Decision", "Risk", "ILF Score", "Catch Flag"]
        display_df["Timestamp"] = pd.to_datetime(display_df["Timestamp"]).dt.strftime("%Y-%m-%d %H:%M")
        display_df["ILF Score"] = display_df["ILF Score"].apply(lambda x: f"{x:.2f}" if pd.notnull(x) else "N/A")
        display_df = display_df.sort_index(ascending=False)
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    else:
        st.markdown("*No applications yet.*")

    # Score Distribution
    if logs and "score" in df.columns and len(df) > 1:
        st.markdown("### Score Distribution")
        chart_data = pd.DataFrame({"Score": df["score"]})
        st.bar_chart(chart_data.value_counts().sort_index(), color="#00BFA6")

with col_right:
    # ── Model Health Panel ────────────────────────────────────────────────
    st.markdown("### Model Health")

    # Load recession test results if available
    recession_path = REPORTS_DIR / "recession_stress_test_results.csv"
    if recession_path.exists():
        recession_df = pd.read_csv(recession_path)
        for _, row in recession_df.iterrows():
            status = row.get("Stability", "UNKNOWN")
            model_name = row.get("Model", "")
            auc_n = row.get("AUC_Normal", 0)
            auc_r = row.get("AUC_Recession", 0)
            if status == "STABLE":
                st.markdown(f'<div class="ok-box">&#9989; <b>{model_name}</b><br>Normal: {auc_n:.4f} | Recession: {auc_r:.4f} | {status}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="alert-box">&#9888; <b>{model_name}</b><br>Normal: {auc_n:.4f} | Recession: {auc_r:.4f} | {status}</div>', unsafe_allow_html=True)
    else:
        st.markdown("*Recession test results not found.*")

    # ── CPS Drift Alerts (Simulated) ──────────────────────────────────────
    st.markdown("### CPS Drift Alerts")
    st.markdown("""
    <div class="alert-box">&#9888; <b>dark_mode_user</b> — CPS dropped to 0.35 (was 0.72). Spurious correlation reversal detected.</div>
    <div class="alert-box">&#9888; <b>social_media_score</b> — CPS dropped to 0.28 (was 0.65). Feature drifting under recession regime.</div>
    <div class="ok-box">&#9989; <b>income_mean</b> — CPS stable at 0.91. Causal feature holding.</div>
    <div class="ok-box">&#9989; <b>utility_rate</b> — CPS stable at 0.88. Causal feature holding.</div>
    <div class="ok-box">&#9989; <b>dti_final</b> — CPS stable at 0.85. Causal feature holding.</div>
    """, unsafe_allow_html=True)

    # ── ILF Summary ───────────────────────────────────────────────────────
    if logs and "ilf_reliability" in df.columns:
        st.markdown("### ILF Summary")
        ilf_vals = df["ilf_reliability"].dropna()
        if len(ilf_vals) > 0:
            high_r = (ilf_vals > 0.85).sum()
            mod_r = ((ilf_vals > 0.60) & (ilf_vals <= 0.85)).sum()
            low_r = (ilf_vals <= 0.60).sum()
            st.markdown(f"""
            <div class="ok-box">&#9989; High reliability: <b>{high_r}</b> sessions</div>
            <div style="background:rgba(245,158,11,0.1);border:1px solid rgba(245,158,11,0.3);border-radius:10px;padding:1rem 1.2rem;margin:0.5rem 0;color:#FBBF24;font-size:0.9rem;">&#9888; Moderate reliability: <b>{mod_r}</b> sessions</div>
            {'<div class="alert-box">&#9888; Low reliability: <b>' + str(low_r) + '</b> sessions</div>' if low_r > 0 else ''}
            """, unsafe_allow_html=True)

# ── Recession Test Chart ──────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### Recession Stress Test Visualization")
chart_path = REPORTS_DIR / "recession_test.png"
if chart_path.exists():
    st.image(str(chart_path), use_container_width=True)
else:
    st.markdown("*Recession test chart not found. Run `python src/run_pipeline.py` to generate.*")
