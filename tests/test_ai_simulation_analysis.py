import json
import os
import unittest
from unittest.mock import MagicMock, patch

from backend.app.ai.traffic_model import GroqLLMPredictor


SIMULATION_RESULT = {
    "city_id": 1,
    "closed_road_id": 101,
    "duration_hours": 4.0,
    "traffic": {
        "baseline_congestion": 0.2,
        "scenario_congestion": 0.4,
        "change_percent": 100.0,
        "baseline_travel_time_s": 60.0,
        "scenario_travel_time_s": 90.0,
    },
    "transit": {"delay_minutes": 4.0},
    "emergency": {"eta_increase_min": 2.0},
    "pollution": {"change_percent": 8.0},
    "metrics": [{"metric_type": "traffic_congestion", "scenario_value": 0.4}],
    "unserializable": object(),
}


class SimulationAnalysisTests(unittest.TestCase):
    def predictor_with_client(self, content: str) -> GroqLLMPredictor:
        with patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}):
            predictor = GroqLLMPredictor()
        predictor.groq_client = MagicMock()
        predictor.groq_client.chat.completions.create.return_value.choices[0].message.content = content
        return predictor

    def test_valid_result_returns_structured_analysis_and_compact_prompt(self) -> None:
        predictor = self.predictor_with_client(json.dumps({"summary": "Closure increases congestion."}))

        result = predictor.analyze_simulation(SIMULATION_RESULT)

        self.assertEqual("AVAILABLE", result["status"])
        self.assertEqual("Closure increases congestion.", result["analysis"]["summary"])
        prompt = predictor.groq_client.chat.completions.create.call_args.kwargs["messages"][0]["content"]
        self.assertIn('"scenario_congestion":0.4', prompt)
        self.assertNotIn("unserializable", prompt)
        self.assertEqual(500, predictor.groq_client.chat.completions.create.call_args.kwargs["max_tokens"])

    def test_missing_optional_metrics_are_explicitly_unavailable(self) -> None:
        predictor = self.predictor_with_client(json.dumps({"summary": "Traffic was evaluated."}))

        result = predictor.analyze_simulation({"city_id": 1, "traffic": {"change_percent": 10.0}})

        self.assertEqual("Unavailable: not evaluated", result["analysis"]["transit_impact"])
        self.assertEqual("Unavailable: not evaluated", result["analysis"]["emergency_impact"])
        self.assertEqual("Unavailable: not evaluated", result["analysis"]["pollution_impact"])
        prompt = predictor.groq_client.chat.completions.create.call_args.kwargs["messages"][0]["content"]
        self.assertIn("absent metric", prompt)

    def test_missing_key_returns_explicit_unavailable_result(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            predictor = GroqLLMPredictor()

        result = predictor.analyze_simulation(SIMULATION_RESULT)

        self.assertEqual("UNAVAILABLE", result["status"])
        self.assertIsNone(result["analysis"])

    def test_api_failure_and_malformed_json_are_safe(self) -> None:
        for content in ("{bad json", "[1, 2, 3]"):
            predictor = self.predictor_with_client(content)
            self.assertEqual("UNAVAILABLE", predictor.analyze_simulation(SIMULATION_RESULT)["status"])

        predictor = self.predictor_with_client("{}")
        predictor.groq_client.chat.completions.create.side_effect = RuntimeError("timeout")
        self.assertEqual("UNAVAILABLE", predictor.analyze_simulation(SIMULATION_RESULT)["status"])

    def test_existing_traffic_prediction_still_works(self) -> None:
        predictor = GroqLLMPredictor()
        prediction = predictor.predict({"vehicle_count": 350, "hour": 9, "road_capacity": 1500})

        self.assertEqual(1, len(prediction))
        self.assertGreater(prediction[0], 0)


if __name__ == "__main__":
    unittest.main()