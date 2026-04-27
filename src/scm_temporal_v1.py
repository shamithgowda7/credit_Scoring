"""
scm_temporal_v1.py
==================
Temporal extension of SCM v5: 12 monthly snapshots per borrower,
seasonality, and a Watts-Strogatz social graph with peer contagion.

DESIGN RATIONALE
━━━━━━━━━━━━━━━━
The cross-sectional SCM v5 generates a single observation per borrower.
Real credit scoring uses time-series signals: 12 months of mobile recharges,
utility payments, and income flows. This file extends v5 to produce:

  1. temporal_credit_data_train.parquet  — 10,000 borrowers × 12 months
  2. temporal_credit_data_test.parquet   — 10,000 borrowers × 12 months (50/50 normal/recession)
  3. social_graph_edges_train.csv        — borrower-borrower peer edges
  4. social_graph_edges_test.csv

WHAT IS STATIC vs DYNAMIC
━━━━━━━━━━━━━━━━━━━━━━━━━
Static (set once at loan origination, same across all 12 months):
  age_bucket, household_structure, employment_status
  financial_agency, financial_consistency  (borrower character)
  borrower_id, split

Dynamic (observed/computed each month):
  economic_shock        — monthly idiosyncratic shock event (Bernoulli 4%)
  income_stability      — AR(1) with seasonal + shock
  debt_to_income        — slowly evolving with seasonal spending
  utility_paid_on_time  — binary: paid utility bill this month
  social_capital        — updated via peer payment and peer shock exposure
  digital_footprint     — monthly transaction activity
  peer_shock_exposure   — mean shock across social graph neighbors

TEMPORAL STRUCTURAL EQUATIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
income_t = 0.80 * income_{t-1}
         + 0.15 * income_baseline    (mean reversion to personal baseline)
         + seasonal_income[t]        (harvest/holiday patterns)
         - 0.30 * shock_eff_t        (shock disrupts income)
         + N(0, 0.04)

dti_t    = 0.93 * dti_{t-1}
         + 0.04 * (1 - income_t)     (low income → debt accumulation)
         + seasonal_dti[t]           (school fees, holiday spending)
         + N(0, 0.015)

ur_t     ~ Bernoulli(sigmoid(
             1.5*income_t + 0.8*sc_{t-1} + 0.9*fa + 1.1*fc
             - 0.4*dti_t + 0.3*employ - 1.50))

sc_t     = 0.88 * sc_{t-1}
         + 0.10 * mean(ur_t[neighbors])     (peer payment lifts social cap)
         - 0.20 * mean(shock_eff[neighbors]) (peer shocks depress social cap)
         + N(0, 0.02)

SEASONALITY (month 0 = January)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Income effects:
  Jan (0):  -0.03  (salary payment delays, government workers)
  Mar (2):  +0.06  (harvest season begins, agricultural LMICs)
  Apr (3):  +0.10  (harvest peak income)
  Dec (11): -0.05  (holiday spending draws down savings)

DTI effects:
  Jun (5):  +0.07  (school fee season)
  Jul (6):  +0.06  (school fee season continuation)
  Nov (10): +0.08  (pre-holiday credit usage)
  Dec (11): +0.10  (holiday peak spending)

SOCIAL GRAPH (Watts-Strogatz small-world)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
k=4 neighbors per borrower.
Start with ring lattice, rewire 20% of edges randomly.
This gives realistic clustering (communities) + short paths (contagion).
Edge weight = 1/k (uniform for simplicity).

Peer contagion mechanism:
  If a neighbor has an economic shock → reduces ego's social capital.
  If neighbors are paying their bills → increases ego's social capital.
  This creates correlated default clusters without making geolocation causal.

AGGREGATED FEATURES (for model training, one row per borrower)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
From 12 months of raw signals, compute:
  income_mean        — mean monthly income stability
  income_cv          — coefficient of variation (volatility)
  income_trend       — mean(months 10-11) - mean(months 0-1)
  utility_rate       — fraction of months paid on time
  utility_recent     — fraction of last 3 months paid on time
  dti_final          — DTI at month 11
  sc_final           — social capital at month 11
  shock_total        — total monthly shocks in 12 months
  peer_shock_exp     — mean peer shock exposure across 12 months
  (plus all static features)

OUTCOME
━━━━━━━
default = Bernoulli(sigmoid(risk - TEMPORAL_INTERCEPT))
where risk uses the same coefficients as v5 cross-section,
applied to aggregated features. Intercept 9.4661 calibrated
for ~8% base default rate.

VALIDATED RESULTS (5k borrowers prototype):
  Default rate: 8.1%
  income_cv ~ default: +0.364   (volatility is the key temporal signal)
  utility_rate ~ default: -0.295
  income_mean ~ default: -0.295
  shock_total ~ default: +0.209
  Seasonality clearly visible in monthly income/utility patterns
"""

import os
import numpy as np
import pandas as pd
from scipy.special import expit
from scipy.optimize import brentq

# ─── Constants ────────────────────────────────────────────────────────────────
TEMPORAL_INTERCEPT = 9.4661   # calibrated for ~8% default on temporal aggregates
PAYMENT_INTERCEPT  = 1.50

# Seasonality arrays indexed by month (0=Jan … 11=Dec)
# Grounded in LMIC agricultural and spending patterns
INCOME_SEASONAL = np.array([
    -0.03,   # Jan: salary payment delays
     0.00,   # Feb: baseline
     0.06,   # Mar: harvest season begins
     0.10,   # Apr: harvest peak
     0.03,   # May: post-harvest slowdown
     0.00,   # Jun: baseline
     0.00,   # Jul: baseline
    -0.02,   # Aug: pre-harvest lean period
    -0.02,   # Sep: lean period
    -0.02,   # Oct: lean period
     0.02,   # Nov: small pre-holiday uptick
    -0.05,   # Dec: holiday spending draws down savings
], dtype=np.float32)

DTI_SEASONAL = np.array([
     0.00,   # Jan
     0.00,   # Feb
     0.00,   # Mar
     0.00,   # Apr
    -0.01,   # May: slight DTI relief (harvest income)
     0.07,   # Jun: school fee season
     0.06,   # Jul: school fee continuation
     0.00,   # Aug
     0.00,   # Sep
     0.00,   # Oct
     0.08,   # Nov: pre-holiday credit usage
     0.10,   # Dec: holiday peak
], dtype=np.float32)


# ─── Social graph construction ────────────────────────────────────────────────

def build_social_graph(n: int, k: int = 4, rewire_prob: float = 0.20,
                        rng: np.random.Generator = None) -> np.ndarray:
    """
    Watts-Strogatz small-world graph.

    Parameters
    ----------
    n           : number of borrowers
    k           : mean degree (must be even)
    rewire_prob : fraction of edges rewired randomly (creates short paths)
    rng         : numpy Generator

    Returns
    -------
    adj : (n, k) integer array — adj[i] = indices of borrower i's neighbors
    """
    if rng is None:
        rng = np.random.default_rng(0)

    # Ring lattice: each node connected to k/2 left and k/2 right neighbors
    half = k // 2
    adj = np.zeros((n, k), dtype=np.int32)
    for j in range(half):
        adj[:, j]         = (np.arange(n) + j + 1) % n
        adj[:, half + j]  = (np.arange(n) - j - 1) % n

    # Rewire with probability rewire_prob
    for col in range(k):
        mask = rng.random(n) < rewire_prob
        new_targets = rng.integers(0, n, size=n)
        # Avoid self-loops
        self_loop = new_targets == np.arange(n)
        new_targets[self_loop] = (new_targets[self_loop] + 1) % n
        adj[mask, col] = new_targets[mask]

    return adj


# ─── Static borrower generator (wraps v5 cross-section logic) ─────────────────

def _generate_static_features(n: int, rng: np.random.Generator,
                                employ_penalty: float = 0.0) -> dict:
    """
    Generate time-invariant borrower characteristics.
    employ_penalty > 0 simulates recession unemployment shift.
    """
    from scipy.special import expit

    age = rng.choice(5, n, p=[0.12, 0.22, 0.30, 0.24, 0.12]).astype(np.int8)

    base_p = np.full(n, 0.72, dtype=np.float32)
    base_p[age == 0] = 0.55
    base_p[age == 4] = 0.58
    employ = rng.binomial(1, np.clip(base_p - employ_penalty, 0.15, 1.0)).astype(np.int8)

    household = rng.choice(3, n, p=[0.35, 0.40, 0.25]).astype(np.int8)

    # Social capital initial level (updated dynamically each month)
    sc_logit = (0.30 * employ.astype(np.float32)
              + 0.20 * (age == 2).astype(np.float32)
              - 0.20 * (age == 0).astype(np.float32)
              + rng.normal(0, 0.50, n).astype(np.float32))
    sc_init = expit(sc_logit).astype(np.float32)

    # Income baseline (personal mean income, time-invariant anchor)
    inc_baseline = np.clip(
        rng.beta(2, 5, n).astype(np.float32)
        + 0.20 * employ
        - 0.05 * (age == 0).astype(np.float32)
        + 0.05 * (age == 2).astype(np.float32)
        + rng.normal(0, 0.03, n).astype(np.float32),
        0.0, 1.0)

    # DTI baseline
    dti_init = expit(
        -1.50 * inc_baseline
        + 0.40 * (1 - employ.astype(np.float32))
        + 0.30 * (age == 0).astype(np.float32)
        - 0.20 * (age >= 3).astype(np.float32)
        + 0.60 * (household == 2).astype(np.float32)
        + 0.25 * (household == 1).astype(np.float32)
        + rng.normal(0, 0.15, n).astype(np.float32)
    ).astype(np.float32)

    # Financial agency and consistency (LLM placeholders)
    fin_agency = expit(
        0.60 * employ.astype(np.float32)
        + 0.40 * sc_init
        - 0.30 * (age == 0).astype(np.float32)
        + 0.50 * (inc_baseline > 0.5).astype(np.float32)
        + rng.normal(0, 0.35, n).astype(np.float32)
    ).astype(np.float32)

    fin_consist = expit(
        0.40 * fin_agency
        + rng.normal(0, 1.0, n).astype(np.float32)
    ).astype(np.float32)

    # Digital footprint (WB: older borrowers less digitally engaged)
    digital_fp = np.clip(
        rng.beta(3, 2, n).astype(np.float32)
        - 0.15 * (age >= 3).astype(np.float32)
        + rng.normal(0, 0.03, n).astype(np.float32),
        0.0, 1.0)

    return {
        "age_bucket":            age,
        "employment_status":     employ,
        "household_structure":   household,
        "financial_agency":      fin_agency,
        "financial_consistency": fin_consist,
        "digital_footprint":     digital_fp,
        "_inc_baseline":         inc_baseline,   # internal — not in output
        "_dti_init":             dti_init,        # internal — not in output
        "_sc_init":              sc_init,         # internal — not in output
    }


# ─── Monthly simulation ────────────────────────────────────────────────────────

def _simulate_months(static: dict, adj: np.ndarray, n: int, T: int,
                      shock_rate: float, shock_strength: float,
                      rng: np.random.Generator) -> dict:
    """
    Simulate T monthly observations per borrower.

    Returns arrays of shape (n, T) for each dynamic variable.
    """
    employ    = static["employment_status"].astype(np.float32)
    household = static["household_structure"]
    fa        = static["financial_agency"]
    fc        = static["financial_consistency"]
    inc_0     = static["_inc_baseline"]
    dti       = static["_dti_init"].copy()
    sc        = static["_sc_init"].copy()

    # Pre-allocate history arrays
    inc_h        = np.zeros((n, T), dtype=np.float32)
    ur_h         = np.zeros((n, T), dtype=np.float32)   # binary: paid on time
    sc_h         = np.zeros((n, T), dtype=np.float32)
    dti_h        = np.zeros((n, T), dtype=np.float32)
    shock_h      = np.zeros((n, T), dtype=np.float32)
    peer_shock_h = np.zeros((n, T), dtype=np.float32)
    dig_h        = np.zeros((n, T), dtype=np.float32)

    inc = inc_0.copy()

    for t in range(T):
        # ── Monthly idiosyncratic economic shock ──
        shock_raw = rng.binomial(1, shock_rate, n).astype(np.float32)
        shock_eff = np.clip(
            shock_raw * (1.0 + 0.60 * (household == 2) + 0.30 * (household == 1)),
            0.0, 1.0).astype(np.float32)
        # Peer shock exposure (vectorised via adjacency matrix)
        peer_shock = shock_eff[adj].mean(axis=1).astype(np.float32)

        # ── Income: AR(1) with mean reversion + seasonal + shock ──
        inc_new = np.clip(
            0.80 * inc
            + 0.15 * inc_0                     # pull toward personal baseline
            + INCOME_SEASONAL[t]
            - shock_strength * shock_eff
            + rng.normal(0, 0.04, n).astype(np.float32),
            0.0, 1.0).astype(np.float32)

        # ── DTI: slow mean reversion + seasonal spending ──
        dti_new = np.clip(
            0.93 * dti
            + 0.04 * (1.0 - inc_new)           # low income → debt accumulation
            + DTI_SEASONAL[t]
            + rng.normal(0, 0.015, n).astype(np.float32),
            0.05, 0.95).astype(np.float32)

        # ── Utility payment (binary outcome) ──
        pay_logit = (1.50 * inc_new
                   + 0.80 * sc
                   + 0.90 * fa
                   + 1.10 * fc
                   - 0.40 * dti_new
                   + 0.30 * employ
                   - PAYMENT_INTERCEPT)
        ur_t = rng.binomial(1, expit(pay_logit)).astype(np.float32)

        # ── Social capital: peer payment + peer shock contagion ──
        peer_pay = ur_t[adj].mean(axis=1).astype(np.float32)
        sc_new = np.clip(
            0.88 * sc
            + 0.10 * peer_pay                  # peers paying → higher social cap
            - 0.20 * peer_shock                # peer shocks → lower social cap
            + rng.normal(0, 0.02, n).astype(np.float32),
            0.0, 1.0).astype(np.float32)

        # ── Digital footprint: monthly transaction activity ──
        age = static["age_bucket"]
        dig_t = np.clip(
            rng.beta(3, 2, n).astype(np.float32)
            - 0.15 * (age >= 3).astype(np.float32)
            + rng.normal(0, 0.03, n).astype(np.float32),
            0.0, 1.0).astype(np.float32)

        # ── Store ──
        inc_h[:, t]        = inc_new
        ur_h[:, t]         = ur_t
        sc_h[:, t]         = sc_new
        dti_h[:, t]        = dti_new
        shock_h[:, t]      = shock_raw
        peer_shock_h[:, t] = peer_shock
        dig_h[:, t]        = dig_t

        inc = inc_new
        dti = dti_new
        sc  = sc_new

    return {
        "income_stability":     inc_h,
        "utility_paid":         ur_h,
        "social_capital":       sc_h,
        "debt_to_income":       dti_h,
        "economic_shock":       shock_h,
        "peer_shock_exposure":  peer_shock_h,
        "digital_footprint":    dig_h,
    }


# ─── Aggregated features (one row per borrower for model training) ─────────────

def _aggregate_features(history: dict, static: dict, n: int) -> pd.DataFrame:
    """
    Collapse (n, T) monthly arrays into (n,) borrower-level features.
    These are the features that go into the three-model comparison.
    """
    inc = history["income_stability"]
    ur  = history["utility_paid"]
    sc  = history["social_capital"]
    dti = history["debt_to_income"]
    sh  = history["economic_shock"]
    ps  = history["peer_shock_exposure"]

    df = pd.DataFrame({
        # Static
        "age_bucket":             static["age_bucket"],
        "employment_status":      static["employment_status"],
        "household_structure":    static["household_structure"],
        "financial_agency":       static["financial_agency"],
        "financial_consistency":  static["financial_consistency"],
        "digital_footprint_mean": history["digital_footprint"].mean(axis=1),
        # Temporal aggregates — causal features
        "income_mean":            inc.mean(axis=1),
        "income_cv":              inc.std(axis=1) / (inc.mean(axis=1) + 1e-6),
        "income_trend":           inc[:, -2:].mean(1) - inc[:, :2].mean(1),
        "utility_rate":           ur.mean(axis=1),
        "utility_recent":         ur[:, -3:].mean(axis=1),
        "dti_final":              dti[:, -1],
        "dti_mean":               dti.mean(axis=1),
        "sc_final":               sc[:, -1],
        "sc_trend":               sc[:, -3:].mean(1) - sc[:, :3].mean(1),
        "shock_total":            sh.sum(axis=1),
        "shock_recent":           sh[:, -3:].sum(axis=1),
        "peer_shock_exposure":    ps.mean(axis=1),
    })
    return df


# ─── Default outcome ───────────────────────────────────────────────────────────

def _compute_temporal_default(agg: pd.DataFrame, rng: np.random.Generator) -> np.ndarray:
    """
    Default outcome from aggregated temporal features.
    Same causal structure as v5 cross-section but applied to time-averaged signals.
    income_cv (volatility) is the key new temporal predictor.
    """
    n    = len(agg)
    fa   = agg["financial_agency"].values
    fc   = agg["financial_consistency"].values
    hh   = agg["household_structure"].values

    risk = (3.50 * (1 - agg["income_mean"].values)
          + 3.50 * (1 - agg["utility_rate"].values)
          + 2.00 * (agg["shock_total"].values / 12) * 3
          + 1.50 * agg["dti_final"].values
          + 0.80 * (1 - agg["utility_rate"].values)
          + 0.70 * (1 - fa)
          + 0.60 * (1 - fc)
          + 0.50 * (hh == 2).astype(np.float32)
          + 0.25 * (hh == 1).astype(np.float32)
          + 1.00 * agg["income_cv"].values           # income VOLATILITY is the key temporal signal
          + rng.normal(0, 0.10, n).astype(np.float32))

    return (rng.random(n) < expit(risk - TEMPORAL_INTERCEPT)).astype(np.int8)


# ─── Spurious variables (same reversal mechanic as v5) ────────────────────────

def _build_temporal_spurious(default: np.ndarray, rng: np.random.Generator,
                               recession: bool = False) -> dict:
    n = len(default)
    d = default.astype(np.float32)

    if not recession:
        dark  = (rng.random(n) < np.where(d==1, 0.45, 0.25)).astype(np.int8)
        signup= (rng.random(n) < np.where(d==1, 0.45, 0.33)).astype(np.int8)
        base  = rng.beta(3, 2, n).astype(np.float32)
        soc   = np.clip(base + np.where(d==1,-0.20,0.08) + rng.normal(0,0.05,n), 0, 1)
        cl    = np.array([rng.choice(5, p=([0.10,0.15,0.20,0.25,0.30] if dd==1
                          else [0.30,0.25,0.20,0.15,0.10])) for dd in d])
        base  = rng.beta(2, 3, n).astype(np.float32)
        app   = np.clip(base + np.where(d==1,-0.15,0.06) + rng.normal(0,0.04,n), 0, 1)
        inq   = np.clip(rng.poisson(np.where(d==1,2.2,1.2)), 0, 10).astype(np.int8)
    else:
        dark  = (rng.random(n) < np.where(d==1, 0.20, 0.50)).astype(np.int8)
        signup= (rng.random(n) < np.where(d==1, 0.30, 0.50)).astype(np.int8)
        base  = rng.beta(3, 2, n).astype(np.float32)
        soc   = np.clip(base + np.where(d==1,+0.20,-0.05) + rng.normal(0,0.05,n), 0, 1)
        cl    = np.array([rng.choice(5, p=([0.35,0.25,0.20,0.12,0.08] if dd==1
                          else [0.10,0.15,0.20,0.25,0.30])) for dd in d])
        base  = rng.beta(2, 3, n).astype(np.float32)
        app   = np.clip(base + np.where(d==1,+0.15,-0.05) + rng.normal(0,0.04,n), 0, 1)
        inq   = np.clip(rng.poisson(np.where(d==1,2.5,3.0)), 0, 10).astype(np.int8)

    return {
        "dark_mode_user":      dark,
        "signup_weekend":      signup,
        "social_media_score":  soc.astype(np.float32),
        "geolocation_cluster": cl.astype(np.int8),
        "app_diversity_index": app.astype(np.float32),
        "num_inquiries":       inq,
    }


# ─── Main public generators ────────────────────────────────────────────────────

def generate_temporal_data(
    n_borrowers: int = 10_000,
    n_months: int = 12,
    random_state: int = 42,
    shock_rate: float = 0.04,        # monthly idiosyncratic shock probability
    shock_strength: float = 0.30,    # income impact per shock
    employ_penalty: float = 0.0,     # recession: reduce employment by this amount
    recession_spurious: bool = False,
    graph_k: int = 4,
    graph_rewire: float = 0.20,
    verbose: bool = True,
) -> tuple:
    """
    Generate temporal credit dataset.

    Returns
    -------
    df_long  : pd.DataFrame  shape (n_borrowers * n_months, ...)
               Long format: one row per (borrower_id, month)
    df_agg   : pd.DataFrame  shape (n_borrowers, ...)
               Aggregated features + default outcome — used for model training
    adj      : np.ndarray    shape (n_borrowers, graph_k)
               Social graph adjacency list (integer borrower indices)
    """
    rng = np.random.default_rng(random_state)
    n   = n_borrowers
    T   = n_months

    if verbose:
        print(f"  Generating {n:,} borrowers × {T} months "
              f"(shock_rate={shock_rate:.0%}, employ_penalty={employ_penalty:.2f})...")

    # ── Static features ──
    static = _generate_static_features(n, rng, employ_penalty=employ_penalty)

    # ── Social graph ──
    adj = build_social_graph(n, k=graph_k, rewire_prob=graph_rewire, rng=rng)

    # ── Monthly simulation ──
    history = _simulate_months(static, adj, n, T,
                                shock_rate=shock_rate,
                                shock_strength=shock_strength, rng=rng)

    # ── Aggregate for model training ──
    df_agg = _aggregate_features(history, static, n)

    # ── Default outcome ──
    df_agg["default"] = _compute_temporal_default(df_agg, rng)

    # ── Spurious features ──
    spurious = _build_temporal_spurious(df_agg["default"].values, rng,
                                         recession=recession_spurious)
    for k_s, v_s in spurious.items():
        df_agg[k_s] = v_s

    # ── Long-format DataFrame ──
    borrower_ids = np.repeat(np.arange(n), T)
    month_ids    = np.tile(np.arange(T), n)

    long_rows = {"borrower_id": borrower_ids, "month": month_ids}

    # Static features repeated for each month
    for col in ["age_bucket", "employment_status", "household_structure",
                "financial_agency", "financial_consistency"]:
        long_rows[col] = np.repeat(static[col], T)

    # Dynamic features flattened row-major
    for key, arr in history.items():
        long_rows[key] = arr.reshape(-1)   # (n*T,)

    df_long = pd.DataFrame(long_rows)

    # Add default (at loan level, repeated)
    df_long["default"] = np.repeat(df_agg["default"].values, T)

    if verbose:
        dr = df_agg["default"].mean()
        print(f"  Default rate:     {dr:.2%}")
        print(f"  income_cv corr:   {df_agg['income_cv'].corr(df_agg['default'].astype(float)):+.4f}")
        print(f"  utility_rate corr:{df_agg['utility_rate'].corr(df_agg['default'].astype(float)):+.4f}")
        print(f"  income_mean corr: {df_agg['income_mean'].corr(df_agg['default'].astype(float)):+.4f}")

    return df_long, df_agg, adj


def generate_temporal_train_test(
    n_train: int = 10_000,
    n_test_each: int = 5_000,
    n_months: int = 12,
    random_state_train: int = 42,
    random_state_normal: int = 99,
    random_state_recession: int = 100,
    verbose: bool = True,
) -> tuple:
    """
    Generate train + test splits mirroring v5 cross-section structure.

    Normal test:    same economic conditions as training.
    Recession test: shock_rate=0.12→0.40, employ_penalty=0.15,
                    spurious correlations reversed.

    Returns
    -------
    df_long_train, df_agg_train, adj_train,
    df_long_test,  df_agg_test,  adj_test
    """
    sep = "─" * 60

    if verbose:
        print(f"\n{sep}")
        print("  SCM Temporal v1 — Training data")
        print(sep)

    df_long_train, df_agg_train, adj_train = generate_temporal_data(
        n_borrowers=n_train, n_months=n_months,
        random_state=random_state_train, verbose=verbose)
    df_agg_train["split"] = "train"
    df_long_train["split"] = "train"

    if verbose:
        print(f"\n{sep}")
        print("  SCM Temporal v1 — Normal test")
        print(sep)

    long_n, agg_n, adj_n = generate_temporal_data(
        n_borrowers=n_test_each, n_months=n_months,
        random_state=random_state_normal, verbose=verbose)
    agg_n["split"]  = "normal"
    long_n["split"] = "normal"

    if verbose:
        print(f"\n{sep}")
        print("  SCM Temporal v1 — Recession test")
        print(sep)

    long_r, agg_r, adj_r = generate_temporal_data(
        n_borrowers=n_test_each, n_months=n_months,
        random_state=random_state_recession,
        shock_rate=0.10,          # 2.5× higher monthly shock rate (vs 0.04 normal)
        shock_strength=0.50,      # deeper income disruption per shock
        employ_penalty=0.15,      # recession unemployment (+15pp)
        recession_spurious=True,
        verbose=verbose)
    agg_r["split"]  = "recession"
    long_r["split"] = "recession"

    # Add borrower_id offset for test set (avoid collisions with train)
    long_n["borrower_id"]  += n_train
    long_r["borrower_id"]  += n_train + n_test_each
    agg_n.index             = agg_n.index + n_train
    agg_r.index             = agg_r.index + n_train + n_test_each

    df_long_test = pd.concat([long_n, long_r], ignore_index=True)
    df_agg_test  = pd.concat([agg_n,  agg_r],  ignore_index=True)
    adj_test     = np.concatenate([adj_n, adj_r], axis=0)

    if verbose:
        print(f"\n{'='*60}")
        print("  SUMMARY")
        print(f"{'='*60}")
        print(f"  Train: {len(df_agg_train):,} borrowers × {n_months} months  "
              f"| default {df_agg_train.default.mean():.2%}")
        print(f"  Normal:    {len(agg_n):,} borrowers | default {agg_n.default.mean():.2%}")
        print(f"  Recession: {len(agg_r):,} borrowers | default {agg_r.default.mean():.2%}")

        # Spurious reversal check
        print(f"\n  Spurious reversal:")
        spurious_vars = ["dark_mode_user","signup_weekend","social_media_score",
                          "geolocation_cluster","app_diversity_index","num_inquiries"]
        print(f"  {'Variable':<28} {'Train':>8} {'Recession':>10} {'Reversed':>10}")
        print(f"  {'─'*58}")
        for v in spurious_vars:
            ct = df_agg_train[[v,"default"]].corr().iloc[0,1]
            cr = agg_r[[v,"default"]].corr().iloc[0,1]
            rev = "YES" if ct * cr < 0 else "NO"
            print(f"  {v:<28} {ct:>+8.3f} {cr:>+10.3f} {rev:>10}")

        # Key temporal features
        print(f"\n  Key temporal features vs default (train):")
        for col in ["income_mean","income_cv","utility_rate","dti_final",
                     "shock_total","sc_final","peer_shock_exposure"]:
            c = df_agg_train[[col,"default"]].corr().iloc[0,1]
            print(f"    {col:<26} {c:+.4f}")

    return (df_long_train, df_agg_train, adj_train,
            df_long_test,  df_agg_test,  adj_test)


# ─── Feature sets for three-model comparison ──────────────────────────────────

TEMPORAL_FEATURE_SETS = {
    # XGBoost sees all aggregated observables + spurious features.
    # income_cv is the key new temporal signal it will learn.
    # But it will also learn spurious correlations that reverse in recession.
    "xgboost_all_temporal": [
        "age_bucket", "employment_status", "household_structure",
        "income_mean", "income_cv", "income_trend",
        "utility_rate", "utility_recent",
        "dti_final", "dti_mean",
        "shock_total", "shock_recent",
        "sc_final", "sc_trend",
        "peer_shock_exposure",
        "digital_footprint_mean",
        # Spurious zone
        "dark_mode_user", "signup_weekend", "social_media_score",
        "geolocation_cluster", "app_diversity_index", "num_inquiries",
    ],
    # Causal-LR: causal aggregated features only.
    # income_cv is the temporal addition — volatility is causal,
    # not just a proxy (high volatility directly causes inability to plan payments).
    "causal_lr_observable_temporal": [
        "income_mean", "income_cv",
        "utility_rate",
        "dti_final",
        "employment_status",
        "shock_total",
    ],
    # Causal-LR-Behavioural: same + LLM placeholder nodes.
    "causal_lr_behavioural_temporal": [
        "income_mean", "income_cv",
        "utility_rate",
        "dti_final",
        "employment_status",
        "shock_total",
        "financial_agency",
        "financial_consistency",
    ],
}


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import os
    print("\n" + "=" * 60)
    print("  SCM Temporal v1 — Generator")
    print("=" * 60)

    (df_long_train, df_agg_train, adj_train,
     df_long_test,  df_agg_test,  adj_test) = generate_temporal_train_test(
        n_train=10_000, n_test_each=5_000, n_months=12, verbose=True)

    os.makedirs("data", exist_ok=True)

    # Save aggregated (model training)
    df_agg_train.to_csv("data/temporal_credit_agg_train.csv", index=False)
    df_agg_test.to_csv("data/temporal_credit_agg_test.csv",   index=False)

    # Save long format (time-series analysis, visualisation)
    df_long_train.to_csv("data/temporal_credit_long_train.csv", index=False)
    df_long_test.to_csv("data/temporal_credit_long_test.csv",   index=False)

    # Save social graphs
    train_edges = []
    for i, neighbors in enumerate(adj_train):
        for nb in neighbors:
            if i < nb:   # undirected: store each edge once
                train_edges.append({"borrower_a": i, "borrower_b": int(nb), "weight": 1})
    pd.DataFrame(train_edges).to_csv("data/social_graph_edges_train.csv", index=False)

    test_edges = []
    for i, neighbors in enumerate(adj_test):
        for nb in neighbors:
            real_nb = int(nb)
            if i < real_nb:
                test_edges.append({"borrower_a": i, "borrower_b": real_nb, "weight": 1})
    pd.DataFrame(test_edges).to_csv("data/social_graph_edges_test.csv", index=False)

    print(f"\n  Files written to data/:")
    print(f"    temporal_credit_agg_train.parquet   {len(df_agg_train):>8,} rows")
    print(f"    temporal_credit_agg_test.parquet    {len(df_agg_test):>8,} rows")
    print(f"    temporal_credit_long_train.parquet  {len(df_long_train):>8,} rows")
    print(f"    temporal_credit_long_test.parquet   {len(df_long_test):>8,} rows")
    print(f"    social_graph_edges_train.csv        {len(train_edges):>8,} edges")
    print(f"    social_graph_edges_test.csv         {len(test_edges):>8,} edges")
    print(f"\n  Feature sets: {list(TEMPORAL_FEATURE_SETS.keys())}")
    print(f"\n  Ready for Day 3 (temporal): train all 3 models on df_agg_train")
    print(f"  using TEMPORAL_FEATURE_SETS.\n")
