"""Isolation Forest Anomaly Detection Engine for AuditLens AI.

Trains an Isolation Forest unsupervised model on numeric engineered features.
Outputs a normalized ml_score in [0, 1] where higher values indicate higher risk/anomaly.
Persists and loads trained models using joblib.
"""

from pathlib import Path
from typing import Optional, Tuple, Union

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from auditlens.config import (
    IFOREST_CONTAMINATION,
    IFOREST_N_ESTIMATORS,
    IFOREST_RANDOM_STATE,
    MODEL_FEATURE_COLUMNS,
    SAVED_MODEL_PATH,
)


class IsolationForestDetector:
    """Wrapper around scikit-learn Isolation Forest with feature scaling and

    normalized anomaly scoring in [0, 1].
    """

    def __init__(
        self,
        contamination: float = IFOREST_CONTAMINATION,
        n_estimators: int = IFOREST_N_ESTIMATORS,
        random_state: int = IFOREST_RANDOM_STATE,
    ) -> None:
        self.contamination = contamination
        self.n_estimators = n_estimators
        self.random_state = random_state
        self.scaler = StandardScaler()
        self.model = IsolationForest(
            n_estimators=self.n_estimators,
            contamination=self.contamination,
            random_state=self.random_state,
            n_jobs=-1,
        )
        self.score_min_: float = 0.0
        self.score_max_: float = 1.0
        self.feature_names_: list = list(MODEL_FEATURE_COLUMNS)
        self.is_fitted_: bool = False

    def fit(self, X: pd.DataFrame) -> "IsolationForestDetector":
        """Fit the scaler and Isolation Forest on numeric feature matrix."""
        # Ensure only model features and expected column ordering
        X_mat = X[self.feature_names_].copy()
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X_mat)
        
        # Fit Isolation Forest
        self.model.fit(X_scaled)
        
        # Calculate raw scores: -score_samples(X) so higher is more anomalous
        raw_anomaly_scores = -self.model.score_samples(X_scaled)
        self.score_min_ = float(np.min(raw_anomaly_scores))
        self.score_max_ = float(np.max(raw_anomaly_scores))
        
        if self.score_max_ <= self.score_min_:
            self.score_max_ = self.score_min_ + 1e-6
            
        self.is_fitted_ = True
        return self

    def predict_score(self, X: pd.DataFrame) -> np.ndarray:
        """Predict normalized ml_score in [0, 1] for the given feature matrix.

        Higher scores represent higher degree of anomaly.
        """
        if not self.is_fitted_:
            raise RuntimeError("Model is not fitted yet. Call fit() or load() first.")

        X_mat = X[self.feature_names_].copy()
        X_scaled = self.scaler.transform(X_mat)
        
        # Raw scores: higher means more anomalous
        raw_anomaly_scores = -self.model.score_samples(X_scaled)
        
        # Normalize to [0, 1] using fitted bounds, with clipping
        normalized = (raw_anomaly_scores - self.score_min_) / (self.score_max_ - self.score_min_)
        return np.clip(normalized, 0.0, 1.0)

    def save(self, filepath: Union[str, Path] = SAVED_MODEL_PATH) -> None:
        """Serialize detector bundle (model, scaler, bounds) using joblib."""
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        bundle = {
            "model": self.model,
            "scaler": self.scaler,
            "score_min_": self.score_min_,
            "score_max_": self.score_max_,
            "feature_names_": self.feature_names_,
            "contamination": self.contamination,
            "n_estimators": self.n_estimators,
            "random_state": self.random_state,
            "is_fitted_": self.is_fitted_,
        }
        joblib.dump(bundle, filepath)
        print(f"Saved IsolationForestDetector model bundle to {filepath}")

    @classmethod
    def load(cls, filepath: Union[str, Path] = SAVED_MODEL_PATH) -> "IsolationForestDetector":
        """Deserialize detector bundle from disk."""
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"Model file not found at {filepath}")

        bundle = joblib.load(filepath)
        detector = cls(
            contamination=bundle.get("contamination", IFOREST_CONTAMINATION),
            n_estimators=bundle.get("n_estimators", IFOREST_N_ESTIMATORS),
            random_state=bundle.get("random_state", IFOREST_RANDOM_STATE),
        )
        detector.model = bundle["model"]
        detector.scaler = bundle["scaler"]
        detector.score_min_ = bundle["score_min_"]
        detector.score_max_ = bundle["score_max_"]
        detector.feature_names_ = bundle.get("feature_names_", list(MODEL_FEATURE_COLUMNS))
        detector.is_fitted_ = bundle.get("is_fitted_", True)
        return detector


def train_and_save_model(
    features_df: pd.DataFrame,
    model_path: Path = SAVED_MODEL_PATH,
    contamination: float = IFOREST_CONTAMINATION,
) -> IsolationForestDetector:
    """Train Isolation Forest on features and save to disk."""
    detector = IsolationForestDetector(contamination=contamination)
    detector.fit(features_df)
    detector.save(model_path)
    return detector


if __name__ == "__main__":
    from auditlens.config import DEFAULT_DATASET_PATH
    from auditlens.engine.features import extract_features
    import sys

    print("Training Isolation Forest Anomaly Detector...")
    if not DEFAULT_DATASET_PATH.exists():
        print(f"Error: {DEFAULT_DATASET_PATH} not found.")
        sys.exit(1)

    raw_df = pd.read_csv(DEFAULT_DATASET_PATH)
    features = extract_features(raw_df)

    detector = train_and_save_model(features, SAVED_MODEL_PATH)
    ml_scores = detector.predict_score(features)

    print("\nModel Training & Scoring Results:")
    print(f"Total Entries Scored: {len(ml_scores):,}")
    print(f"ML Score Min:         {ml_scores.min():.4f}")
    print(f"ML Score Mean:        {ml_scores.mean():.4f}")
    print(f"ML Score Median:      {np.median(ml_scores):.4f}")
    print(f"ML Score Max:         {ml_scores.max():.4f}")
    print(f"ML Score Std:         {ml_scores.std():.4f}")
    print(f"Entries with ML Score > 0.60: {(ml_scores > 0.60).sum():,} ({(ml_scores > 0.60).mean() * 100:.2f}%)")

    # Test load functionality
    print("\nVerifying model load from disk...")
    loaded_detector = IsolationForestDetector.load(SAVED_MODEL_PATH)
    test_scores = loaded_detector.predict_score(features[:10])
    assert np.allclose(test_scores, ml_scores[:10]), "Loaded model score mismatch!"
    print("Model load verification passed!")

    print("\nStage 4 Isolation Forest successfully verified!")
