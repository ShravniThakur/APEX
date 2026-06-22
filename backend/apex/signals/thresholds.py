"""Signal-detection thresholds (specs/signals.md, 'Open tuning').

Spec anchor numbers, centralised so tuning is one place. They are *anchors, not law*
— tuned against the persona manifest via `apex.signals.validate`.
"""

# --- dormancy (#1) --- #
DORMANCY_DAYS = 90

# --- application_dropoff (#2) --- #
APPLICATION_STALL_HOURS = 48
APPLICATION_DROPOFF_STEPS = {"document_upload", "video_kyc"}

# --- idle_balance (#3) --- #
IDLE_BALANCE_MIN = 50_000
LARGE_OUTFLOW_MIN = 50_000      # a single debit >= this counts as a "large outflow" (suppresses idle)
IDLE_WINDOW_DAYS = 90

# --- fiscal_year_end_window (#4) --- #
FISCAL_YEAR_END_MONTHS = {1, 2, 3}   # Jan–Mar (Q4 of the Indian financial year)

# --- sip_graduation (#5) --- #
SIP_PRODUCT_ID = "inv_jannivesh_sip"
SIP_GRADUATION_MIN_AGE_DAYS = 120    # ~4 months

# --- life_event (#6) / large_asset_purchase (#7) (anomaly-fed) --- #
ANOMALY_MEDICAL_CATEGORY = "medical"
LARGE_ASSET_CATEGORIES = {"retail", "vehicle", "property"}

# --- manual_recurring_payment (#8) --- #
MANUAL_RECURRING_MIN_COUNT = 3
MANUAL_RECURRING_WINDOW_DAYS = 180
# Categories with their own dedicated signal are excluded so they don't double-fire here.
MANUAL_RECURRING_EXCLUDE_CATEGORIES = {"rent", "education", "salary"}

# --- login_decay (#9) --- #
LOGIN_DECAY_THRESHOLD = 0.30

# --- sustained_rent_payment (#10) --- #
RENT_MIN_MONTHS = 6

# --- tuition_payment (#11) --- #
TUITION_MIN_COUNT = 2     # seasonal lump sums, not strictly monthly

# --- cash_flow_stress (#12) --- #
# Tuned against the manifest: stress personas score 0.93/0.96, highest noise 0.70 → 0.80
# separates them with margin.
STRESS_THRESHOLD = 0.80

# --- gold_loan_liquidity_gap (#13) --- #
GOLD_DIP_MAX_AMOUNT = 2_500
GOLD_DIP_WINDOW_DAYS = 45
GOLD_DIP_MIN_COUNT = 8

# --- salary_credit_upgrade (#14) --- #
# Plain Regular savings only; Insta Plus is treated as not-needing-upgrade (tuning decision,
# since the synthetic population puts most salaried customers in Insta Plus).
SALARY_UPGRADE_ACCOUNT_TYPES = {"acc_savings_regular"}

# --- protection_gap (#15) --- #
PROTECTION_GAP_MIN_AGE = 18
PROTECTION_GAP_MAX_AGE = 70

# --- churn_risk (attrition-model-fed) --- #
# The trained Kaggle churn model predicts the customer is likely to leave — an EARLY warning, before
# the hard `dormancy` line. Anchor; tuned high enough that the engineered-calm noise population
# (active, healthy balances) stays silent, while a genuinely disengaging customer crosses it.
CHURN_RISK_THRESHOLD = 0.80
