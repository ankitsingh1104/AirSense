import { useEffect, useMemo, useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { getAQIColor } from '../utils/aqiColors';

const POLLUTANT_SLIDERS = [
  { key: 'pm2.5', label: 'PM2.5' },
  { key: 'no2', label: 'NO2' },
  { key: 'co', label: 'CO' }
];

const clamp = (v, min, max) => Math.max(min, Math.min(max, v));

const SimulatorCard = ({ realtime, selectedCountry, simulatedAqi, onSimulatedAqiChange, onSimulationReset }) => {
  const [mods, setMods] = useState({ 'pm2.5': 0, no2: 0, co: 0 });
  const [localSimAqi, setLocalSimAqi] = useState(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');

  const pollutantValues = useMemo(() => ({
    'pm2.5': Number(realtime?.pollutants?.pm25?.aqi_value ?? 0),
    no2: Number(realtime?.pollutants?.no2?.aqi_value ?? 0),
    co: Number(realtime?.pollutants?.co?.aqi_value ?? 0),
    ozone: Number(realtime?.pollutants?.ozone?.aqi_value ?? 0)
  }), [realtime]);

  const liveAqi = Number(realtime?.live_aqi ?? 0);
  const effectiveSimAqi = Number(simulatedAqi ?? localSimAqi ?? liveAqi);
  const delta = Number((effectiveSimAqi - liveAqi).toFixed(1));

  useEffect(() => {
    // Reset sliders when selected country changes.
    setMods({ 'pm2.5': 0, no2: 0, co: 0 });
    setLocalSimAqi(null);
    setError('');
  }, [selectedCountry?.code]);

  useEffect(() => {
    const hasChange = Object.values(mods).some((v) => Math.abs(v) > 0.0001);
    if (!hasChange) {
      setLocalSimAqi(null);
      onSimulationReset?.();
      return;
    }

    const t = setTimeout(async () => {
      setPending(true);
      setError('');
      try {
        const payload = {
          country_name: realtime?.country_name || selectedCountry?.name || 'Unknown',
          pollutant_values: pollutantValues,
          modification_map: mods
        };

        const res = await fetch('/api/simulate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        if (!res.ok) throw new Error(`Simulation failed: ${res.status}`);
        const sim = await res.json();
        setLocalSimAqi(Number(sim.simulated_aqi));
        onSimulatedAqiChange?.(Number(sim.simulated_aqi));
      } catch (e) {
        setError(e.message || 'Simulation unavailable');
      } finally {
        setPending(false);
      }
    }, 300);

    return () => clearTimeout(t);
  }, [mods, pollutantValues, realtime?.country_name, selectedCountry?.name, onSimulatedAqiChange, onSimulationReset]);

  const chartData = [
    { name: 'Live', value: liveAqi, color: '#94a3b8' },
    { name: 'Sim', value: effectiveSimAqi, color: getAQIColor(effectiveSimAqi) },
    { name: 'Delta', value: Math.abs(delta), color: delta <= 0 ? '#22c55e' : '#ef4444' }
  ];

  return (
    <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-slate-100">What-If Simulator</h3>
        <button
          className="text-sm px-3 py-1 rounded border border-slate-600 text-slate-300 hover:bg-slate-700"
          onClick={() => {
            setMods({ 'pm2.5': 0, no2: 0, co: 0 });
            setLocalSimAqi(null);
            onSimulationReset?.();
          }}
        >
          Reset
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-5">
        {POLLUTANT_SLIDERS.map((slider) => {
          const pct = Math.round((mods[slider.key] || 0) * 100);
          return (
            <div key={slider.key} className="rounded-lg border border-slate-700 p-3 bg-slate-900/40">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-slate-300 font-medium">{slider.label}</span>
                <span className={`text-sm font-semibold ${pct < 0 ? 'text-green-400' : pct > 0 ? 'text-red-400' : 'text-slate-400'}`}>
                  {pct > 0 ? '+' : ''}{pct}%
                </span>
              </div>
              <input
                type="range"
                min={-50}
                max={50}
                step={1}
                value={pct}
                onChange={(e) => {
                  const next = clamp(Number(e.target.value), -50, 50) / 100;
                  setMods((prev) => ({ ...prev, [slider.key]: next }));
                }}
                className="w-full accent-blue-500"
              />
            </div>
          );
        })}
      </div>

      <div className="rounded-lg border border-slate-700 p-4 bg-slate-900/40">
        <div className="flex items-center justify-between mb-2">
          <div className="text-sm text-slate-300">AQI Impact</div>
          <div className={`text-sm font-semibold ${delta <= 0 ? 'text-green-400' : 'text-red-400'}`}>
            {pending ? 'Simulating...' : `${delta > 0 ? '+' : ''}${delta} AQI`}
          </div>
        </div>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={chartData}>
            <XAxis dataKey="name" tick={{ fill: '#cbd5e1', fontSize: 12 }} />
            <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} />
            <Tooltip
              contentStyle={{ background: '#1e293b', border: '1px solid #475569' }}
              formatter={(v) => [Number(v).toFixed(1), 'AQI']}
            />
            <Bar dataKey="value" radius={[6, 6, 0, 0]}>
              {chartData.map((d, i) => (
                <Cell key={i} fill={d.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {error && <div className="text-sm text-red-400 mt-3">{error}</div>}
    </div>
  );
};

export default SimulatorCard;
