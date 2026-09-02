import unittest
from unittest.mock import MagicMock, patch

from backend.app.api.simulation import SimulationRunRequest, run_simulation


SIMULATION_RESULT = {
    "city_id": 1,
    "closed_road_id": 101,
    "duration_hours": 4.0,
    "traffic": {"baseline_congestion": 0.2, "scenario_congestion": 0.4},
    "transit": {"delay_minutes": 4.0},
    "emergency": {"eta_increase_min": 2.0},
    "pollution": {"change_percent": 8.0},
    "metrics": [{"metric_type": "traffic_congestion", "baseline_value": 0.2, "scenario_value": 0.4, "change_percent": 100.0, "unit": "index"}],
}


class SimulationGroqApiTests(unittest.TestCase):
    def request(self) -> SimulationRunRequest:
        return SimulationRunRequest(city_id=1, closed_road_id=101)

    @patch("backend.app.api.simulation.DigitalTwinEngine.run_scenario_simulation", return_value=SIMULATION_RESULT.copy())
    @patch("backend.app.api.simulation.GroqLLMPredictor")
    def test_available_analysis_is_attached_without_changing_simulation_results(self, predictor_class, run_simulation_mock) -> None:
        analysis = {"status": "AVAILABLE", "model_used": "Groq Llama", "analysis": {"summary": "Closure increases congestion."}}
        predictor_class.return_value.analyze_simulation.return_value = analysis

        result = run_simulation(self.request(), MagicMock())

        self.assertEqual(analysis, result["ai_analysis"])
        self.assertEqual(0.4, result["traffic"]["scenario_congestion"])
        self.assertEqual(SIMULATION_RESULT["metrics"], result["metrics"])
        predictor_class.return_value.analyze_simulation.assert_called_once()
        run_simulation_mock.assert_called_once()

    @patch("backend.app.api.simulation.DigitalTwinEngine.run_scenario_simulation", return_value=SIMULATION_RESULT.copy())
    @patch("backend.app.api.simulation.GroqLLMPredictor")
    def test_unavailable_analysis_preserves_simulation_result(self, predictor_class, run_simulation_mock) -> None:
        predictor_class.return_value.analyze_simulation.return_value = {"status": "UNAVAILABLE", "analysis": None, "reason": "no key"}

        result = run_simulation(self.request(), MagicMock())

        self.assertEqual("UNAVAILABLE", result["ai_analysis"]["status"])
        self.assertIsNone(result["ai_analysis"]["analysis"])
        self.assertIn("traffic", result)
        self.assertIn("transit", result)
        self.assertIn("emergency", result)
        self.assertIn("pollution", result)
        self.assertEqual(len(SIMULATION_RESULT["metrics"]), len(result["metrics"]))

    @patch("backend.app.api.simulation.DigitalTwinEngine.run_scenario_simulation", return_value=SIMULATION_RESULT.copy())
    @patch("backend.app.api.simulation.GroqLLMPredictor")
    def test_analyzer_exception_does_not_fail_simulation(self, predictor_class, run_simulation_mock) -> None:
        predictor_class.return_value.analyze_simulation.side_effect = RuntimeError("Groq timeout")

        result = run_simulation(self.request(), MagicMock())

        self.assertEqual("UNAVAILABLE", result["ai_analysis"]["status"])
        self.assertEqual(0.2, result["traffic"]["baseline_congestion"])
        self.assertEqual(4.0, result["duration_hours"])


if __name__ == "__main__":
    unittest.main()