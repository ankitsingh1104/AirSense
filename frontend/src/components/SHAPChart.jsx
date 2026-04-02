import { useMemo } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, Cell, LabelList, ReferenceLine, ResponsiveContainer } from 'recharts';

const safeNum = (value, fallback = 0) => {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
};

const SHAPChart = ({ shapValues = [], mode = 'panel' }) => {
  const isModal = mode === 'modal';
  const shapData = useMemo(() => {
    const raw = Array.isArray(shapValues) ? shapValues : [];
    return [...raw]
      .map((item) => ({ feature: item?.feature || 'Unknown', contribution: safeNum(item?.contribution) }))
      .sort((a, b) => Math.abs(b.contribution) - Math.abs(a.contribution))
      .slice(0, 5);
  }, [shapValues]);

  return (
    <div className={`bg-slate-800/50 rounded-xl border border-slate-700 mb-4 ${isModal ? 'p-6' : 'p-4'}`}>
      <h3 className={`${isModal ? 'text-lg' : 'text-sm'} font-semibold text-slate-200`}>Why this prediction?</h3>
      <p className={`${isModal ? 'text-sm mb-3' : 'text-xs mb-2'} text-slate-400`}>Feature contributions to the ML model output</p>

      <ResponsiveContainer width="100%" height={isModal ? 340 : 220}>
        <BarChart layout="vertical" data={shapData} margin={{ left: isModal ? 170 : 110, right: isModal ? 84 : 60, top: 10, bottom: 10 }}>
          <XAxis type="number" tick={{ fill: '#94a3b8', fontSize: isModal ? 13 : 11 }} tickFormatter={(v) => (v > 0 ? `+${v}` : `${v}`)} />
          <YAxis type="category" dataKey="feature" width={isModal ? 160 : 105} tick={{ fill: '#e2e8f0', fontSize: isModal ? 13 : 11 }} />
          <ReferenceLine x={0} stroke="#475569" strokeWidth={1} />
          <Tooltip
            formatter={(value) => [`${value > 0 ? '+' : ''}${Number(value).toFixed(2)}`, 'SHAP contribution']}
            contentStyle={{ background: '#1e293b', border: 'none', borderRadius: 8 }}
          />
          <Bar dataKey="contribution" radius={4}>
            {shapData.map((entry, index) => (
              <Cell key={index} fill={entry.contribution > 0 ? '#f87171' : '#2dd4bf'} />
            ))}
            <LabelList dataKey="contribution" position="right" style={{ fill: '#cbd5e1', fontSize: isModal ? 12 : 10 }} formatter={(v) => `${v > 0 ? '+' : ''}${Number(v).toFixed(1)}`} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      <div className={`${isModal ? 'text-sm mt-3' : 'text-xs mt-2'} text-slate-400`}>■ Red = pushes AQI higher    ■ Teal = pushes AQI lower</div>
    </div>
  );
};

export default SHAPChart;
