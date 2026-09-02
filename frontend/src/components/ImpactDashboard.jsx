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

      {simulationData.ai_analysis && (
        <div style={{ marginTop: '32px', background: 'rgba(15, 23, 42, 0.6)', border: '1px solid #334155', borderRadius: '12px', padding: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '20px', borderBottom: '1px solid #334155', paddingBottom: '12px' }}>
            <TrendingUp size={20} color="#10b981" />
            <span style={{ fontSize: '15px', fontWeight: '700', letterSpacing: '0.5px', color: '#10b981' }}>
              GROQ AI URBAN IMPACT ANALYSIS
            </span>
            <span style={{ marginLeft: 'auto', fontSize: '12px', color: '#94a3b8' }}>
              {simulationData.ai_analysis.status === 'AVAILABLE' ? `Powered by ${simulationData.ai_analysis.model_used || 'Groq'}` : 'Analysis Unavailable'}
            </span>
          </div>

          {simulationData.ai_analysis.status === 'AVAILABLE' && simulationData.ai_analysis.analysis ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div>
                <div style={{ fontSize: '12px', color: '#94a3b8', marginBottom: '4px', textTransform: 'uppercase', fontWeight: 'bold' }}>Summary</div>
                <div style={{ fontSize: '14px', color: '#f1f5f9' }}>{simulationData.ai_analysis.analysis.summary}</div>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                <div>
                  <div style={{ fontSize: '12px', color: '#94a3b8', marginBottom: '4px', textTransform: 'uppercase', fontWeight: 'bold' }}>Traffic Impact</div>
                  <div style={{ fontSize: '14px', color: '#cbd5e1' }}>{simulationData.ai_analysis.analysis.traffic_impact}</div>
                </div>
                <div>
                  <div style={{ fontSize: '12px', color: '#94a3b8', marginBottom: '4px', textTransform: 'uppercase', fontWeight: 'bold' }}>Travel-Time Impact</div>
                  <div style={{ fontSize: '14px', color: '#cbd5e1' }}>{simulationData.ai_analysis.analysis.travel_time_impact}</div>
                </div>
              </div>
              <div>
                <div style={{ fontSize: '12px', color: '#94a3b8', marginBottom: '4px', textTransform: 'uppercase', fontWeight: 'bold' }}>Key Trade-off</div>
                <div style={{ fontSize: '14px', color: '#f59e0b' }}>{simulationData.ai_analysis.analysis.key_tradeoff}</div>
              </div>
              <div style={{ background: 'rgba(16, 185, 129, 0.1)', borderLeft: '3px solid #10b981', padding: '12px', borderRadius: '4px' }}>
                <div style={{ fontSize: '12px', color: '#10b981', marginBottom: '4px', textTransform: 'uppercase', fontWeight: 'bold' }}>Recommendation</div>
                <div style={{ fontSize: '14px', color: '#f1f5f9', marginBottom: '8px' }}>{simulationData.ai_analysis.analysis.recommendation}</div>
                <div style={{ fontSize: '12px', color: '#cbd5e1', fontStyle: 'italic' }}>Reasoning: {simulationData.ai_analysis.analysis.reasoning}</div>
              </div>
            </div>
          ) : (
            <div style={{ fontSize: '14px', color: '#94a3b8' }}>
              {simulationData.ai_analysis.reason || "AI reasoning is currently unavailable. Displaying raw simulation values only."}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
