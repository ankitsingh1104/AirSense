import React from 'react';

const AQILegend = ({ count = 0 }) => {
  const levels = [
    { label: 'Good', color: '#00e400' },
    { label: 'Moderate', color: '#ffff00' },
    { label: 'Unhealthy for Sensitive', color: '#ff7e00' },
    { label: 'Unhealthy', color: '#ff0000' },
    { label: 'Very Unhealthy', color: '#8f3f97' },
    { label: 'Hazardous', color: '#7e0023' },
  ];

  return (
    <div className="absolute bottom-6 left-6 z-[100] bg-slate-900/40 backdrop-blur-lg border border-slate-700/30 p-4 rounded-3xl shadow-2xl">
      <div className="flex flex-col gap-2">
        <div className="text-[10px] uppercase font-bold text-slate-500 mb-1 tracking-widest">
          AQI Levels
        </div>
        {levels.map((level) => (
          <div key={level.label} className="flex items-center gap-3">
            <div className="w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: level.color }} />
            <span className="text-[11px] font-medium text-slate-300">{level.label}</span>
          </div>
        ))}
        <div className="mt-2 pt-2 border-t border-slate-700/50 text-[10px] text-blue-400 font-bold">
          🌍 {count} COUNTRIES LOADED
        </div>
      </div>
    </div>
  );
};

export default AQILegend;
