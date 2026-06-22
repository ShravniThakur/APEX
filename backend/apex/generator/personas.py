"""The 16 signal-personas (specs/data-generator.md).

Each persona is authored backwards from a signal. `traits` are pattern tags the
generator turns into transactions / sessions / applications. `expected_signals`
is the manifest the validation harness will assert against once the signal layer
exists.

Trait kinds (see generate.py for emitters):
  salary(amount)              monthly salary credit
  baseline()                  normal background spend
  idle()                      keep balance high, no large outflow
  manual_bill(payee, amount, count)   recurring manual same-payee payments
  rent(amount, months)        merchant_category=rent, stable payee
  tuition(amount)             merchant_category=education, seasonal lump sum
  medical_anomaly(amount)     one large medical debit (anomaly)
  vehicle_anomaly(amount)     one large vehicle debit (anomaly)
  stress()                    rising debit velocity + falling balance
  gold_dips()                 short-window low-balance dips, small withdrawals
  sessions(mode)              healthy | decay | none
"""


def t(kind, **params):
    return {"kind": kind, **params}


PERSONAS = [
    # 1 — idle_balance (HERO)
    {
        "key": "priya", "name": "Priya Nair", "age": 34, "gender": "F",
        "city_tier": "metro", "language_pref": "en", "occupation": "salaried",
        "customer_type": "existing", "kyc_status": "complete", "monthly_income": 90000,
        "accounts": [{"type": "acc_insta_plus", "balance": 280000}],
        "holdings": [{"product_id": "ins_eshield_insta", "current_value": 5000000}],
        "traits": [t("salary", amount=90000), t("baseline"), t("idle"), t("sessions", mode="healthy")],
        "expected_signals": ["idle_balance"],
        "expected_recommendation": "MOD / Auto Sweep or JanNivesh SIP",
        "hero": True,
    },
    # 2 — manual_recurring_payment (HERO)
    {
        "key": "vikram", "name": "Vikram Patel", "age": 41, "gender": "M",
        "city_tier": "tier_2", "language_pref": "hi", "occupation": "self_employed",
        "customer_type": "existing", "kyc_status": "complete", "monthly_income": 70000,
        "accounts": [{"type": "acc_insta_plus", "balance": 60000}],
        "holdings": [{"product_id": "ins_eshield_insta", "current_value": 2500000}],
        "traits": [
            t("baseline"),
            t("manual_bill", payee="MSEB_ELECTRICITY", amount=2200, count=6),
            t("sessions", mode="healthy"),
        ],
        "expected_signals": ["manual_recurring_payment"],
        "expected_recommendation": "e-PAY AutoPay",
        "hero": True,
    },
    # 3 — life_event (HERO — ethical restraint)
    {
        "key": "anjali", "name": "Anjali Desai", "age": 38, "gender": "F",
        "city_tier": "metro", "language_pref": "en", "occupation": "salaried",
        "customer_type": "existing", "kyc_status": "complete", "monthly_income": 110000,
        "accounts": [{"type": "acc_insta_plus", "balance": 150000}],
        "holdings": [],
        "traits": [
            t("salary", amount=110000), t("baseline"),
            t("medical_anomaly", amount=90000),
            t("sessions", mode="healthy"),
        ],
        "expected_signals": ["life_event"],
        "expected_recommendation": "eShield (delayed insight, never an immediate push)",
        "hero": True,
    },
    # 4 — dormancy (HERO)
    {
        "key": "ramesh", "name": "Ramesh Iyer", "age": 52, "gender": "M",
        "city_tier": "tier_3", "language_pref": "ta", "occupation": "retired",
        "customer_type": "dormant", "kyc_status": "complete", "monthly_income": 25000,
        "accounts": [{"type": "acc_insta_plus", "balance": 18000, "status": "dormant"}],
        "holdings": [],
        "traits": [t("sessions", mode="none"), t("dormant_history")],
        "expected_signals": ["dormancy"],
        "expected_recommendation": "Insta Plus reactivation",
        "hero": True,
    },
    # 5 — sustained_rent_payment
    {
        "key": "meera", "name": "Meera Reddy", "age": 31, "gender": "F",
        "city_tier": "tier_2", "language_pref": "te", "occupation": "salaried",
        "customer_type": "existing", "kyc_status": "complete", "monthly_income": 85000,
        "owns_property": False,
        "accounts": [{"type": "acc_insta_plus", "balance": 120000}],
        "holdings": [],
        "traits": [
            t("salary", amount=85000), t("baseline"),
            t("rent", amount=22000, months=8),
            t("sessions", mode="healthy"),
        ],
        "expected_signals": ["sustained_rent_payment"],
        "expected_recommendation": "Home Loan",
    },
    # 6 — tuition_payment
    {
        "key": "karthik", "name": "Karthik Menon", "age": 46, "gender": "M",
        "city_tier": "metro", "language_pref": "en", "occupation": "salaried",
        "customer_type": "existing", "kyc_status": "complete", "monthly_income": 130000,
        "dependents": 2,
        "accounts": [{"type": "acc_insta_plus", "balance": 200000}],
        "holdings": [],
        "traits": [
            t("salary", amount=130000), t("baseline"),
            t("tuition", amount=75000),
            t("sessions", mode="healthy"),
        ],
        "expected_signals": ["tuition_payment"],
        "expected_recommendation": "Education Loan",
    },
    # 7 — cash_flow_stress -> PAPL
    {
        "key": "suresh", "name": "Suresh Kumar", "age": 29, "gender": "M",
        "city_tier": "tier_2", "language_pref": "hi", "occupation": "salaried",
        "customer_type": "existing", "kyc_status": "complete", "monthly_income": 60000,
        "has_papl_offer": True,
        "accounts": [{"type": "acc_insta_plus", "balance": 12000}],
        "holdings": [],
        "traits": [t("stress"), t("sessions", mode="healthy")],  # stress shaping emits its own salary
        "expected_signals": ["cash_flow_stress"],
        "expected_recommendation": "PAPL (has pre-approved offer)",
    },
    # 8 — cash_flow_stress -> Loan against FD
    {
        "key": "lakshmi", "name": "Lakshmi Banerjee", "age": 44, "gender": "F",
        "city_tier": "tier_3", "language_pref": "bn", "occupation": "self_employed",
        "customer_type": "existing", "kyc_status": "complete", "monthly_income": 50000,
        "accounts": [
            {"type": "acc_insta_plus", "balance": 9000},
            {"type": "dep_fd_regular", "balance": 300000},
        ],
        "holdings": [],
        "traits": [t("stress"), t("sessions", mode="healthy")],
        "expected_signals": ["cash_flow_stress"],
        "expected_recommendation": "Loan against FD (no PAPL, holds FD)",
    },
    # 9 — gold_loan_liquidity_gap
    {
        "key": "mohan", "name": "Mohan Yadav", "age": 49, "gender": "M",
        "city_tier": "rural", "language_pref": "hi", "occupation": "self_employed",
        "customer_type": "existing", "kyc_status": "complete", "monthly_income": 40000,
        "owns_gold": True,
        "accounts": [{"type": "acc_insta_plus", "balance": 7000}],
        "holdings": [],
        "traits": [t("gold_dips"), t("sessions", mode="healthy")],
        "expected_signals": ["gold_loan_liquidity_gap"],
        "expected_recommendation": "Gold Loan",
    },
    # 10 — login_decay
    {
        "key": "deepa", "name": "Deepa Joshi", "age": 27, "gender": "F",
        "city_tier": "metro", "language_pref": "en", "occupation": "salaried",
        "customer_type": "existing", "kyc_status": "complete", "monthly_income": 75000,
        "accounts": [{"type": "acc_insta_plus", "balance": 95000}],
        "holdings": [],
        "traits": [t("salary", amount=75000), t("baseline"), t("sessions", mode="decay")],
        "expected_signals": ["login_decay"],
        "expected_recommendation": "YONO Cash (one reason to re-open the app)",
    },
    # 11 — salary_credit_upgrade (+ preapproved_card_offer)
    {
        "key": "rohan", "name": "Rohan Sharma", "age": 26, "gender": "M",
        "city_tier": "tier_2", "language_pref": "hi", "occupation": "salaried",
        "customer_type": "existing", "kyc_status": "complete", "monthly_income": 55000,
        "has_card_offer": True,
        "accounts": [{"type": "acc_savings_regular", "balance": 70000}],
        "holdings": [],
        "traits": [t("salary", amount=55000), t("baseline"), t("sessions", mode="healthy")],
        "expected_signals": ["salary_credit_upgrade", "preapproved_card_offer"],
        "expected_recommendation": "Salary Package (+ pre-approved Credit Card)",
    },
    # 12 — protection_gap (inclusion showcase)
    {
        "key": "gita", "name": "Gita Devi", "age": 35, "gender": "F",
        "city_tier": "rural", "language_pref": "te", "occupation": "self_employed",
        "customer_type": "existing", "kyc_status": "complete", "monthly_income": 22000,
        "accounts": [{"type": "acc_insta_plus", "balance": 30000}],
        "holdings": [],  # deliberately no insurance
        "traits": [t("salary", amount=22000), t("baseline"), t("sessions", mode="healthy")],
        "expected_signals": ["protection_gap"],
        "expected_recommendation": "PMJJBY / PMSBY (ultra-low-cost cover)",
    },
    # 13 — fiscal_year_end_window
    {
        "key": "anita", "name": "Anita Rao", "age": 39, "gender": "F",
        "city_tier": "metro", "language_pref": "en", "occupation": "salaried",
        "customer_type": "existing", "kyc_status": "complete", "monthly_income": 120000,
        "accounts": [{"type": "acc_insta_plus", "balance": 250000}],
        "holdings": [],  # holds no tax_saving product
        "traits": [t("salary", amount=120000), t("baseline"), t("idle"), t("sessions", mode="healthy")],
        "expected_signals": ["fiscal_year_end_window"],
        "expected_recommendation": "Tax Saver FD / PPF (NPS if 80C maxed) — fires only Jan-Mar",
    },
    # 14 — sip_graduation
    {
        "key": "deepak", "name": "Deepak Verma", "age": 33, "gender": "M",
        "city_tier": "tier_2", "language_pref": "hi", "occupation": "salaried",
        "customer_type": "existing", "kyc_status": "complete", "monthly_income": 80000,
        "accounts": [
            {"type": "acc_insta_plus", "balance": 110000},
            {"type": "inv_jannivesh_sip", "balance": 18000, "opened_days_ago": 150},
        ],
        "holdings": [],
        "traits": [t("salary", amount=80000), t("baseline"), t("sessions", mode="healthy")],
        "expected_signals": ["sip_graduation"],
        "expected_recommendation": "SBI Mutual Fund (graduate from micro-SIP)",
    },
    # 15 — large_asset_purchase
    {
        "key": "sanjay", "name": "Sanjay Gupta", "age": 43, "gender": "M",
        "city_tier": "metro", "language_pref": "en", "occupation": "self_employed",
        "customer_type": "existing", "kyc_status": "complete", "monthly_income": 150000,
        "accounts": [{"type": "acc_insta_plus", "balance": 400000}],
        "holdings": [],
        "traits": [
            t("salary", amount=150000), t("baseline"),
            t("vehicle_anomaly", amount=250000),
            t("sessions", mode="healthy"),
        ],
        "expected_signals": ["large_asset_purchase"],
        "expected_recommendation": "Auto Loan + SBI General (insure the asset, insight)",
    },
    # 16 — application_dropoff (Guide; no account yet)
    {
        "key": "fatima", "name": "Fatima Khan", "age": 30, "gender": "F",
        "city_tier": "tier_2", "language_pref": "hi", "occupation": "salaried",
        "customer_type": "new", "kyc_status": "in_progress", "monthly_income": None,
        "no_account": True,
        "accounts": [],
        "holdings": [],
        "traits": [],
        "application": {
            "product_id": "acc_insta_plus", "current_step": "video_kyc",
            "steps_completed": ["personal_details", "document_upload"],
            "status": "in_progress", "stalled_hours": 72,
        },
        "expected_signals": ["application_dropoff"],
        "expected_recommendation": "Guide: resume onboarding at video_kyc step",
    },
]
