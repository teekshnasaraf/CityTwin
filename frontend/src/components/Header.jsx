import React from 'react';
import { Activity, ShieldCheck, MapPin } from 'lucide-react';

export default function Header({ selectedCity, onCityChange }) {
  return (
    <header className="app-header glass-panel">
      <div className="brand-section">
        <div className="logo-badge">CT</div>
        <div>
          <h1 style={{ fontSize: '20px', fontWeight: '800', background: 'linear-gradient(135deg, #06b6d4, #3b82f6)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            CITYTWIN
          </h1>
          <p style={{ fontSize: '11px', color: '#94a3b8', letterSpacing: '0.4px' }}>
            AI-POWERED URBAN DIGITAL TWIN & DECISION INTELLIGENCE
          </p>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <div className="city-select-box">
          <MapPin size={16} color="#06b6d4" />
          <select 
            className="custom-select" 
            value={selectedCity} 
            onChange={(e) => onCityChange(e.target.value)}
          >
            <option value="1">Chennai, India</option>
            <option value="2">Victoria, Australia</option>
            <option value="3">Singapore</option>
          </select>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 12px', background: 'rgba(16, 185, 129, 0.15)', border: '1px solid rgba(16, 185, 129, 0.3)', borderRadius: '20px', color: '#10b981', fontSize: '12px', fontWeight: '600' }}>
          <Activity size={14} className="pulse-dot" />
          DIGITAL TWIN ENGINE ACTIVE
        </div>
      </div>
    </header>
  );
}
