"""Train the 3 supervised models, persist artifacts, report metrics (specs/ml.md).

    python -m apex.ml.train

- stress           : synthetic latent-driver trainset
- churn            : real Kaggle Churn_Modelling.csv
- propensity       : synthetic latent-driver trainset, all categories (cold-start prior)

Anomaly/confidence/similarity are not trained.
"""
import joblib
import pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split

from ..config import BACKEND_DIR, RANDOM_SEED
from .features import (
    PROPENSITY_CATEGORIES, PROPENSITY_FEATURES, STRESS_FEATURES,
    compute_propensity_features, compute_stress_features,
)
from .loaders import load_churn
from .trainset import generate_propensity_trainset, generate_stress_trainset

ARTIFACTS = BACKEND_DIR / "apex" / "ml" / "artifacts"

# Gradient-boosted trees: LightGBM if available, else sklearn's HistGradientBoosting
# (same family; keeps the build robust if LightGBM's native lib is missing).
try:
    from lightgbm import LGBMClassifier

    def _make_model():
        return LGBMClassifier(n_estimators=200, learning_rate=0.05, max_depth=-1, verbose=-1)
    BACKEND = "lightgbm"
except Exception:  # pragma: no cover
    from sklearn.ensemble import HistGradientBoostingClassifier

    def _make_model():
        return HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05)
    BACKEND = "sklearn-histgb"


def _fit_report(name, X, y):
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=RANDOM_SEED, stratify=y)
    model = _make_model()
    model.fit(Xtr, ytr)
    auc = roc_auc_score(yte, model.predict_proba(Xte)[:, 1])
    print(f"  {name:22} rows={len(X):>6}  test ROC-AUC={auc:.3f}  (positives={int(y.sum())})")
    return model, auc


def train_stress():
    records, labels = generate_stress_trainset(seed=RANDOM_SEED)
    X = pd.DataFrame([compute_stress_features(r) for r in records])[STRESS_FEATURES]
    y = pd.Series(labels)
    model, auc = _fit_report("stress (synthetic)", X, y)
    joblib.dump({"model": model, "features": STRESS_FEATURES, "auc": auc}, ARTIFACTS / "stress.joblib")


def train_churn():
    X, y = load_churn()
    model, auc = _fit_report("churn (Kaggle)", X, y)
    joblib.dump({"model": model, "features": list(X.columns), "auc": auc}, ARTIFACTS / "churn.joblib")


def train_propensity():
    """One binary GBM per category over a shared feature matrix; bundled into a single
    artifact. Synthetic cold-start prior — swap the trainset for an OUTCOMES loader once
    real click data exists; features/model/scoring stay unchanged."""
    records, labels = generate_propensity_trainset(seed=RANDOM_SEED)
    X = pd.DataFrame([compute_propensity_features(r) for r in records])[PROPENSITY_FEATURES]
    models, aucs = {}, {}
    for cat in PROPENSITY_CATEGORIES:
        y = pd.Series([lab[cat] for lab in labels])
        model, auc = _fit_report(f"propensity:{cat} (synthetic)", X, y)
        models[cat] = model
        aucs[cat] = auc
    joblib.dump(
        {"models": models, "features": PROPENSITY_FEATURES,
         "categories": PROPENSITY_CATEGORIES, "aucs": aucs},
        ARTIFACTS / "propensity.joblib",
    )


def main():
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    print(f"Training (backend: {BACKEND})...")
    train_stress()
    train_churn()
    train_propensity()
    print(f"Artifacts written to {ARTIFACTS}")


if __name__ == "__main__":
    main()
