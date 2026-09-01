import React from 'react';
import { Sliders, Play, Award, CloudRain, Car, Clock } from 'lucide-react';

export default function ScenarioBuilder({
  scenarioParams,
  onParamChange,
  onRunSimulation,
  onEvaluateRecommendations,
  loading,
}) {
  return (
    <div className="builder-panel glass-panel">
      <div className="panel-title">
        <Sliders size={20} color="#3b82f6" />
        SCENARIO BUILDER
      </div>

      <div className="form-group">
        <label className="form-label">Intervention Type</label>
        <select
          className="form-input"
          value={scenarioParams.scenario_type}
          onChange={(e) => onParamChange('scenario_type', e.target.value)}
        >
          <option value="road_closure">Road Closure (Virtual Modification)</option>
          <option value="capacity_reduction">Lane Capacity Reduction (50%)</option>
          <option value="event_traffic">Major Stadium Event Traffic</option>
        </select>
      </div>

      <div className="form-group">
        <label className="form-label">Target Road Segment</label>
        <select
          className="form-input"
          value={scenarioParams.road_id}
          onChange={(e) => onParamChange('road_id', Number(e.target.value))}
        >
          <option value={101}>Anna Salai Main Corridor (Segment #101)</option>
          <option value={102}>Mount Road West Junction (#102)</option>
          <option value={103}>GST Road Airport Link (#103)</option>
          <option value={106}>OMR Tech Expressway (#106)</option>
        </select>
      </div>

      <div className="form-group">
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <label className="form-label">Closure Duration</label>
          <span style={{ fontSize: '13px', fontWeight: '700', color: '#06b6d4' }}>
            {scenarioParams.duration_hours} Hours
          </span>
        </div>
        <input
          type="range"
          min="1"
          max="24"
          step="1"
          className="form-range"
          value={scenarioParams.duration_hours}
          onChange={(e) => onParamChange('duration_hours', Number(e.target.value))}
        />
      </div>

      <div className="form-group">
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <label className="form-label">Traffic Volume Multiplier</label>
          <span style={{ fontSize: '13px', fontWeight: '700', color: '#3b82f6' }}>
            +{Math.round((scenarioParams.traffic_factor - 1) * 100)}%
          </span>
        </div>
        <input
          type="range"
          min="1.0"
          max="2.0"
          step="0.05"
          className="form-range"
          value={scenarioParams.traffic_factor}
          onChange={(e) => onParamChange('traffic_factor', Number(e.target.value))}
        />
      </div>

      <div className="form-group">
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <label className="form-label">Rainfall / Weather Factor</label>
          <span style={{ fontSize: '13px', fontWeight: '700', color: '#8b5cf6' }}>
            +{Math.round((scenarioParams.weather_factor - 1) * 100)}% Rain
          </span>
        </div>
        <input
          type="range"
          min="1.0"
          max="2.0"
          step="0.1"
          className="form-range"
          value={scenarioParams.weather_factor}
          onChange={(e) => onParamChange('weather_factor', Number(e.target.value))}
        />
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '10px' }}>
        <button
          className="btn-primary"
          onClick={onRunSimulation}
          disabled={loading}
          style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}
        >
          <Play size={16} />
          {loading ? 'RUNNING SIMULATION...' : 'SIMULATE CASCADING IMPACT'}
        </button>

        <button
          className="btn-secondary"
          onClick={onEvaluateRecommendations}
          disabled={loading}
          style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}
        >
          <Award size={16} color="#10b981" />
          RANK INTERVENTION OPTIONS
        </button>
      </div>
    </div>
  );
}
