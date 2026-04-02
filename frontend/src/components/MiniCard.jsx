import { useMemo, useState } from 'react';

const ShimmerLines = () => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
    {[82, 64, 90].map((w, i) => (
      <div
        key={i}
        style={{
          height: 10,
          width: `${w}%`,
          borderRadius: 4,
          background: 'linear-gradient(90deg,#1e293b 25%,#334155 50%,#1e293b 75%)',
          backgroundSize: '200% 100%',
          animation: 'shimmer 1.5s infinite'
        }}
      />
    ))}
  </div>
);

const MiniCardBody = ({ cardId, content }) => {
  switch (cardId) {
    case 'aqi':
      return (
        <div>
          <span style={{ fontSize: 40, fontWeight: 800, color: content.primaryColor, lineHeight: 1 }}>
            {content.primary}
          </span>
          <span style={{ fontSize: 13, color: 'rgba(255,255,255,0.72)', marginLeft: 8 }}>
            {content.secondary}
          </span>
          <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.5)', marginTop: 5 }}>
            {content.tertiary}
          </div>
        </div>
      );

    case 'pollutants': {
      const bars = [
        { name: 'PM2.5', val: content.pm25, color: '#f87171' },
        { name: 'O3', val: content.ozone, color: '#38bdf8' },
        { name: 'NO2', val: content.no2, color: '#fb923c' },
        { name: 'CO', val: content.co, color: '#94a3b8' }
      ];
      const maxVal = Math.max(...bars.map((b) => b.val ?? 0), 1);
      return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
          {bars.map((b) => (
            <div key={b.name} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.65)', width: 36 }}>{b.name}</span>
              <div style={{ flex: 1, height: 7, background: 'rgba(255,255,255,0.1)', borderRadius: 3, overflow: 'hidden' }}>
                <div style={{ width: `${Math.min(100, ((b.val ?? 0) / maxVal) * 100)}%`, height: '100%', background: b.color, borderRadius: 2 }} />
              </div>
            </div>
          ))}
        </div>
      );
    }

    case 'health':
      return (
        <div>
          <div style={{ display: 'flex', gap: 3, marginBottom: 5 }}>
            {Array.from({ length: 5 }, (_, i) => (
              <div
                key={i}
                style={{
                  width: 22,
                  height: 8,
                  borderRadius: 3,
                  background: i < content.risk ? content.color : 'rgba(255,255,255,0.1)'
                }}
              />
            ))}
          </div>
          <div
            style={{
              fontSize: 12,
              color: 'rgba(255,255,255,0.72)',
              lineHeight: 1.4,
              display: '-webkit-box',
              WebkitLineClamp: 2,
              WebkitBoxOrient: 'vertical',
              overflow: 'hidden'
            }}
          >
            {content.advice}
          </div>
        </div>
      );

    case 'forecast': {
      const sparkVals = content.sparkData ?? [];
      if (sparkVals.length < 2) {
        return <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.3)' }}>No forecast data</div>;
      }
      const spMin = Math.min(...sparkVals);
      const spMax = Math.max(...sparkVals) || 1;
      const spW = 192;
      const spH = 50;
      const pts = sparkVals
        .map((v, i) => {
          const x = (i / (sparkVals.length - 1)) * spW;
          const y = spH - ((v - spMin) / (spMax - spMin || 1)) * spH;
          return `${x},${y}`;
        })
        .join(' ');

      const trendConfig = {
        worsening: { color: '#ef4444', icon: '▲' },
        improving: { color: '#22c55e', icon: '▼' },
        stable: { color: '#94a3b8', icon: '→' }
      };
      const tc = trendConfig[content.trend] ?? trendConfig.stable;

      return (
        <div>
          <svg width={spW} height={spH} style={{ display: 'block' }}>
            <polyline points={pts} fill="none" stroke={tc.color} strokeWidth="2.4" strokeLinejoin="round" />
          </svg>
          <div style={{ fontSize: 12, fontWeight: 600, color: tc.color, marginTop: 4 }}>
            {tc.icon} {content.trend}
          </div>
        </div>
      );
    }

    case 'shap': {
      const top = content.topFeature;
      return (
        <div>
          <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.65)', marginBottom: 5 }}>Top driver</div>
          <div style={{ fontSize: 15, color: '#e2e8f0', fontWeight: 600 }}>{top?.feature ?? '—'}</div>
          <div style={{ fontSize: 12, marginTop: 4, color: (top?.contribution ?? 0) > 0 ? '#f87171' : '#2dd4bf' }}>
            {(top?.contribution ?? 0) > 0 ? '+' : ''}
            {(top?.contribution ?? 0).toFixed(1)} AQI impact
          </div>
        </div>
      );
    }

    case 'simulate': {
      const delta = Number(content.delta ?? 0);
      const trendColor = delta <= 0 ? '#22c55e' : '#ef4444';
      return (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
            <span style={{ fontSize: 12, color: 'rgba(255,255,255,0.7)' }}>Live</span>
            <span style={{ fontSize: 12, color: '#cbd5e1', fontWeight: 700 }}>{Number(content.live || 0).toFixed(0)}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
            <span style={{ fontSize: 12, color: 'rgba(255,255,255,0.7)' }}>Sim</span>
            <span style={{ fontSize: 12, color: '#e2e8f0', fontWeight: 700 }}>{Number(content.simulated || 0).toFixed(0)}</span>
          </div>
          <div style={{ fontSize: 13, fontWeight: 700, color: trendColor }}>
            {delta > 0 ? '+' : ''}{delta.toFixed(1)} AQI
          </div>
        </div>
      );
    }

    default:
      return null;
  }
};

const MiniCard = ({ card, content, index, onClick }) => {
  const [hovered, setHovered] = useState(false);

  const baseStyle = useMemo(
    () => ({
      position: 'absolute',
      left: card.x,
      top: card.y,
      width: card.w || 220,
      minHeight: card.h || 132,
      padding: '14px 16px',
      background: 'rgba(10, 15, 30, 0.65)',
      backdropFilter: 'blur(16px) saturate(180%)',
      WebkitBackdropFilter: 'blur(16px) saturate(180%)',
      border: `1px solid ${hovered ? 'rgba(255,255,255,0.28)' : 'rgba(255,255,255,0.11)'}`,
      borderRadius: 18,
      boxShadow: hovered
        ? '0 12px 40px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.14), 0 0 20px rgba(99,153,220,0.12)'
        : '0 8px 32px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.07)',
      transform: hovered ? 'scale(1.04) translateY(-2px)' : 'scale(1)',
      transition: 'all 0.2s ease',
      cursor: 'pointer',
      pointerEvents: 'auto',
      animation: `cardEnter 0.45s cubic-bezier(0.34,1.56,0.64,1) ${index * 80}ms both`,
      color: 'white',
      userSelect: 'none'
    }),
    [card.x, card.y, hovered, index]
  );

  return (
    <>
      <style>{`
        @keyframes cardEnter {
          from { opacity:0; transform:scale(0.6) translateY(10px); }
          to   { opacity:1; transform:scale(1) translateY(0); }
        }
        @keyframes shimmer {
          0%   { background-position: 200% 0; }
          100% { background-position: -200% 0; }
        }
      `}</style>
      <div style={baseStyle} onClick={onClick} onMouseEnter={() => setHovered(true)} onMouseLeave={() => setHovered(false)}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
          <span style={{ fontSize: 15, opacity: 0.6 }}>{card.icon}</span>
          <span
            style={{
              fontSize: 12,
              fontWeight: 700,
              color: 'rgba(255,255,255,0.78)',
              letterSpacing: '0.05em',
              textTransform: 'uppercase'
            }}
          >
            {card.label}
          </span>
        </div>

        {content.loading ? <ShimmerLines /> : <MiniCardBody cardId={card.id} content={content} />}

        <div style={{ marginTop: 8, fontSize: 11, color: 'rgba(255,255,255,0.46)', textAlign: 'right' }}>tap to expand ↗</div>
      </div>
    </>
  );
};

export default MiniCard;
