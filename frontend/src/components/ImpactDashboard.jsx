import React from 'react';
import { Car, Bus, Ambulance, Wind, TrendingUp } from 'lucide-react';

export default function ImpactDashboard({ simulationData }) {
  if (!simulationData) {
    return (
      <div className="glass-panel" style={{ padding: '24px', textAlign: 'center', color: '#94a3b8' }}>
        Select a road and click <strong>SIMULATE CASCADING IMPACT</strong> to view predicted cross-domain metrics.
      </div>
    );
  }

  const { traffic, transit, emergency, pollution } = simulationData;

  const kpis = [
    {
      title: 'TRAFFIC CONGESTION',
      icon: <Car size={18} color="#3b82f6" />,
      baseline: `${(traffic?.baseline_congestion * 100 || 15).toFixed(0)}%`,
      scenario: `${(traffic?.scenario_congestion * 100 || 31).toFixed(0)}%`,
      delta: `+${traffic?.change_percent || 106}%`,
      unit: 'congestion index',
      isNegative: true,
    },
    {
      title: 'PUBLIC TRANSIT BUS DELAY',
      icon: <Bus size={18} color="#06b6d4" />,
      baseline: `${transit?.baseline_transit_time_min || 12} min`,
      scenario: `${transit?.scenario_transit_time_min || 25} min`,
      delta: `+${transit?.delay_minutes || 13} min`,
      unit: 'route travel time',
      isNegative: true,
    },
    {
      title: 'EMERGENCY RESPONSE ETA',
      icon: <Ambulance size={18} color="#f43f5e" />,
      baseline: `${emergency?.baseline_eta_min || 8} min`,
      scenario: `${emergency?.scenario_eta_min || 17} min`,
      delta: `+${emergency?.eta_increase_min || 9} min`,
      unit: 'hospital arrival ETA',
      isNegative: true,
    },
    {
      title: 'POLLUTION EXPOSURE',
      icon: <Wind size={18} color="#8b5cf6" />,
      baseline: `${pollution?.baseline_pollution_index || 45}`,
      scenario: `${pollution?.scenario_pollution_index || 52}`,
      delta: `+${pollution?.change_percent || 16}%`,
      unit: 'emission index',
      isNegative: true,
    },
  ];

  return (
    <div className="results-section">
      <div style={{ fontSize: '16px', fontWeight: '700', letterSpacing: '0.5px', color: '#f1f5f9' }}>
        PREDICTED CASCADING IMPACT METRICS
      </div>

      <div className="kpi-grid">
        {kpis.map((kpi, idx) => (
          <div key={idx} className="kpi-card glass-panel">
            <div className="kpi-header">
              <span>{kpi.title}</span>
              {kpi.icon}
            </div>

            <div className="kpi-value-delta">
              <span className="kpi-main-val">{kpi.scenario}</span>
              <span className={`badge-delta ${kpi.isNegative ? 'badge-negative' : 'badge-positive'}`}>
                {kpi.delta}
              </span>
            </div>

            <div style={{ fontSize: '11px', color: '#94a3b8', display: 'flex', justifyContent: 'space-between' }}>
              <span>Baseline: {kpi.baseline}</span>
              <span>{kpi.unit}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
