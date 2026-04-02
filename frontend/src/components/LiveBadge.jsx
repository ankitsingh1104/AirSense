import React, { useEffect, useState } from 'react';

const LiveBadge = ({ status, lastUpdated }) => {
  const [timeAgo, setTimeAgo] = useState('');

  useEffect(() => {
    const update = () => {
      if (!lastUpdated) return;
      const diff = Math.floor((Date.now() - new Date(lastUpdated).getTime()) / 60000);
      if (diff < 1) {
        setTimeAgo('just now');
      } else if (diff < 60) {
        setTimeAgo(`${diff}m ago`);
      } else {
        setTimeAgo(`${Math.floor(diff / 60)}h ago`);
      }
    };

    update();
    const timer = setInterval(update, 30000);
    return () => clearInterval(timer);
  }, [lastUpdated]);

  const badgeConfig = {
    connected: { color: '#22c55e', bg: 'rgba(34,197,94,0.15)', label: 'CONNECTED' },
    reconnecting: { color: '#eab308', bg: 'rgba(234,179,8,0.15)', label: 'RECONNECTING' },
    disconnected: { color: '#ef4444', bg: 'rgba(239,68,68,0.15)', label: 'OFFLINE' },
    connecting: { color: '#94a3b8', bg: 'rgba(148,163,184,0.1)', label: 'CONNECTING' }
  };

  const cfg = badgeConfig[status] ?? badgeConfig.connecting;

  const dotStyle = {
    width: 8,
    height: 8,
    borderRadius: '50%',
    background: cfg.color,
    animation: status === 'connected' ? 'pulse 2s infinite' : 'none'
  };
  
  return (
    <div
      className="absolute top-6 left-6 z-[100] flex items-center gap-3 backdrop-blur-md px-4 py-2 rounded-full border border-slate-700/50"
      style={{ backgroundColor: cfg.bg }}
    >
      <style>
        {`@keyframes pulse { 0% { opacity: 0.4; } 50% { opacity: 1; } 100% { opacity: 0.4; } }`}
      </style>
      <div style={dotStyle} />
      <div className="flex flex-col">
        <span className="text-[10px] uppercase font-bold tracking-wider" style={{ color: cfg.color }}>
          {cfg.label}
        </span>
        {lastUpdated && (
          <span className="text-[9px] text-slate-500 -mt-0.5">
            updated {timeAgo}
          </span>
        )}
      </div>
    </div>
  );
};

export default LiveBadge;
