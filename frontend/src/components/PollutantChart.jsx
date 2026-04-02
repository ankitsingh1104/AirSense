import { useMemo } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, Cell, LabelList, ResponsiveContainer } from 'recharts';

const safeNum = (value, fallback = 0) => {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
};

const PollutantChart = ({ realtime, mode = 'panel' }) => {
  const isModal = mode === 'modal';
  const pollutantChartData = useMemo(() => {
    const pollutants = realtime?.pollutants || {};
    return [
      { name: 'PM2.5', value: safeNum(pollutants?.pm25?.aqi_value), fill: '#f87171', category: pollutants?.pm25?.aqi_category || 'Unknown' },
      { name: 'Ozone', value: safeNum(pollutants?.ozone?.aqi_value), fill: '#38bdf8', category: pollutants?.ozone?.aqi_category || 'Unknown' },
      { name: 'NO2', value: safeNum(pollutants?.no2?.aqi_value), fill: '#fb923c', category: pollutants?.no2?.aqi_category || 'Unknown' },
      { name: 'CO', value: safeNum(pollutants?.co?.aqi_value), fill: '#94a3b8', category: pollutants?.co?.aqi_category || 'Unknown' }
    ];
  }, [realtime]);

  const dominant = pollutantChartData.reduce(
    (a, b) => (a.value > b.value ? a : b),
    pollutantChartData[0] || { name: 'Unknown', fill: '#94a3b8' }
  );

  return (
    <div className={`bg-slate-800/50 rounded-xl border border-slate-700 mb-4 ${isModal ? 'p-6' : 'p-4'}`}>
      <div className="flex items-center justify-between mb-3">
        <h3 className={`${isModal ? 'text-lg' : 'text-sm'} font-semibold text-slate-200 uppercase`}>Pollutants</h3>
        <span className={`${isModal ? 'text-sm px-3 py-1.5' : 'text-xs px-2 py-1'} rounded-full font-semibold`} style={{ color: dominant.fill, border: `1px solid ${dominant.fill}55` }}>
          {`⚠ Dominant: ${dominant.name}`}
        </span>
      </div>

      <ResponsiveContainer width="100%" height={isModal ? 300 : 180}>
        <BarChart layout="vertical" data={pollutantChartData} margin={{ left: isModal ? 84 : 50, right: isModal ? 84 : 60, top: 10, bottom: 10 }}>
          <XAxis type="number" domain={[0, 300]} tick={{ fill: '#94a3b8', fontSize: isModal ? 13 : 11 }} />
          <YAxis type="category" dataKey="name" tick={{ fill: '#e2e8f0', fontSize: isModal ? 14 : 12 }} width={isModal ? 70 : 45} />
          <Tooltip
            formatter={(value, name, props) => [`${value} (${props.payload.category})`, name]}
            contentStyle={{ background: '#1e293b', border: 'none', borderRadius: 8 }}
          />
          <Bar dataKey="value" radius={[0, 4, 4, 0]}>
            {pollutantChartData.map((entry, index) => (
              <Cell key={index} fill={entry.fill} />
            ))}
            <LabelList dataKey="value" position="right" style={{ fill: '#cbd5e1', fontSize: isModal ? 13 : 11 }} formatter={(v) => (v > 0 ? v.toFixed(0) : '')} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};

export default PollutantChart;
