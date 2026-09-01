import React from 'react';
import { Award, CheckCircle, AlertCircle, ArrowRight } from 'lucide-react';

export default function RecommendationCard({ recommendationData }) {
  if (!recommendationData || !recommendationData.recommendations) {
    return null;
  }

  const { best_option, recommendations } = recommendationData;

  return (
    <div className="glass-panel recommendation-banner" style={{ margin: '0 28px 28px 28px' }}>
      <div className="recommendation-rank">
        <Award size={22} color="#10b981" />
        <span>OPTIMAL INTERVENTION RECOMMENDATION</span>
        <span className="opt-pill">RECOMMENDED</span>
      </div>

      <p style={{ fontSize: '14px', color: '#cbd5e1', lineHeight: '1.6' }}>
        {recommendations[0]?.reason}
      </p>

      <div style={{ display: 'flex', gap: '16px', marginTop: '8px' }}>
        {recommendations.map((rec) => (
          <div
            key={rec.rank}
            style={{
              flex: 1,
              padding: '12px 16px',
              background: rec.rank === 1 ? 'rgba(16, 185, 129, 0.1)' : 'rgba(255, 255, 255, 0.03)',
              border: rec.rank === 1 ? '1px solid rgba(16, 185, 129, 0.4)' : '1px solid rgba(255, 255, 255, 0.08)',
              borderRadius: '8px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', fontWeight: '700', color: rec.rank === 1 ? '#10b981' : '#94a3b8' }}>
              <span>RANK #{rec.rank}</span>
              <span>SCORE: {rec.score}</span>
            </div>
            <div style={{ fontSize: '13px', fontWeight: '600', marginTop: '4px', color: '#f1f5f9' }}>
              {rec.intervention}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
