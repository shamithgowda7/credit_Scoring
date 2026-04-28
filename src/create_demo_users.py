"""
Day 4 — Create Demo Users & Export Feature Names
=================================================
Loads the trained Causal-LR model, samples representative borrowers
from the synthetic dataset, computes credit scores, and exports:
  - data/demo_users.json      (12 demo user profiles)
  - models/feature_names.json (ordered feature list for the API)
"""

import json
import numpy as np
import pandas as pd
import joblib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR     = PROJECT_ROOT / "data"
MODELS_DIR   = PROJECT_ROOT / "models"

FEATURE_NAMES = [
    'income_mean', 'income_cv', 'utility_rate',
    'dti_final', 'employment_status', 'shock_total',
]

# Human-readable names for demo profiles
DEMO_NAMES = [
    "Amara Okonkwo",   "Raj Patel",        "Fatima Al-Sayed",
    "Chen Wei",         "Priya Sharma",     "Kwame Mensah",
    "Sofia Rodriguez",  "Yuki Tanaka",      "David Kimani",
    "Lina Nguyen",      "Omar Hassan",      "Zara Mbeki",
]


def compute_score(model, features_dict: dict) -> int:
    """Convert model probability to a 300-900 credit score."""
    df = pd.DataFrame([features_dict])[FEATURE_NAMES]
    proba = model.predict_proba(df)[0, 1]
    score = int(300 + 600 * (1 - proba))  # maps [0,1] -> [900,300]
    return max(300, min(900, score))


def get_decision(score: int) -> str:
    if score < 400:
        return "DECLINE"
    elif score < 700:
        return "NANO_CREDIT"
    else:
        return "STANDARD"


def get_risk_tier(score: int) -> str:
    if score < 450:
        return "High"
    elif score < 650:
        return "Medium"
    else:
        return "Low"


def main():
    print("=" * 60)
    print("  Day 4: Creating Demo Users & Exporting Feature Names")
    print("=" * 60)

    # Load model
    model_path = MODELS_DIR / "causal_lr_model.pkl"
    if not model_path.exists():
        print("  ERROR: causal_lr_model.pkl not found. Run run_pipeline.py first.")
        return
    model = joblib.load(model_path)
    print(f"  Loaded: {model_path}")

    # Load training data to sample realistic profiles
    train_path = DATA_DIR / "temporal_credit_agg_train.csv"
    if not train_path.exists():
        print("  ERROR: temporal_credit_agg_train.csv not found. Run scm_temporal_v1.py first.")
        return
    train = pd.read_csv(train_path)
    print(f"  Loaded: {train_path} ({len(train):,} rows)")

    # Compute scores for all training rows to find good candidates
    X_all = train[FEATURE_NAMES]
    probas = model.predict_proba(X_all)[:, 1]
    scores = (300 + 600 * (1 - probas)).astype(int).clip(300, 900)
    train['_score'] = scores

    # Select 4 high-risk, 4 medium-risk, 4 low-risk
    high_risk   = train[train['_score'].between(350, 450)].sample(4, random_state=42)
    medium_risk = train[train['_score'].between(520, 650)].sample(4, random_state=42)
    low_risk    = train[train['_score'].between(720, 850)].sample(4, random_state=42)

    selected = pd.concat([high_risk, medium_risk, low_risk]).reset_index(drop=True)

    # Build demo users
    demo_users = []
    for i, (_, row) in enumerate(selected.iterrows()):
        features = {feat: round(float(row[feat]), 6) for feat in FEATURE_NAMES}
        score = compute_score(model, features)
        user = {
            "id": i + 1,
            "name": DEMO_NAMES[i],
            "risk_tier": get_risk_tier(score),
            "expected_score": score,
            "decision": get_decision(score),
            "features": features,
        }
        demo_users.append(user)

    # Save demo_users.json
    demo_path = DATA_DIR / "demo_users.json"
    with open(demo_path, 'w') as f:
        json.dump(demo_users, f, indent=2)
    print(f"\n  Saved: {demo_path}")
    print(f"  Users: {len(demo_users)}")

    # Print summary
    print(f"\n  {'#':<3} {'Name':<20} {'Risk':<8} {'Score':<6} {'Decision':<12}")
    print("  " + "-" * 52)
    for u in demo_users:
        print(f"  {u['id']:<3} {u['name']:<20} {u['risk_tier']:<8} "
              f"{u['expected_score']:<6} {u['decision']:<12}")

    # Export feature_names.json
    fn_path = MODELS_DIR / "feature_names.json"
    with open(fn_path, 'w') as f:
        json.dump(FEATURE_NAMES, f, indent=2)
    print(f"\n  Saved: {fn_path}")
    print(f"  Features: {FEATURE_NAMES}")

    print("\n  Day 4 complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
