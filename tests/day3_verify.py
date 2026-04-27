"""Day 3 verification script — mirrors mode_train.ipynb logic."""
import os, sys, warnings
os.chdir(os.path.dirname(os.path.abspath(__file__)))
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, roc_curve
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.ensemble import GradientBoostingClassifier
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# XGBoost with fallback
try:
    import xgboost as xgb
    _t = xgb.XGBClassifier(); del _t
    USE_XGB = True
    print(f"XGBoost {xgb.__version__} loaded.")
except Exception as e:
    USE_XGB = False
    print(f"XGBoost unavailable ({e.__class__.__name__}). Using sklearn GBM.")

# ── Load data ─────────────────────────────────────────────────────────────────
train = pd.read_csv('temporal_credit_agg_train.csv')
test  = pd.read_csv('temporal_credit_agg_test.csv')
print(f"\nTrain: {train.shape}, Test: {test.shape}")
print(f"Test splits: {test['split'].value_counts().to_dict()}")

test_normal    = test[test['split'] == 'normal'].copy()
test_recession = test[test['split'] == 'recession'].copy()

X_train     = train.drop(columns=['default','split'], errors='ignore')
y_train     = train['default']
X_test_norm = test_normal.drop(columns=['default','split'], errors='ignore')
y_test_norm = test_normal['default']

# ── Validation checks ─────────────────────────────────────────────────────────
assert train.shape[0] == 10_000, f"Train rows: {train.shape[0]}"
assert test_normal.shape[0] == 5_000, f"Normal rows: {test_normal.shape[0]}"
assert test_recession.shape[0] == 5_000, f"Recession rows: {test_recession.shape[0]}"

FEATURE_SETS = {
    'xgboost_all': [
        'age_bucket','employment_status','household_structure',
        'income_mean','income_cv','income_trend',
        'utility_rate','utility_recent',
        'dti_final','dti_mean',
        'shock_total','shock_recent',
        'sc_final','sc_trend','peer_shock_exposure',
        'digital_footprint_mean',
        'dark_mode_user','signup_weekend','social_media_score',
        'geolocation_cluster','app_diversity_index','num_inquiries',
    ],
    'causal_lr_observable': [
        'income_mean','income_cv','utility_rate',
        'dti_final','employment_status','shock_total',
    ],
    'causal_lr_behavioural': [
        'income_mean','income_cv','utility_rate',
        'dti_final','employment_status','shock_total',
        'financial_agency','financial_consistency',
    ],
}

for name, feats in FEATURE_SETS.items():
    missing = set(feats) - set(train.columns)
    assert len(missing) == 0, f"Missing in {name}: {missing}"
print("All validation checks passed.\n")

# ── Model training ────────────────────────────────────────────────────────────
feats_xgb = FEATURE_SETS['xgboost_all']
if USE_XGB:
    booster = xgb.XGBClassifier(
        n_estimators=100, max_depth=5, learning_rate=0.1,
        subsample=0.8, colsample_bytree=0.8,
        eval_metric='logloss', random_state=42, verbosity=0)
else:
    booster = GradientBoostingClassifier(
        n_estimators=100, max_depth=5, learning_rate=0.1,
        subsample=0.8, random_state=42)

print("Training XGBoost-All...")
booster.fit(X_train[feats_xgb], y_train)
prob_xgb = booster.predict_proba(X_test_norm[feats_xgb])[:,1]
auc_xgb  = roc_auc_score(y_test_norm, prob_xgb)
print(f"  AUC (normal): {auc_xgb:.4f}")

feats_obs = FEATURE_SETS['causal_lr_observable']
print("Training Causal-LR (observable)...")
lr_obs = Pipeline([('s', StandardScaler()), ('lr', LogisticRegression(max_iter=1000, random_state=42))])
lr_obs.fit(X_train[feats_obs], y_train)
prob_obs = lr_obs.predict_proba(X_test_norm[feats_obs])[:,1]
auc_obs  = roc_auc_score(y_test_norm, prob_obs)
print(f"  AUC (normal): {auc_obs:.4f}")

feats_beh = FEATURE_SETS['causal_lr_behavioural']
print("Training Causal-LR (behavioural)...")
lr_beh = Pipeline([('s', StandardScaler()), ('lr', LogisticRegression(max_iter=1000, random_state=42))])
lr_beh.fit(X_train[feats_beh], y_train)
prob_beh = lr_beh.predict_proba(X_test_norm[feats_beh])[:,1]
auc_beh  = roc_auc_score(y_test_norm, prob_beh)
print(f"  AUC (normal): {auc_beh:.4f}")

# ── Save results ──────────────────────────────────────────────────────────────
os.makedirs('results', exist_ok=True)
os.makedirs('outputs', exist_ok=True)

results = pd.DataFrame({
    'model':      ['XGBoost-All','Causal-LR (observable)','Causal-LR (behavioural)'],
    'auc_normal': [auc_xgb, auc_obs, auc_beh],
})
results.to_csv('results/baseline_auc.csv', index=False)
print("\nSaved: results/baseline_auc.csv")

# ── ROC Curves ─────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(8, 6))
for name, probs, auc, color in [
    ('XGBoost-All', prob_xgb, auc_xgb, '#e74c3c'),
    ('Causal-LR (observable)', prob_obs, auc_obs, '#2ecc71'),
    ('Causal-LR (beh.)', prob_beh, auc_beh, '#3498db'),
]:
    fpr, tpr, _ = roc_curve(y_test_norm, probs)
    ax.plot(fpr, tpr, label=f'{name}  (AUC={auc:.4f})', color=color, lw=2)
ax.plot([0,1],[0,1],'k--',lw=1,label='Random')
ax.set(xlabel='FPR', ylabel='TPR', title='ROC Curves — Normal Test Set (Day 3 Baseline)')
ax.legend(fontsize=10); ax.grid(True, alpha=0.3)
plt.tight_layout()
fig.savefig('outputs/roc_curves_normal.png', dpi=150)
print("Saved: outputs/roc_curves_normal.png")
plt.close()

# ── Spurious reversal check ────────────────────────────────────────────────────
spurious_cols = ['dark_mode_user','signup_weekend','social_media_score',
                 'geolocation_cluster','app_diversity_index','num_inquiries']
print()
print(f"  {'Variable':<28} {'Train':>8} {'Normal':>8} {'Recession':>10} {'Reversed':>10}")
print("  " + "-" * 65)
log_lines = []
all_reversed = True
for col in spurious_cols:
    ct = train[col].corr(train['default'].astype(float))
    cn = test_normal[col].corr(test_normal['default'].astype(float))
    cr = test_recession[col].corr(test_recession['default'].astype(float))
    rev = ct * cr < 0
    if not rev: all_reversed = False
    line = f"  {col:<28} {ct:>+8.3f} {cn:>+8.3f} {cr:>+10.3f} {'YES' if rev else 'NO':>10}"
    print(line)
    log_lines.append(line)
print(f"\n  All 6 reversed: {'YES' if all_reversed else 'NO'}")
with open('outputs/spurious_reversal_check.txt', 'w') as f:
    f.write('\n'.join(log_lines))
print("Saved: outputs/spurious_reversal_check.txt")

# ── Day 3 Summary ─────────────────────────────────────────────────────────────
expected = {
    'XGBoost-All':             (0.82, 0.85),
    'Causal-LR (observable)':  (0.76, 0.79),
    'Causal-LR (behavioural)': (0.79, 0.82),
}
print("\n" + "="*55)
print("  DAY 3 — NORMAL BASELINE SUMMARY")
print("="*55)
for _, row in results.iterrows():
    lo, hi = expected[row['model']]
    ok = 'OK' if lo <= row['auc_normal'] <= hi else ('High' if row['auc_normal'] > hi else 'Low')
    print(f"  {row['model']:<30}  AUC={row['auc_normal']:.4f}  ({lo:.2f}-{hi:.2f})  [{ok}]")
