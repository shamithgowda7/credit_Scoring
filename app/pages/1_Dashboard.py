"""
FutureBank Admin Dashboard
===========================
Bank-side view: application log, model health, CPS alerts, score distribution,
and dynamic portfolio feedback (closed-loop threshold management).
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
THRESHOLDS_PATH = PROJECT_ROOT / "thresholds.json"

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


# ══════════════════════════════════════════════════════════════════════════════
#  PORTFOLIO PERFORMANCE — Dynamic Threshold Feedback Loop
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("---")

# ── Load live thresholds from config ──────────────────────────────────────────

def load_thresholds_config() -> dict:
    """Load the full thresholds.json config used by the API."""
    defaults = {
        "thresholds": {"DECLINE_UPPER": 400, "NANO_CREDIT_UPPER": 700},
        "risk_appetite": {"nano_credit_max_default_rate": 0.03, "standard_max_default_rate": 0.01},
        "adjustment_rules": {
            "tighten_step": 20, "relax_step": 10,
            "min_decline_upper": 350, "max_decline_upper": 500,
            "min_nano_upper": 600, "max_nano_upper": 800,
        },
    }
    if THRESHOLDS_PATH.exists():
        try:
            return json.loads(THRESHOLDS_PATH.read_text())
        except Exception:
            pass
    return defaults

cfg = load_thresholds_config()
thresholds = cfg.get("thresholds", {})
risk_appetite = cfg.get("risk_appetite", {})
adj_rules = cfg.get("adjustment_rules", {})

DECLINE_UPPER = thresholds.get("DECLINE_UPPER", 400)
NANO_UPPER = thresholds.get("NANO_CREDIT_UPPER", 700)

# ── Section Header ────────────────────────────────────────────────────────────

st.markdown("""
<div style="display:flex; align-items:center; gap:0.7rem; margin-bottom:0.3rem;">
    <span style="font-size:1.8rem;">&#127919;</span>
    <span class="dash-title" style="font-size:1.6rem;">Portfolio Performance &amp; Dynamic Thresholds</span>
</div>
<p class="dash-sub">
    Closed-loop feedback: thresholds auto-adjust based on actual default rates vs. risk appetite.
</p>
""", unsafe_allow_html=True)

# ── Simulated Portfolio Data ──────────────────────────────────────────────────
# In production these would come from a nightly batch job over the loan book.
# Here we use static simulated values to demonstrate the concept.

portfolio_data = [
    {
        "band": "DECLINE",
        "score_range": f"300 – {DECLINE_UPPER - 1}",
        "current_threshold": f"< {DECLINE_UPPER}",
        "sim_default_rate": 0.12,
        "risk_appetite": "N/A (declined)",
        "volume": 834,
        "status": "BLOCKED",
    },
    {
        "band": "NANO CREDIT",
        "score_range": f"{DECLINE_UPPER} – {NANO_UPPER - 1}",
        "current_threshold": f"{DECLINE_UPPER} – {NANO_UPPER}",
        "sim_default_rate": 0.027,
        "risk_appetite": f"{risk_appetite.get('nano_credit_max_default_rate', 0.03):.1%}",
        "volume": 2_146,
        "status": "OK",
    },
    {
        "band": "STANDARD",
        "score_range": f"{NANO_UPPER} – 900",
        "current_threshold": f"≥ {NANO_UPPER}",
        "sim_default_rate": 0.008,
        "risk_appetite": f"{risk_appetite.get('standard_max_default_rate', 0.01):.1%}",
        "volume": 4_012,
        "status": "OK",
    },
]

# ── Render the portfolio table ────────────────────────────────────────────────

p_col1, p_col2 = st.columns([3, 2])

with p_col1:
    st.markdown("#### Score Bands & Simulated Default Rates")

    table_rows = ""
    for row in portfolio_data:
        rate_pct = f"{row['sim_default_rate']:.1%}"

        if row["status"] == "BLOCKED":
            status_badge = '<span style="background:rgba(239,68,68,0.15);color:#F87171;padding:3px 10px;border-radius:20px;font-size:0.75rem;font-weight:600;">&#9940; BLOCKED</span>'
            rate_color = "#F87171"
        elif row["status"] == "BREACH":
            status_badge = '<span style="background:rgba(245,158,11,0.15);color:#FBBF24;padding:3px 10px;border-radius:20px;font-size:0.75rem;font-weight:600;">&#9888; BREACH</span>'
            rate_color = "#FBBF24"
        else:
            status_badge = '<span style="background:rgba(0,191,166,0.15);color:#00E5CC;padding:3px 10px;border-radius:20px;font-size:0.75rem;font-weight:600;">&#9989; OK</span>'
            rate_color = "#00E5CC"

        table_rows += f"""
        <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
            <td style="padding:10px 12px;color:#E8ECF1;font-weight:600;">{row['band']}</td>
            <td style="padding:10px 12px;color:#8899AA;">{row['score_range']}</td>
            <td style="padding:10px 12px;color:{rate_color};font-weight:700;">{rate_pct}</td>
            <td style="padding:10px 12px;color:#8899AA;">{row['risk_appetite']}</td>
            <td style="padding:10px 12px;color:#8899AA;">{row['volume']:,}</td>
            <td style="padding:10px 12px;">{status_badge}</td>
        </tr>"""

    st.markdown(f"""
    <div style="background:rgba(19,34,56,0.7);border:1px solid rgba(0,191,166,0.15);border-radius:14px;overflow:hidden;backdrop-filter:blur(12px);box-shadow:0 6px 24px rgba(0,0,0,0.3);">
        <table style="width:100%;border-collapse:collapse;">
            <thead>
                <tr style="border-bottom:2px solid rgba(0,191,166,0.2);">
                    <th style="padding:12px;color:#00BFA6;text-align:left;font-size:0.8rem;text-transform:uppercase;letter-spacing:1px;">Band</th>
                    <th style="padding:12px;color:#00BFA6;text-align:left;font-size:0.8rem;text-transform:uppercase;letter-spacing:1px;">Score Range</th>
                    <th style="padding:12px;color:#00BFA6;text-align:left;font-size:0.8rem;text-transform:uppercase;letter-spacing:1px;">Default Rate</th>
                    <th style="padding:12px;color:#00BFA6;text-align:left;font-size:0.8rem;text-transform:uppercase;letter-spacing:1px;">Risk Appetite</th>
                    <th style="padding:12px;color:#00BFA6;text-align:left;font-size:0.8rem;text-transform:uppercase;letter-spacing:1px;">Volume</th>
                    <th style="padding:12px;color:#00BFA6;text-align:left;font-size:0.8rem;text-transform:uppercase;letter-spacing:1px;">Status</th>
                </tr>
            </thead>
            <tbody>
                {table_rows}
            </tbody>
        </table>
    </div>
    """, unsafe_allow_html=True)

with p_col2:
    st.markdown("#### Current Thresholds")
    st.markdown(f"""
    <div class="metric-card" style="margin-bottom:1rem;">
        <div style="color:#8899AA;font-size:0.75rem;text-transform:uppercase;letter-spacing:2px;">Decline Boundary</div>
        <div style="font-size:2.5rem;font-weight:800;color:#F87171;">&lt; {DECLINE_UPPER}</div>
        <div style="color:#8899AA;font-size:0.8rem;margin-top:0.3rem;">Scores below this are declined</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown(f"""
    <div class="metric-card" style="margin-bottom:1rem;">
        <div style="color:#8899AA;font-size:0.75rem;text-transform:uppercase;letter-spacing:2px;">Nano → Standard Boundary</div>
        <div style="font-size:2.5rem;font-weight:800;color:#FBBF24;">{NANO_UPPER}</div>
        <div style="color:#8899AA;font-size:0.8rem;margin-top:0.3rem;">Below = Nano Credit &nbsp;|&nbsp; Above = Standard</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown(f"""
    <div class="metric-card">
        <div style="color:#8899AA;font-size:0.75rem;text-transform:uppercase;letter-spacing:2px;">Last Updated</div>
        <div style="font-size:1.1rem;font-weight:600;color:#00E5CC;margin-top:0.5rem;">{cfg.get('last_updated', 'N/A')}</div>
        <div style="color:#8899AA;font-size:0.8rem;margin-top:0.3rem;">by {cfg.get('updated_by', 'system_init')}</div>
    </div>
    """, unsafe_allow_html=True)

# ── Threshold Adjustment Demonstration ────────────────────────────────────────

st.markdown("")
st.markdown("""
<div style="background:rgba(245,158,11,0.08);border:1px solid rgba(245,158,11,0.25);border-radius:14px;padding:1.5rem 2rem;margin:1rem 0;">
    <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.8rem;">
        <span style="font-size:1.3rem;">&#128300;</span>
        <span style="color:#FBBF24;font-weight:700;font-size:1.05rem;">Demonstration: Automatic Threshold Adjustment</span>
    </div>
    <p style="color:#E8ECF1;font-size:0.92rem;line-height:1.7;margin:0;">
        If the <b>Nano Credit default rate exceeds 3%</b>, the system would automatically
        <b>reduce the DECLINE threshold from {decline} to {tightened}</b> to tighten approvals —
        moving borderline borrowers into the Decline band.
        Conversely, if losses stay well below appetite, the threshold <b>relaxes by
        {relax}-point steps</b> to serve more borrowers.
        This creates a <em>self-correcting feedback loop</em> that aligns the model with
        real-world portfolio outcomes without manual recalibration.
    </p>
</div>
""".format(
    decline=DECLINE_UPPER,
    tightened=min(DECLINE_UPPER + adj_rules.get("tighten_step", 20), adj_rules.get("max_decline_upper", 500)),
    relax=adj_rules.get("relax_step", 10),
), unsafe_allow_html=True)

# ── Expander: How Thresholds Self-Adjust ──────────────────────────────────────

with st.expander("🔄 How thresholds self-adjust", expanded=False):
    st.markdown("""
    #### Closed-Loop Portfolio Feedback

    The decision boundaries for **DECLINE** and **NANO_CREDIT** are **not static** —
    they adjust based on the bank's actual loss experience:

    | Scenario | Action | Example |
    |----------|--------|---------|
    | Default rate **exceeds** risk appetite | **Tighten** threshold (↑ by {tighten} pts) | DECLINE boundary moves from 400 → 420 |
    | Default rate **well below** appetite | **Relax** threshold (↓ by {relax} pts) | DECLINE boundary moves from 400 → 390 |
    | Default rate **at or near** appetite | **Hold** — no change | Boundary stays at 400 |

    **Guardrails** ensure thresholds never drift beyond safe bounds:
    - DECLINE boundary: **{min_d}** – **{max_d}**
    - Nano→Standard boundary: **{min_n}** – **{max_n}**

    ---

    #### Why This Matters

    1. **Aligns the model with business outcomes** — return on equity, loss rates, and
       capital reserves drive the boundaries, not arbitrary cut-offs.
    2. **Creates a real feedback loop** — safer lending → more repayment data →
       even safer lending → lower cost of capital.
    3. **Autonomous optimisation** — the system self-adjusts like a Palantir-style
       operating system, without manual recalibration every quarter.

    ---

    #### Simulated Threshold Evolution (Mock Data)
    """.format(
        tighten=adj_rules.get("tighten_step", 20),
        relax=adj_rules.get("relax_step", 10),
        min_d=adj_rules.get("min_decline_upper", 350),
        max_d=adj_rules.get("max_decline_upper", 500),
        min_n=adj_rules.get("min_nano_upper", 600),
        max_n=adj_rules.get("max_nano_upper", 800),
    ))

    # ── Mock quarterly threshold evolution chart ──────────────────────────
    quarters = ["Q1 2025", "Q2 2025", "Q3 2025", "Q4 2025", "Q1 2026", "Q2 2026"]
    decline_history = [400, 400, 420, 420, 410, 400]      # tightened Q3, relaxed Q1-Q2 2026
    nano_history    = [700, 700, 700, 720, 720, 710]      # tightened Q4, relaxed Q2 2026

    chart_df = pd.DataFrame({
        "Quarter": quarters * 2,
        "Threshold": decline_history + nano_history,
        "Boundary": (["Decline Upper"] * len(quarters)) + (["Nano → Standard"] * len(quarters)),
    })

    import altair as alt  # noqa: E402

    threshold_chart = (
        alt.Chart(chart_df)
        .mark_line(point=True, strokeWidth=3)
        .encode(
            x=alt.X("Quarter:N", title="Quarter", sort=quarters,
                     axis=alt.Axis(labelColor="#8899AA", titleColor="#8899AA")),
            y=alt.Y("Threshold:Q", title="Score Threshold",
                     scale=alt.Scale(domain=[350, 750]),
                     axis=alt.Axis(labelColor="#8899AA", titleColor="#8899AA")),
            color=alt.Color("Boundary:N",
                            scale=alt.Scale(
                                domain=["Decline Upper", "Nano → Standard"],
                                range=["#F87171", "#FBBF24"],
                            ),
                            legend=alt.Legend(
                                title="Boundary",
                                labelColor="#8899AA",
                                titleColor="#8899AA",
                            )),
            tooltip=["Quarter", "Boundary", "Threshold"],
        )
        .properties(height=320)
        .configure_view(strokeWidth=0)
        .configure(background="rgba(0,0,0,0)")
    )

    st.altair_chart(threshold_chart, use_container_width=True)

    st.markdown("""
    > **Note:** The chart above uses simulated data to illustrate how thresholds would
    > move over time. In Q3 2025 the Decline boundary tightened from 400 → 420
    > because simulated Nano-Credit defaults exceeded the 3% appetite.
    > By Q2 2026 improved repayment data allowed the system to relax back.
    """)

    st.markdown("""
    ---
    #### Configuration (`thresholds.json`)

    The API reads decision boundaries from `thresholds.json` at startup.
    In a production deployment this file would be **updated nightly** by the
    portfolio-monitoring pipeline after computing actual default rates from the loan book.
    """)

    st.code(json.dumps(cfg, indent=2), language="json")


# ══════════════════════════════════════════════════════════════════════════════
#  FEATURE LABORATORY — Gated Feature Shadowing
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("---")

st.markdown("""
<div style="display:flex; align-items:center; gap:0.7rem; margin-bottom:0.3rem;">
    <span style="font-size:1.8rem;">&#129514;</span>
    <span class="dash-title" style="font-size:1.6rem;">Feature Laboratory</span>
</div>
<p class="dash-sub">
    Gated feature-shadowing pipeline: candidate features run in shadow mode before promotion.
</p>
""", unsafe_allow_html=True)

# Simulated shadow feature data
shadow_features = [
    {
        "feature": "social_media_score",
        "status": "SHADOW",
        "cps_normal": 0.65,
        "cps_recession": 0.28,
        "shadow_auc": 0.81,
        "production_auc": 0.84,
        "weeks_in_shadow": 6,
        "verdict": "CPS dropped under recession → REJECT candidate",
    },
    {
        "feature": "mobile_app_logins",
        "status": "SHADOW",
        "cps_normal": 0.72,
        "cps_recession": 0.68,
        "shadow_auc": 0.83,
        "production_auc": 0.84,
        "weeks_in_shadow": 3,
        "verdict": "CPS stable but no AUC lift → still monitoring",
    },
    {
        "feature": "utility_rate_3m",
        "status": "PROMOTED",
        "cps_normal": 0.89,
        "cps_recession": 0.86,
        "shadow_auc": 0.86,
        "production_auc": 0.84,
        "weeks_in_shadow": 12,
        "verdict": "CPS stable + AUC lift → PROMOTED to production",
    },
    {
        "feature": "browser_type",
        "status": "REJECTED",
        "cps_normal": 0.72,
        "cps_recession": 0.31,
        "shadow_auc": 0.82,
        "production_auc": 0.84,
        "weeks_in_shadow": 8,
        "verdict": "CPS collapsed under recession → REJECTED",
    },
]

# Build the table
lab_col1, lab_col2 = st.columns([3, 2])

with lab_col1:
    st.markdown("#### Shadow Feature Pipeline")

    lab_rows = ""
    for sf in shadow_features:
        if sf["status"] == "SHADOW":
            badge = '<span style="background:rgba(245,158,11,0.15);color:#FBBF24;padding:3px 10px;border-radius:20px;font-size:0.72rem;font-weight:600;">&#128300; SHADOW</span>'
        elif sf["status"] == "PROMOTED":
            badge = '<span style="background:rgba(0,191,166,0.15);color:#00E5CC;padding:3px 10px;border-radius:20px;font-size:0.72rem;font-weight:600;">&#9989; PROMOTED</span>'
        else:
            badge = '<span style="background:rgba(239,68,68,0.15);color:#F87171;padding:3px 10px;border-radius:20px;font-size:0.72rem;font-weight:600;">&#10060; REJECTED</span>'

        cps_color_r = "#F87171" if sf["cps_recession"] < 0.50 else "#FBBF24" if sf["cps_recession"] < 0.70 else "#00E5CC"

        lab_rows += f"""
        <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
            <td style="padding:8px 10px;color:#E8ECF1;font-weight:600;font-family:monospace;font-size:0.85rem;">{sf['feature']}</td>
            <td style="padding:8px 10px;">{badge}</td>
            <td style="padding:8px 10px;color:#00E5CC;">{sf['cps_normal']:.2f}</td>
            <td style="padding:8px 10px;color:{cps_color_r};font-weight:700;">{sf['cps_recession']:.2f}</td>
            <td style="padding:8px 10px;color:#8899AA;">{sf['shadow_auc']:.2f}</td>
            <td style="padding:8px 10px;color:#8899AA;">{sf['weeks_in_shadow']}w</td>
        </tr>"""

    st.markdown(f"""
    <div style="background:rgba(19,34,56,0.7);border:1px solid rgba(0,191,166,0.15);border-radius:14px;overflow:hidden;backdrop-filter:blur(12px);box-shadow:0 6px 24px rgba(0,0,0,0.3);">
        <table style="width:100%;border-collapse:collapse;">
            <thead>
                <tr style="border-bottom:2px solid rgba(0,191,166,0.2);">
                    <th style="padding:10px;color:#00BFA6;text-align:left;font-size:0.75rem;text-transform:uppercase;letter-spacing:1px;">Feature</th>
                    <th style="padding:10px;color:#00BFA6;text-align:left;font-size:0.75rem;text-transform:uppercase;letter-spacing:1px;">Status</th>
                    <th style="padding:10px;color:#00BFA6;text-align:left;font-size:0.75rem;text-transform:uppercase;letter-spacing:1px;">CPS Normal</th>
                    <th style="padding:10px;color:#00BFA6;text-align:left;font-size:0.75rem;text-transform:uppercase;letter-spacing:1px;">CPS Recession</th>
                    <th style="padding:10px;color:#00BFA6;text-align:left;font-size:0.75rem;text-transform:uppercase;letter-spacing:1px;">Shadow AUC</th>
                    <th style="padding:10px;color:#00BFA6;text-align:left;font-size:0.75rem;text-transform:uppercase;letter-spacing:1px;">Duration</th>
                </tr>
            </thead>
            <tbody>
                {lab_rows}
            </tbody>
        </table>
    </div>
    """, unsafe_allow_html=True)

with lab_col2:
    st.markdown("#### Promotion Criteria")
    st.markdown("""
    <div class="metric-card" style="text-align:left;margin-bottom:1rem;">
        <div style="color:#00BFA6;font-weight:700;margin-bottom:0.8rem;">A feature is promoted only when:</div>
        <div style="color:#E8ECF1;font-size:0.88rem;line-height:1.8;">
            1. <b>CPS ≥ 0.70</b> in both normal <em>and</em> recession regimes<br>
            2. <b>Shadow AUC ≥ Production AUC</b> (net lift required)<br>
            3. <b>≥ 8 weeks</b> of stable shadow monitoring<br>
            4. <b>No reversal</b> in spurious correlation check
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Mini chart: CPS comparison
    import altair as alt  # noqa: E402

    cps_chart_data = pd.DataFrame({
        "Feature": [sf["feature"] for sf in shadow_features] * 2,
        "CPS": [sf["cps_normal"] for sf in shadow_features] + [sf["cps_recession"] for sf in shadow_features],
        "Regime": ["Normal"] * len(shadow_features) + ["Recession"] * len(shadow_features),
    })

    cps_chart = (
        alt.Chart(cps_chart_data)
        .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X("Feature:N", axis=alt.Axis(labelColor="#8899AA", titleColor="#8899AA", labelAngle=-30)),
            y=alt.Y("CPS:Q", scale=alt.Scale(domain=[0, 1]), axis=alt.Axis(labelColor="#8899AA", titleColor="#8899AA")),
            color=alt.Color("Regime:N",
                            scale=alt.Scale(domain=["Normal", "Recession"], range=["#00E5CC", "#F87171"]),
                            legend=alt.Legend(labelColor="#8899AA", titleColor="#8899AA")),
            xOffset="Regime:N",
            tooltip=["Feature", "Regime", "CPS"],
        )
        .properties(height=250, title=alt.TitleParams("CPS: Normal vs Recession", color="#8899AA"))
        .configure_view(strokeWidth=0)
        .configure(background="rgba(0,0,0,0)")
    )
    st.altair_chart(cps_chart, use_container_width=True)

with st.expander("🧪 How the Feature Laboratory works", expanded=False):
    st.markdown("""
    #### Gated Feature-Shadowing Pipeline

    Before any new feature enters the production model, it goes through a **3-stage gate**:

    ```
    ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
    │  CANDIDATE   │────▶│   SHADOW     │────▶│  PROMOTED    │
    │  (proposed)  │     │  (parallel)  │     │ (production) │
    └──────────────┘     └──────────────┘     └──────────────┘
           │                    │                     │
           │              Runs alongside          Full model
           │              production model       integration
           │              for ≥ 8 weeks
           │                    │
           │              If CPS drops ──▶  REJECTED ❌
           │              under recession
    ```

    #### Why This Matters

    1. **Prevents spurious features** from entering production — features like
       `browser_type` or `social_media_score` correlate well in normal conditions
       but **collapse during economic stress**.
    2. **The CPS (Causal Predictive Stability)** metric tracks whether a feature's
       predictive power holds across regime changes. A CPS < 0.70 under recession
       is an automatic rejection.
    3. **No human intervention needed** — the pipeline monitors, evaluates, and
       gates features autonomously, creating a Palantir-style self-improving system.

    #### Current Shadow Features

    """)
    for sf in shadow_features:
        icon = "🔬" if sf["status"] == "SHADOW" else "✅" if sf["status"] == "PROMOTED" else "❌"
        st.markdown(f"- {icon} **{sf['feature']}**: {sf['verdict']}")


# ══════════════════════════════════════════════════════════════════════════════
#  KNOWLEDGE GRAPH — Growth Counter
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("---")

st.markdown("""
<div style="display:flex; align-items:center; gap:0.7rem; margin-bottom:0.3rem;">
    <span style="font-size:1.8rem;">&#128279;</span>
    <span class="dash-title" style="font-size:1.6rem;">Knowledge Graph Intelligence</span>
</div>
<p class="dash-sub">
    NetworkX-powered borrower graph: employers, communities, referrals, and utility networks.
</p>
""", unsafe_allow_html=True)

# Load graph stats
import sys  # noqa: E402
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from api.graph_utils import load_graph, get_graph_stats
    G = load_graph()
    g_stats = get_graph_stats(G)
except Exception:
    g_stats = {"node_count": 0, "edge_count": 0, "avg_degree": 0,
               "node_types": {}, "edge_types": {}, "borrower_count": 0}

# Metric cards
gc1, gc2, gc3, gc4 = st.columns(4)
with gc1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{g_stats.get('node_count', 0)}</div>
        <div class="metric-label">Total Nodes</div>
    </div>""", unsafe_allow_html=True)
with gc2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{g_stats.get('edge_count', 0)}</div>
        <div class="metric-label">Total Edges</div>
    </div>""", unsafe_allow_html=True)
with gc3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{g_stats.get('avg_degree', 0)}</div>
        <div class="metric-label">Avg Degree</div>
    </div>""", unsafe_allow_html=True)
with gc4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{g_stats.get('borrower_count', 0)}</div>
        <div class="metric-label">Borrowers</div>
    </div>""", unsafe_allow_html=True)

# Node/edge type breakdown
g_col1, g_col2 = st.columns(2)
with g_col1:
    st.markdown("#### Node Types")
    node_types = g_stats.get("node_types", {})
    if node_types:
        nt_df = pd.DataFrame([
            {"Type": k.title(), "Count": v} for k, v in node_types.items()
        ])
        nt_chart = (
            alt.Chart(nt_df)
            .mark_arc(innerRadius=50, cornerRadius=4)
            .encode(
                theta=alt.Theta("Count:Q"),
                color=alt.Color("Type:N",
                                scale=alt.Scale(range=["#00E5CC", "#FBBF24", "#F87171", "#818CF8"]),
                                legend=alt.Legend(labelColor="#8899AA", titleColor="#8899AA")),
                tooltip=["Type", "Count"],
            )
            .properties(height=220)
            .configure_view(strokeWidth=0)
            .configure(background="rgba(0,0,0,0)")
        )
        st.altair_chart(nt_chart, use_container_width=True)

with g_col2:
    st.markdown("#### Edge Types")
    edge_types = g_stats.get("edge_types", {})
    if edge_types:
        et_df = pd.DataFrame([
            {"Type": k.replace("_", " ").title(), "Count": v} for k, v in edge_types.items()
        ])
        et_chart = (
            alt.Chart(et_df)
            .mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6)
            .encode(
                x=alt.X("Count:Q", axis=alt.Axis(labelColor="#8899AA", titleColor="#8899AA")),
                y=alt.Y("Type:N", sort="-x", axis=alt.Axis(labelColor="#8899AA", titleColor="#8899AA")),
                color=alt.value("#00BFA6"),
                tooltip=["Type", "Count"],
            )
            .properties(height=220)
            .configure_view(strokeWidth=0)
            .configure(background="rgba(0,0,0,0)")
        )
        st.altair_chart(et_chart, use_container_width=True)

# Simulated growth over time
st.markdown("#### Graph Growth Over Time (Simulated)")
growth_data = pd.DataFrame({
    "Month": ["Jan", "Feb", "Mar", "Apr", "May", "Jun"] * 2,
    "Count": [8, 12, 14, 16, 18, 20, 15, 22, 26, 30, 34, 36],
    "Metric": ["Nodes"] * 6 + ["Edges"] * 6,
})

growth_chart = (
    alt.Chart(growth_data)
    .mark_area(opacity=0.3, line=True)
    .encode(
        x=alt.X("Month:N", sort=["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
                 axis=alt.Axis(labelColor="#8899AA", titleColor="#8899AA")),
        y=alt.Y("Count:Q", axis=alt.Axis(labelColor="#8899AA", titleColor="#8899AA")),
        color=alt.Color("Metric:N",
                        scale=alt.Scale(domain=["Nodes", "Edges"], range=["#00E5CC", "#FBBF24"]),
                        legend=alt.Legend(labelColor="#8899AA", titleColor="#8899AA")),
        tooltip=["Month", "Metric", "Count"],
    )
    .properties(height=250)
    .configure_view(strokeWidth=0)
    .configure(background="rgba(0,0,0,0)")
)
st.altair_chart(growth_chart, use_container_width=True)

st.markdown("""
<div class="ok-box">
    &#128279; <b>Graph Intelligence Active</b> — The knowledge graph enriches every credit decision
    with employer risk profiles, community trust scores, and referral networks. As more borrowers
    join, the graph grows and scoring accuracy improves autonomously.
</div>
""", unsafe_allow_html=True)
