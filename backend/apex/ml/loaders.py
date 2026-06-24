"""Load + clean the real public training dataset (specs/ml.md).

Only the feature-intersection columns are kept — the ones we can also compute
for our own customers at serve time (no train/serve skew). Attrition (churn)
trains on this real data; stress is synthetic (see trainset.py).
"""
import pandas as pd

from ..config import BACKEND_DIR

DATA_DIR = BACKEND_DIR / "data"

# Churn model — features computable for our customers (drop CreditScore/Geography/ids).
CHURN_FEATURES = ["Age", "Tenure", "Balance", "NumOfProducts", "IsActiveMember", "EstimatedSalary"]


def load_churn():
    df = pd.read_csv(DATA_DIR / "Churn_Modelling.csv")
    return df[CHURN_FEATURES].copy(), df["Exited"].astype(int)
