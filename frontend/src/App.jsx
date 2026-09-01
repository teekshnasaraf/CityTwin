import React, { useState, useEffect } from 'react';
import Header from './components/Header.jsx';
import CityMap from './components/CityMap.jsx';
import ScenarioBuilder from './components/ScenarioBuilder.jsx';
import ImpactDashboard from './components/ImpactDashboard.jsx';
import RecommendationCard from './components/RecommendationCard.jsx';
import FreshnessIndicator from './components/FreshnessIndicator.jsx';

export default function App() {
  const [selectedCity, setSelectedCity] = useState('1');
  const [scenarioParams, setScenarioParams] = useState({
    scenario_type: 'road_closure',
    road_id: 101,
    duration_hours: 4,
    traffic_factor: 1.1,
    weather_factor: 1.2,
  });

  const [loading, setLoading] = useState(false);
  const [isSimulated, setIsSimulated] = useState(false);
  const [simulationData, setSimulationData] = useState(null);
  const [recommendationData, setRecommendationData] = useState(null);
  const [trafficState, setTrafficState] = useState(null);
  const [weatherState, setWeatherState] = useState(null);

  const API_BASE = 'http://127.0.0.1:8000/api/v1';

  // Fetch initial city state & freshness indicators
  useEffect(() => {
    fetch(`${API_BASE}/cities/${selectedCity}/traffic/latest`)
      .then((res) => res.json())
      .then((data) => setTrafficState(data))
      .catch(() => {});

    fetch(`${API_BASE}/cities/${selectedCity}/weather/latest`)
      .then((res) => res.json())
      .then((data) => setWeatherState(data))
      .catch(() => {});
  }, [selectedCity]);

  const handleParamChange = (key, value) => {
    setScenarioParams((prev) => ({ ...prev, [key]: value }));
  };

  const handleRunSimulation = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/simulations/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          city_id: Number(selectedCity),
          closed_road_id: scenarioParams.road_id,
          duration_hours: scenarioParams.duration_hours,
          capacity_factor: scenarioParams.scenario_type === 'capacity_reduction' ? 0.5 : 0.0,
          traffic_factor: scenarioParams.traffic_factor,
          weather_factor: scenarioParams.weather_factor,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setSimulationData(data);
        setIsSimulated(true);
      }
    } catch (err) {
      console.error('Simulation request failed:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleEvaluateRecommendations = async () => {
    setLoading(true);
    try {
      const response = await fetch(
        `${API_BASE}/simulations/recommendation/evaluate?city_id=${selectedCity}&closed_road_id=${scenarioParams.road_id}&duration_hours=${scenarioParams.duration_hours}`
      );

      if (response.ok) {
        const data = await response.json();
        setRecommendationData(data);
        if (data.recommendations && data.recommendations[0]) {
          setSimulationData(data.recommendations[0].simulation);
          setIsSimulated(true);
        }
      }
    } catch (err) {
      console.error('Recommendation request failed:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container-layout">
      <Header selectedCity={selectedCity} onCityChange={setSelectedCity} />

      <main className="dashboard-grid">
        <CityMap
          activeRoad={scenarioParams.road_id}
          isSimulated={isSimulated}
          simulationData={simulationData}
        />

        <ScenarioBuilder
          scenarioParams={scenarioParams}
          onParamChange={handleParamChange}
          onRunSimulation={handleRunSimulation}
          onEvaluateRecommendations={handleEvaluateRecommendations}
          loading={loading}
        />
      </main>

      <ImpactDashboard simulationData={simulationData} />

      <RecommendationCard recommendationData={recommendationData} />

      <FreshnessIndicator trafficState={trafficState} weatherState={weatherState} />
    </div>
  );
}
