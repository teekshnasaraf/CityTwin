import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from backend.app.ai.data_generator import generate_traffic_state
from backend.app.ai.features import MODEL_FEATURE_NAMES, build_training_samples, split_features_and_target
from backend.app.ai.traffic_model import TrafficPredictionModel, chronological_split, compare_models


class TrafficModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        records = generate_traffic_state(
            [{"road_id": "road_a", "road_length": 800, "lanes": 3, "capacity": 1800}],
            datetime(2026, 1, 5, 5),
            timedelta(hours=5, minutes=15),
            timedelta(minutes=15),
            seed=17,
        )
        cls.samples = build_training_samples(records)

    def test_trains_and_predicts_numeric_values(self) -> None:
        model = TrafficPredictionModel(n_estimators=20)

        result = model.train(self.samples, test_size=0.25)
        features, _ = split_features_and_target(self.samples[:2])
        predictions = model.predict(features)

        self.assertGreater(result.train_samples, 0)
        self.assertGreater(result.test_samples, 0)
        self.assertEqual(2, len(predictions))
        self.assertTrue(all(isinstance(value, float) for value in predictions))

    def test_chronological_split_keeps_latest_samples_for_test(self) -> None:
        train, test = chronological_split(self.samples, test_size=0.25)

        self.assertLessEqual(train[-1].timestamp, test[0].timestamp)
        self.assertEqual(sorted(self.samples, key=lambda sample: (sample.timestamp, sample.road_id)), train + test)

    def test_evaluation_returns_regression_metrics(self) -> None:
        model = TrafficPredictionModel(n_estimators=20)
        model.train(self.samples, test_size=0.25)

        metrics = model.evaluate(self.samples[-2:])

        self.assertGreaterEqual(metrics.mae, 0)
        self.assertGreaterEqual(metrics.rmse, 0)
        self.assertLessEqual(metrics.r2, 1)

    def test_predict_before_training_fails(self) -> None:
        model = TrafficPredictionModel()
        features, _ = split_features_and_target(self.samples[:1])

        with self.assertRaisesRegex(RuntimeError, "trained"):
            model.predict(features)

    def test_save_and_load_preserve_predictions_and_feature_order(self) -> None:
        model = TrafficPredictionModel(n_estimators=20)
        model.train(self.samples, test_size=0.25)
        features, _ = split_features_and_target(self.samples[:2])
        expected = model.predict(features)

        with tempfile.TemporaryDirectory() as directory:
            model_path = Path(directory) / "traffic_model.json"
            model.save(model_path)
            loaded = TrafficPredictionModel.load(model_path)

            self.assertEqual(MODEL_FEATURE_NAMES, loaded.feature_names)
            self.assertEqual(expected, loaded.predict(features))

    def test_malformed_or_empty_inputs_fail_clearly(self) -> None:
        with self.assertRaisesRegex(ValueError, "empty"):
            TrafficPredictionModel().train([])
        model = TrafficPredictionModel(n_estimators=20)
        model.train(self.samples, test_size=0.25)
        with self.assertRaisesRegex(ValueError, "missing"):
            model.predict({"vehicle_count": 1})

    def test_future_target_is_not_a_model_feature(self) -> None:
        features, targets = split_features_and_target(self.samples[:1])

        self.assertNotIn("target_vehicle_count", features[0])
        self.assertNotIn("road_id", features[0])
        self.assertNotIn("timestamp", features[0])
        self.assertEqual(1, len(targets))

    def test_compare_models_evaluates_all_candidates_on_one_split(self) -> None:
        comparison = compare_models(self.samples, test_size=0.25)

        self.assertEqual(
            {"Linear Regression", "Random Forest Regressor", "XGBoost Regressor"},
            {result.model_name for result in comparison.results},
        )
        self.assertEqual({result.train_samples for result in comparison.results}, {len(comparison.train_samples)})
        self.assertEqual({result.test_samples for result in comparison.results}, {len(comparison.test_samples)})
        self.assertEqual(
            sorted(self.samples, key=lambda sample: (sample.timestamp, sample.road_id)),
            list(comparison.train_samples + comparison.test_samples),
        )
        self.assertIn(comparison.best_model_name, {result.model_name for result in comparison.results})

    def test_comparison_results_have_metrics_and_selected_model_predicts(self) -> None:
        comparison = compare_models(self.samples, test_size=0.25)
        features, _ = split_features_and_target(comparison.test_samples[:2])

        for result in comparison.results:
            self.assertGreaterEqual(result.metrics.mae, 0)
            self.assertGreaterEqual(result.metrics.rmse, 0)
            self.assertLessEqual(result.metrics.r2, 1)
            self.assertEqual(MODEL_FEATURE_NAMES, result.model.feature_names)
        self.assertEqual(2, len(comparison.best_model.predict(features)))

    def test_selection_prefers_lower_mae(self) -> None:
        comparison = compare_models(self.samples, test_size=0.25)

        best_result = min(comparison.results, key=lambda result: (result.metrics.mae, result.metrics.rmse, result.model_name))
        self.assertEqual(best_result.model_name, comparison.best_model_name)


if __name__ == "__main__":
    unittest.main()