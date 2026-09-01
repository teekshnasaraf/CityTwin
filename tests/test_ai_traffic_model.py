import unittest
from datetime import datetime, timedelta

from backend.app.ai.data_generator import generate_traffic_state
from backend.app.ai.features import build_training_samples
from backend.app.ai.traffic_model import GroqLLMPredictor, chronological_split, compare_models


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

    def test_groq_llm_predicts_numeric_values(self) -> None:
        model = GroqLLMPredictor(model_name="Groq Llama-3.3-70B Versatile")
        feature_row = {
            "road_id": "101",
            "hour": 9,
            "day_of_week": 1,
            "temperature": 30.0,
            "rainfall": 0.0,
            "vehicle_count": 350,
            "road_capacity": 1500,
        }
        predictions = model.predict(feature_row)

        self.assertEqual(1, len(predictions))
        self.assertTrue(all(isinstance(value, float) for value in predictions))
        self.assertGreater(predictions[0], 0.0)

    def test_chronological_split_keeps_latest_samples_for_test(self) -> None:
        train, test = chronological_split(self.samples, test_size=0.25)

        self.assertLessEqual(train[-1].timestamp, test[0].timestamp)
        self.assertEqual(sorted(self.samples, key=lambda sample: (sample.timestamp, sample.road_id)), train + test)

    def test_compare_models_evaluates_groq_candidates(self) -> None:
        comparison = compare_models(self.samples, test_size=0.25)

        model_names = {result.model_name for result in comparison.results}
        self.assertIn("Groq Llama-3.3-70B Versatile", model_names)
        self.assertEqual({result.train_samples for result in comparison.results}, {len(comparison.train_samples)})
        self.assertEqual({result.test_samples for result in comparison.results}, {len(comparison.test_samples)})
        self.assertEqual(comparison.best_model_name, "Groq Llama-3.3-70B Versatile")


if __name__ == "__main__":
    unittest.main()