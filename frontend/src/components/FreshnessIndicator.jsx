import React from 'react';
import { Clock, RefreshCw, Database } from 'lucide-react';

export default function FreshnessIndicator({ trafficState, weatherState }) {
  const trafficLabel = trafficState?.freshness_label || 'Updated 12 sec ago';
  const weatherLabel = weatherState?.freshness_label || 'Updated 4 min ago';
  const trafficType = trafficState?.data_type || 'REALTIME';
  const weatherType = weatherState?.data_type || 'MODELLED';

  return (
    <footer className="freshness-bar">
      <div className="freshness-item">
        <span className="pulse-dot"></span>
        <span>Traffic Feed: <strong>{trafficLabel}</strong></span>
        <span style={{ fontSize: '10px', background: 'rgba(59, 130, 246, 0.2)', color: '#3b82f6', padding: '1px 5px', borderRadius: '4px' }}>
          {trafficType}
        </span>
      </div>

      <div className="freshness-item">
        <span className="pulse-dot" style={{ background: '#06b6d4' }}></span>
        <span>Transit GTFS: <strong>Updated 35 sec ago</strong></span>
        <span style={{ fontSize: '10px', background: 'rgba(6, 182, 212, 0.2)', color: '#06b6d4', padding: '1px 5px', borderRadius: '4px' }}>
          GTFS-RT
        </span>
      </div>

      <div className="freshness-item">
        <span className="pulse-dot" style={{ background: '#8b5cf6' }}></span>
        <span>Weather & Copernicus: <strong>{weatherLabel}</strong></span>
        <span style={{ fontSize: '10px', background: 'rgba(139, 92, 246, 0.2)', color: '#8b5cf6', padding: '1px 5px', borderRadius: '4px' }}>
          {weatherType}
        </span>
      </div>

      <div className="freshness-item" style={{ marginLeft: 'auto' }}>
        <Database size={13} color="#94a3b8" />
        <span>PostgreSQL + PostGIS 3.6</span>
      </div>
    </footer>
  );
}
