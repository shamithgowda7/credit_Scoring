"""
Self-Improvement Engine — Pattern Detection & Drift Monitoring
================================================================
Analyzes accumulated KG data to generate actionable insights,
detect distribution drift, and suggest threshold adjustments.
"""

import json
import logging
from typing import Dict, List
from pathlib import Path

import numpy as np

from src.knowledge_graph import KnowledgeGraph

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
THRESHOLDS_PATH = PROJECT_ROOT / "thresholds.json"


def generate_insights(kg: KnowledgeGraph) -> List[Dict]:
    """
    Analyze the KG and produce a list of actionable insights.

    Each insight: {type, severity, title, description, metric}
    """
    kg._ensure_loaded()
    insights = []

    # Gather all borrower nodes
    borrowers = []
    for nid, ndata in kg.G.nodes(data=True):
        if ndata.get("type") == "borrower" and ndata.get("score"):
            borrowers.append({"id": nid, **ndata})

    if len(borrowers) < 2:
        insights.append({
            "type": "info",
            "severity": "low",
            "title": "Insufficient Data",
            "description": f"Only {len(borrowers)} borrower(s) in the graph. Need more assessments for meaningful insights.",
            "metric": len(borrowers),
        })
        return insights

    # ── 1. Score Distribution Analysis ──
    scores = [b.get("score", 0) for b in borrowers if b.get("score")]
    if scores:
        avg_score = np.mean(scores)
        std_score = np.std(scores)
        high_risk = sum(1 for s in scores if s < 450)
        low_risk = sum(1 for s in scores if s >= 700)
        total = len(scores)

        insights.append({
            "type": "distribution",
            "severity": "info",
            "title": "Portfolio Score Distribution",
            "description": f"Avg score: {avg_score:.0f} (σ={std_score:.0f}). "
                          f"{high_risk}/{total} high-risk ({high_risk/total*100:.0f}%), "
                          f"{low_risk}/{total} low-risk ({low_risk/total*100:.0f}%).",
            "metric": round(avg_score),
        })

        if high_risk / total > 0.3:
            insights.append({
                "type": "warning",
                "severity": "high",
                "title": "High-Risk Concentration",
                "description": f"{high_risk/total*100:.0f}% of borrowers are high-risk (score < 450). "
                              f"Consider tightening eligibility criteria.",
                "metric": round(high_risk / total * 100),
            })

    # ── 2. Employer Risk Analysis ──
    employer_risks = {}
    for nid, ndata in kg.G.nodes(data=True):
        if ndata.get("type") != "employer":
            continue
        emp_borrowers = [
            nb for nb in kg.G.neighbors(nid)
            if kg.G.nodes[nb].get("type") == "borrower"
        ]
        if len(emp_borrowers) >= 2:
            emp_scores = [kg.G.nodes[b].get("score", 500) for b in emp_borrowers]
            emp_high = sum(1 for b in emp_borrowers if kg.G.nodes[b].get("risk_tier") == "High")
            employer_risks[ndata.get("name", nid)] = {
                "count": len(emp_borrowers),
                "avg_score": np.mean(emp_scores),
                "high_risk_pct": emp_high / len(emp_borrowers),
            }

    for emp_name, stats in employer_risks.items():
        if stats["high_risk_pct"] > 0.4:
            insights.append({
                "type": "employer_risk",
                "severity": "high",
                "title": f"High Default Rate: {emp_name}",
                "description": f"{stats['high_risk_pct']*100:.0f}% of {stats['count']} "
                              f"borrowers from {emp_name} are high-risk. "
                              f"Avg score: {stats['avg_score']:.0f}.",
                "metric": round(stats["high_risk_pct"] * 100),
            })
        elif stats["high_risk_pct"] < 0.1 and stats["count"] >= 3:
            insights.append({
                "type": "employer_positive",
                "severity": "info",
                "title": f"Strong Employer: {emp_name}",
                "description": f"Only {stats['high_risk_pct']*100:.0f}% high-risk among "
                              f"{stats['count']} borrowers. Avg score: {stats['avg_score']:.0f}.",
                "metric": round(stats["avg_score"]),
            })

    # ── 3. Feature Distribution Drift ──
    feature_keys = ["income_mean", "income_cv", "utility_rate", "dti_final", "employment_status", "shock_total"]
    feature_values = {k: [] for k in feature_keys}
    for b in borrowers:
        feats = b.get("features", {})
        if isinstance(feats, str):
            try: feats = json.loads(feats)
            except: feats = {}
        for k in feature_keys:
            if k in feats:
                feature_values[k].append(float(feats[k]))

    for feat, vals in feature_values.items():
        if len(vals) < 3:
            continue
        mean_val = np.mean(vals)
        std_val = np.std(vals)

        # Check for extreme distributions
        if feat == "income_cv" and mean_val > 0.6:
            insights.append({
                "type": "feature_drift",
                "severity": "medium",
                "title": f"High Income Volatility",
                "description": f"Avg income_cv is {mean_val:.2f} (σ={std_val:.2f}). "
                              f"Borrowers are experiencing above-average income instability.",
                "metric": round(mean_val, 2),
            })
        elif feat == "utility_rate" and mean_val < 0.6:
            insights.append({
                "type": "feature_drift",
                "severity": "medium",
                "title": f"Low Bill Payment Rates",
                "description": f"Avg utility_rate is {mean_val:.2f}. "
                              f"Borrowers are struggling with bill payments.",
                "metric": round(mean_val, 2),
            })

    # ── 4. Graph Structure Insights ──
    stats = kg.get_stats()
    if stats.get("avg_degree", 0) > 5:
        insights.append({
            "type": "graph_health",
            "severity": "info",
            "title": "Dense Knowledge Graph",
            "description": f"Avg degree {stats['avg_degree']:.1f} with "
                          f"{stats.get('connected_components', 0)} components. "
                          f"Rich relationship data available for scoring.",
            "metric": stats["avg_degree"],
        })

    # ── 5. Self-Improvement Recommendations ──
    if len(borrowers) >= 10:
        # Check if similarity edges exist
        sim_edges = sum(1 for _, _, d in kg.G.edges(data=True) if d.get("type") == "similar_to")
        if sim_edges > 0:
            insights.append({
                "type": "self_improvement",
                "severity": "info",
                "title": "Peer Clusters Detected",
                "description": f"{sim_edges} borrower similarity links found. "
                              f"The system is learning peer risk patterns.",
                "metric": sim_edges,
            })

    if len(borrowers) >= 20:
        insights.append({
            "type": "self_improvement",
            "severity": "info",
            "title": "Model Retraining Eligible",
            "description": f"With {len(borrowers)} assessed borrowers, the system has "
                          f"enough data to refine risk thresholds and validate causal features.",
            "metric": len(borrowers),
        })

    return insights


def suggest_threshold_adjustments(kg: KnowledgeGraph) -> Dict:
    """
    Based on accumulated assessment outcomes, suggest adjustments
    to the DECLINE_UPPER and NANO_CREDIT_UPPER thresholds.
    """
    kg._ensure_loaded()

    borrowers = [
        ndata for _, ndata in kg.G.nodes(data=True)
        if ndata.get("type") == "borrower" and ndata.get("score")
    ]

    if len(borrowers) < 10:
        return {"suggestion": "none", "reason": "Not enough data", "borrower_count": len(borrowers)}

    scores = [b["score"] for b in borrowers]
    decisions = [b.get("decision", "") for b in borrowers]

    decline_count = sum(1 for d in decisions if d == "DECLINE")
    total = len(decisions)
    decline_rate = decline_count / total

    # Load current thresholds
    current = {"DECLINE_UPPER": 400, "NANO_CREDIT_UPPER": 700}
    if THRESHOLDS_PATH.exists():
        try:
            cfg = json.loads(THRESHOLDS_PATH.read_text())
            t = cfg.get("thresholds", {})
            current["DECLINE_UPPER"] = t.get("DECLINE_UPPER", 400)
            current["NANO_CREDIT_UPPER"] = t.get("NANO_CREDIT_UPPER", 700)
        except: pass

    suggestion = "maintain"
    reason = "Current thresholds are performing within acceptable bounds."
    new_thresholds = dict(current)

    if decline_rate > 0.4:
        suggestion = "tighten"
        reason = f"Decline rate is {decline_rate:.0%} — too many high-risk applications getting through. Suggest raising DECLINE_UPPER."
        new_thresholds["DECLINE_UPPER"] = min(current["DECLINE_UPPER"] + 20, 500)
    elif decline_rate < 0.1:
        suggestion = "relax"
        reason = f"Decline rate is only {decline_rate:.0%} — thresholds may be too strict. Consider lowering DECLINE_UPPER."
        new_thresholds["DECLINE_UPPER"] = max(current["DECLINE_UPPER"] - 10, 350)

    return {
        "suggestion": suggestion,
        "reason": reason,
        "current_thresholds": current,
        "suggested_thresholds": new_thresholds,
        "decline_rate": round(decline_rate, 3),
        "borrower_count": len(borrowers),
        "avg_score": round(np.mean(scores)),
    }
