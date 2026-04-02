import React from 'react';
import { getHealthImpact, getRiskBar } from '../utils/healthImpact';

const HealthImpactCard = ({ aqi, mode = 'panel' }) => {
  const impact = getHealthImpact(aqi);
  const isModal = mode === 'modal';

  const demographics = [
    { icon: '👶', label: 'Children', text: impact.children },
    { icon: '👴', label: 'Elderly', text: impact.elderly },
    { icon: '❤️', label: 'Heart cond.', text: impact.heart },
    { icon: '🫁', label: 'Lung cond.', text: impact.lung },
    { icon: '🏃', label: 'Outdoor act.', text: impact.outdoor },
  ];

  const riskBar = getRiskBar(impact.risk);

  return (
    <div style={{ padding: isModal ? '28px 0' : '18px 0' }}>
      {/* Risk level indicator */}
      <div style={{ display: 'flex', alignItems: 'center', gap: isModal ? 14 : 10, marginBottom: isModal ? 22 : 14 }}>
        <span style={{ color: '#cbd5e1', fontSize: isModal ? 18 : 14, fontWeight: isModal ? 700 : 600 }}>Risk level</span>
        <div style={{ display: 'flex', gap: isModal ? 8 : 5 }}>
          {riskBar.map((filled, i) => (
            <div
              key={i}
              style={{
                width: isModal ? 34 : 24,
                height: isModal ? 12 : 9,
                borderRadius: 6,
                background: filled ? impact.color : '#1e293b',
                transition: 'background 0.3s',
              }}
            />
          ))}
        </div>
        <span style={{ color: impact.color, fontSize: isModal ? 18 : 14, fontWeight: 700 }}>
          {impact.category}
        </span>
      </div>

      {/* General advice */}
      <div
        style={{
          background: impact.color + (isModal ? '26' : '18'),
          border: `1px solid ${impact.color}${isModal ? '80' : '40'}`,
          borderRadius: 12,
          padding: isModal ? '18px 20px' : '12px 14px',
          marginBottom: isModal ? 20 : 14,
          color: '#f1f5f9',
          fontSize: isModal ? 20 : 15,
          fontWeight: isModal ? 600 : 500,
          lineHeight: 1.45,
        }}
      >
        {impact.general}
      </div>

      {/* Demographic breakdown */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: isModal ? 14 : 9 }}>
        {demographics.map((d) => (
          <div
            key={d.label}
            style={{
              display: 'grid',
              gridTemplateColumns: isModal ? '170px 1fr' : '120px 1fr',
              gap: isModal ? 12 : 8,
              alignItems: 'start',
            }}
          >
            <span style={{ color: '#cbd5e1', fontSize: isModal ? 16 : 12, display: 'flex', alignItems: 'center', gap: isModal ? 8 : 5, fontWeight: isModal ? 600 : 500 }}>
              <span style={{ fontSize: isModal ? 19 : 15 }}>{d.icon}</span>
              {d.label}
            </span>
            <span style={{ color: '#f1f5f9', fontSize: isModal ? 16 : 13, lineHeight: 1.5 }}>
              {d.text}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default HealthImpactCard;
