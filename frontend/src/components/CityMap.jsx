import React, { useState } from 'react';
import { Layers, AlertTriangle, Navigation, Hospital, ShieldAlert, Truck } from 'lucide-react';

export default function CityMap({ activeRoad, isSimulated, simulationData }) {
  const [activeLayers, setActiveLayers] = useState({
    roads: true,
    traffic: true,
    emergency: true,
    transit: true,
  });

  const toggleLayer = (layerKey) => {
    setActiveLayers((prev) => ({ ...prev, [layerKey]: !prev[layerKey] }));
  };

  // Grid node coordinates for interactive SVG rendering
  const nodes = [
    { id: 'N1', x: 120, y: 80, label: 'Central Junction' },
    { id: 'N2', x: 320, y: 80, label: 'Anna Salai North' },
    { id: 'N3', x: 520, y: 80, label: 'Airport Connector' },
    { id: 'N4', x: 120, y: 220, label: 'Port Corridor' },
    { id: 'N5', x: 320, y: 220, label: 'Anna Salai Main' },
    { id: 'N6', x: 520, y: 220, label: 'East Coast Junction' },
    { id: 'N7', x: 120, y: 360, label: 'Industrial Zone' },
    { id: 'N8', x: 320, y: 360, label: 'Anna Salai South' },
    { id: 'N9', x: 520, y: 360, label: 'IT Expressway' },
  ];

  const edges = [
    { id: 101, u: 'N2', v: 'N5', name: 'Anna Salai Main Segment', type: 'primary' },
    { id: 102, u: 'N1', v: 'N2', name: 'Mount Road West', type: 'primary' },
    { id: 103, u: 'N2', v: 'N3', name: 'GST Road East', type: 'primary' },
    { id: 104, u: 'N4', v: 'N5', name: 'Poonamallee High Rd', type: 'secondary' },
    { id: 105, u: 'N5', v: 'N6', name: 'Radhakrishnan Salai', type: 'secondary' },
    { id: 106, u: 'N5', v: 'N8', name: 'Anna Salai South Link', type: 'primary' },
    { id: 107, u: 'N7', v: 'N8', name: 'Guindy Bypass', type: 'secondary' },
    { id: 108, u: 'N8', v: 'N9', name: 'OMR Tech Corridor', type: 'primary' },
    { id: 109, u: 'N1', v: 'N4', name: 'Harbour Bypass', type: 'tertiary' },
    { id: 110, u: 'N3', v: 'N6', name: 'Velachery Link', type: 'tertiary' },
  ];

  const getNodeCoord = (id) => nodes.find((n) => n.id === id) || { x: 0, y: 0 };

  return (
    <div className="map-container glass-panel">
      {/* Layer Toggle Controls */}
      <div className="map-layer-controls">
        <button
          className={`layer-btn ${activeLayers.roads ? 'active' : ''}`}
          onClick={() => toggleLayer('roads')}
        >
          <Layers size={13} style={{ display: 'inline', marginRight: 4 }} /> Roads
        </button>
        <button
          className={`layer-btn ${activeLayers.traffic ? 'active' : ''}`}
          onClick={() => toggleLayer('traffic')}
        >
          Traffic Heat
        </button>
        <button
          className={`layer-btn ${activeLayers.emergency ? 'active' : ''}`}
          onClick={() => toggleLayer('emergency')}
        >
          Emergency POIs
        </button>
        <button
          className={`layer-btn ${activeLayers.transit ? 'active' : ''}`}
          onClick={() => toggleLayer('transit')}
        >
          Bus Corridors
        </button>
      </div>

      {/* SVG Map Viewport */}
      <svg className="svg-map-viewport" viewBox="0 0 640 420">
        <defs>
          <linearGradient id="closedGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#f43f5e" />
            <stop offset="100%" stopColor="#e11d48" />
          </linearGradient>
          <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>

        {/* Road Grid Lines */}
        {activeLayers.roads &&
          edges.map((e) => {
            const u = getNodeCoord(e.u);
            const v = getNodeCoord(e.v);
            const isClosed = isSimulated && e.id === Number(activeRoad);
            const isRerouted = isSimulated && !isClosed && (e.id === 104 || e.id === 105 || e.id === 106);

            let strokeColor = '#334155';
            let strokeWidth = e.type === 'primary' ? 6 : 4;

            if (activeLayers.traffic) {
              if (isClosed) {
                strokeColor = 'url(#closedGrad)';
                strokeWidth = 9;
              } else if (isRerouted) {
                strokeColor = '#f59e0b'; // Congested amber
                strokeWidth = 7;
              } else if (e.type === 'primary') {
                strokeColor = '#3b82f6';
              }
            }

            return (
              <g key={e.id}>
                <line
                  x1={u.x}
                  y1={u.y}
                  x2={v.x}
                  y2={v.y}
                  stroke={strokeColor}
                  strokeWidth={strokeWidth}
                  strokeLinecap="round"
                  filter={isClosed || isRerouted ? 'url(#glow)' : undefined}
                />
                {isClosed && (
                  <line
                    x1={u.x}
                    y1={u.y}
                    x2={v.x}
                    y2={v.y}
                    stroke="#ffffff"
                    strokeWidth="2"
                    strokeDasharray="6 6"
                  />
                )}
              </g>
            );
          })}

        {/* Intersections / Nodes */}
        {nodes.map((n) => (
          <g key={n.id} transform={`translate(${n.x}, ${n.y})`}>
            <circle r="7" fill="#1e293b" stroke="#06b6d4" strokeWidth="2" />
            <text x="12" y="4" fill="#94a3b8" fontSize="10" fontWeight="500">
              {n.label}
            </text>
          </g>
        ))}

        {/* Emergency POI Markers */}
        {activeLayers.emergency && (
          <>
            <g transform="translate(120, 80)">
              <circle r="14" fill="rgba(244, 63, 94, 0.25)" stroke="#f43f5e" strokeWidth="1.5" />
              <text x="-6" y="5" fill="#f43f5e" fontSize="12" fontWeight="800">H</text>
            </g>
            <g transform="translate(520, 360)">
              <circle r="14" fill="rgba(245, 158, 11, 0.25)" stroke="#f59e0b" strokeWidth="1.5" />
              <text x="-5" y="5" fill="#f59e0b" fontSize="12" fontWeight="800">F</text>
            </g>
          </>
        )}

        {/* Simulation Banner Overlay */}
        {isSimulated && (
          <g transform="translate(320, 150)">
            <rect x="-100" y="-18" width="200" height="36" rx="18" fill="rgba(244, 63, 94, 0.9)" />
            <text x="0" y="5" textAnchor="middle" fill="#ffffff" fontSize="12" fontWeight="700">
              ⚠️ ROAD CLOSED — TRAFFIC REROUTED
            </text>
          </g>
        )}
      </svg>
    </div>
  );
}
