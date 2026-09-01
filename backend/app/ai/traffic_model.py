"""First trainable CITYTWIN traffic prediction model."""

from dataclasses import dataclass
from datetime import datetime
import json
import math
from pathlib import Path
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from xgboost import XGBRegressor

from .features import MODEL_FEATURE_NAMES, TrafficTrainingSample, split_features_and_target


@dataclass(frozen=True)
class RegressionMetrics:
    mae: float
    rmse: float
    r2: float


@dataclass(frozen=True)
class TrainingResult:
    train_samples: int
    test_samples: int
    metrics: RegressionMetrics


@dataclass(frozen=True)
class ModelComparisonResult:
    model_name: str
    metrics: RegressionMetrics
    train_samples: int
    test_samples: int
    model: "CandidateRegressionModel"


@dataclass(frozen=True)
class ModelComparison:
    results: tuple[ModelComparisonResult, ...]
    best_model_name: str
    best_model: "CandidateRegressionModel"
    train_samples: tuple[TrafficTrainingSample, ...]
    test_samples: tuple[TrafficTrainingSample, ...]


class CandidateRegressionModel:
    """Trained candidate model using the shared CITYTWIN feature schema."""

    def __init__(self, model_name: str, estimator: Any) -> None:
        self.model_name = model_name
        self.feature_names = MODEL_FEATURE_NAMES
        self._estimator = estimator

    def predict(self, feature_rows: Mapping[str, object] | Sequence[Mapping[str, object]]) -> list[float]:
        """Predict vehicle counts from one or more feature rows."""
        rows = [feature_rows] if isinstance(feature_rows, Mapping) else list(feature_rows)
        if not rows:
            raise ValueError("prediction data must not be empty")
        prepared_rows = [_prepare_feature_row(row) for row in rows]
        return [float(value) for value in self._estimator.predict(prepared_rows)]


def chronological_split(
    samples: Iterable[TrafficTrainingSample],
    test_size: float = 0.2,
) -> tuple[list[TrafficTrainingSample], list[TrafficTrainingSample]]:
    """Split samples into earliest training data and latest test data."""
    if not 0 < test_size < 1:
        raise ValueError("test_size must be greater than 0 and less than 1")
    ordered = sorted(samples, key=lambda sample: (sample.timestamp, sample.road_id))
    if len(ordered) < 2:
        raise ValueError("at least two training samples are required")
    test_count = max(1, math.ceil(len(ordered) * test_size))
    if test_count >= len(ordered):
        raise ValueError("test_size leaves no training samples")
    split_index = len(ordered) - test_count
    return ordered[:split_index], ordered[split_index:]


def compare_models(
    samples: Iterable[TrafficTrainingSample],
    test_size: float = 0.2,
) -> ModelComparison:
    """Evaluate all candidate regressors on one shared chronological split."""
    sample_values = list(samples)
    if not sample_values:
        raise ValueError("training data must not be empty")
    train_samples, test_samples = chronological_split(sample_values, test_size)
    train_features, train_targets = _prepare_samples(train_samples)
    test_features, test_targets = _prepare_samples(test_samples)
    candidate_specs = (
        ("Linear Regression", LinearRegression()),
        (
            "Random Forest Regressor",
            RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=1),
        ),
        ("XGBoost Regressor", XGBRegressor(**_xgboost_defaults())),
    )
    results: list[ModelComparisonResult] = []
    for model_name, estimator in candidate_specs:
        estimator.fit(train_features, train_targets)
        candidate = CandidateRegressionModel(model_name, estimator)
        metrics = _calculate_metrics(estimator.predict(test_features), test_targets)
        results.append(ModelComparisonResult(model_name, metrics, len(train_samples), len(test_samples), candidate))
    best_result = min(results, key=lambda result: (result.metrics.mae, result.metrics.rmse, result.model_name))
    return ModelComparison(tuple(results), best_result.model_name, best_result.model, tuple(train_samples), tuple(test_samples))


class TrafficPredictionModel:
    """Small XGBoost regression wrapper for 15-minute vehicle-count prediction."""

    feature_names = MODEL_FEATURE_NAMES

    def __init__(self, **model_params: object) -> None:
        defaults = _xgboost_defaults()
        defaults.update(model_params)
        self._model = XGBRegressor(**defaults)
        self._trained = False

    def train(
        self,
        samples: Iterable[TrafficTrainingSample],
        test_size: float = 0.2,
    ) -> TrainingResult:
        """Chronologically train and evaluate the model on the latest samples."""
        sample_values = list(samples)
        if not sample_values:
            raise ValueError("training data must not be empty")
        train_samples, test_samples = chronological_split(sample_values, test_size)
        train_features, train_targets = _prepare_samples(train_samples)
        test_features, test_targets = _prepare_samples(test_samples)
        self._model.fit(train_features, train_targets)
        self._trained = True
        metrics = self._evaluate_rows(test_features, test_targets)
        return TrainingResult(len(train_samples), len(test_samples), metrics)

    def predict(self, feature_rows: Mapping[str, object] | Sequence[Mapping[str, object]]) -> list[float]:
        """Predict vehicle counts from one or more Step 2 feature rows."""
        self._require_trained()
        rows = [feature_rows] if isinstance(feature_rows, Mapping) else list(feature_rows)
        if not rows:
            raise ValueError("prediction data must not be empty")
        prepared_rows = [_prepare_feature_row(row) for row in rows]
        return [float(value) for value in self._model.predict(prepared_rows)]

    def evaluate(self, samples: Iterable[TrafficTrainingSample]) -> RegressionMetrics:
        """Evaluate predictions against the targets already present in samples."""
        self._require_trained()
        sample_values = list(samples)
        if not sample_values:
            raise ValueError("evaluation data must not be empty")
        features, targets = _prepare_samples(sample_values)
        return self._evaluate_rows(features, targets)

    def save(self, path: str | Path) -> None:
        """Save the XGBoost model and its authoritative feature ordering."""
        self._require_trained()
        model_path = Path(path)
        model_path.parent.mkdir(parents=True, exist_ok=True)
        self._model.save_model(model_path)
        metadata_path = _metadata_path(model_path)
        metadata_path.write_text(json.dumps({"feature_names": list(self.feature_names)}), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "TrafficPredictionModel":
        """Load a model and verify its persisted feature schema."""
        model_path = Path(path)
        metadata_path = _metadata_path(model_path)
        if not model_path.is_file() or not metadata_path.is_file():
            raise FileNotFoundError("model and feature-schema metadata files are required")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if tuple(metadata.get("feature_names", ())) != MODEL_FEATURE_NAMES:
            raise ValueError("saved model feature schema does not match MODEL_FEATURE_NAMES")
        instance = cls()
        instance._model.load_model(model_path)
        instance._trained = True
        return instance

    def _require_trained(self) -> None:
        if not self._trained:
            raise RuntimeError("traffic prediction model must be trained before use")

    def _evaluate_rows(self, features: list[list[float]], targets: list[float]) -> RegressionMetrics:
        return _calculate_metrics(self._model.predict(features), targets)


def _prepare_samples(samples: Sequence[TrafficTrainingSample]) -> tuple[list[list[float]], list[float]]:
    features, targets = split_features_and_target(samples)
    return [_prepare_feature_row(row) for row in features], [float(target) for target in targets]


def _prepare_feature_row(row: Mapping[str, object]) -> list[float]:
    missing = set(MODEL_FEATURE_NAMES) - set(row)
    unexpected = set(row) - set(MODEL_FEATURE_NAMES)
    if missing:
        raise ValueError(f"feature row is missing {sorted(missing)}")
    if unexpected:
        raise ValueError(f"feature row contains unsupported fields {sorted(unexpected)}")
    values: list[float] = []
    for name in MODEL_FEATURE_NAMES:
        value = row[name]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            raise ValueError(f"feature {name} must be a finite numeric value")
        values.append(float(value))
    return values


def _metadata_path(model_path: Path) -> Path:
    return model_path.with_name(model_path.name + ".metadata.json")


def _xgboost_defaults() -> dict[str, object]:
    return {
        "objective": "reg:squarederror",
        "n_estimators": 100,
        "max_depth": 3,
        "learning_rate": 0.05,
        "subsample": 0.9,
        "colsample_bytree": 0.9,
        "random_state": 42,
        "n_jobs": 1,
    }


def _calculate_metrics(predictions: Iterable[float], targets: Sequence[float]) -> RegressionMetrics:
    prediction_values = [float(value) for value in predictions]
    if len(prediction_values) != len(targets) or not targets:
        raise ValueError("predictions and targets must be non-empty and have equal length")
    errors = [prediction - target for prediction, target in zip(prediction_values, targets)]
    mae = sum(abs(error) for error in errors) / len(errors)
    rmse = math.sqrt(sum(error * error for error in errors) / len(errors))
    target_mean = sum(targets) / len(targets)
    total_sum_squares = sum((target - target_mean) ** 2 for target in targets)
    r2 = 1.0 - sum(error * error for error in errors) / total_sum_squares if total_sum_squares else 0.0
    return RegressionMetrics(mae, rmse, r2)