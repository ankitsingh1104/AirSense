import { useEffect, useMemo, useState } from 'react';
import {
  LineChart, Line, ReferenceLine, ResponsiveContainer
} from 'recharts';
import { getAQIColor } from '../utils/aqiColors';
import HealthImpactCard from './HealthImpactCard';
import ForecastChart from './ForecastChart';
import FullAQIView from './FullAQIView';
import PollutantChart from './PollutantChart';
import SHAPChart from './SHAPChart';

const getFlagEmoji = (countryCode) => {
  if (!countryCode) return '🌍';
  return countryCode
    .toUpperCase()
    .split('')
    .map((char) => String.fromCodePoint(127397 + char.charCodeAt(0)))
    .join('');
};

const formatTime = (isoString) => {
  if (!isoString) return 'Unknown';
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) return 'Unknown';
  const diff = Math.floor((Date.now() - date.getTime()) / 60000);
  if (diff < 1) return 'Just now';
  if (diff < 60) return `${diff} min ago`;
  return `${Math.floor(diff / 60)}h ago`;
};

const Skeleton = ({ width = '100%', height = 20, style = {} }) => (
  <div
    style={{
      width,
      height,
      background: 'linear-gradient(90deg, #1e293b 25%, #334155 50%, #1e293b 75%)',
      backgroundSize: '200% 100%',
      animation: 'shimmer 1.5s infinite',
      borderRadius: 6,
      ...style
    }}
  />
);

const safeNum = (value, fallback = 0) => {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
};

const CountryPanel = ({ countryCode, countryName, initialAqi, onClose }) => {
  const [data, setData] = useState(null);
  const [history, setHistory] = useState([]);
  const [forecast, setForecast] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [reloadTick, setReloadTick] = useState(0);

  console.log('CountryPanel received data:', JSON.stringify(data, null, 2));

  useEffect(() => {
    if (!countryCode) return;

    let cancelled = false;
    setLoading(true);
    setData(null);
    setError(null);

    Promise.all([
      fetch(`/api/realtime/${countryCode}`).then((r) => {
        if (!r.ok) throw new Error(`Realtime fetch failed: ${r.status}`);
        return r.json();
      }),
      fetch(`/api/history/${countryCode}?days=7`).then((r) => {
        if (!r.ok) return [];
        return r.json();
      }),
      fetch(`/api/forecast/${countryCode}?days=14`).then((r) => {
        if (!r.ok) return { error: 'Unavailable', forecast_points: [] };
        return r.json();
      })
    ])
      .then(([realtimeData, historyData, forecastData]) => {
        if (cancelled) return;
        setData(realtimeData);
        setHistory(Array.isArray(historyData) ? historyData : []);
        setForecast(forecastData || {});
      })
      .catch((err) => {
        if (cancelled) return;
        console.error('CountryPanel fetch error:', err);
        setError(err.message || 'Unknown error');
      })
      .finally(() => {
        if (cancelled) return;
        setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [countryCode, reloadTick]);

  const liveAqi = safeNum(data?.live_aqi, safeNum(initialAqi, 0));
  const predictedAqi = safeNum(data?.predicted_aqi, liveAqi);

  const delta = predictedAqi - liveAqi;

  return (
    <div className="fixed right-0 top-0 h-screen w-[400px] bg-slate-900/95 text-white shadow-2xl border-l border-slate-700 overflow-y-auto z-50 p-5">
      <style>
        {`@keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }`}
      </style>

      <div className="flex items-start justify-between mb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xl">{getFlagEmoji(countryCode)}</span>
            <h2 style={{ fontSize: 22, lineHeight: '28px', fontWeight: 700 }}>
              {countryName || data?.country_name || 'Unknown'}
            </h2>
          </div>
          <div className="mt-2">
            {loading ? (
              <Skeleton width={170} height={26} />
            ) : (
              <span
                className="inline-block px-3 py-1 rounded-full text-slate-900 font-semibold text-sm"
                style={{ backgroundColor: getAQIColor(liveAqi) }}
              >
                {`${liveAqi.toFixed(1)} - ${data?.aqi_category || 'Unknown'}`}
              </span>
            )}
          </div>
          <p className="text-slate-400 text-xs mt-2">
            Last updated: {loading ? 'Loading...' : formatTime(data?.fetched_at)}
          </p>
        </div>

        <button onClick={onClose} className="text-slate-400 hover:text-white text-2xl leading-none">×</button>
      </div>

      {error && !loading ? (
        <div style={{ padding: '20px', textAlign: 'center' }}>
          <div style={{ fontSize: 32, marginBottom: 8 }}>⚠️</div>
          <div style={{ color: '#f87171', marginBottom: 8 }}>Failed to load data</div>
          <div style={{ color: '#94a3b8', fontSize: 12, marginBottom: 16 }}>{error}</div>
          <button
            onClick={() => {
              setLoading(true);
              setError(null);
              setReloadTick((v) => v + 1);
            }}
            style={{
              background: '#3b82f6',
              color: 'white',
              border: 'none',
              padding: '8px 16px',
              borderRadius: 8,
              cursor: 'pointer'
            }}
          >
            Retry
          </button>
        </div>
      ) : (
        <>
          {loading ? <Skeleton width="100%" height={130} style={{ marginBottom: 16 }} /> : <FullAQIView realtime={data} />}

          {/* Health Impact Card */}
          <div style={{ borderTop: '1px solid #1e293b', paddingTop: 12, marginBottom: 16 }}>
            <div style={{ color: '#94a3b8', fontSize: 12, fontWeight: 500, marginBottom: 8 }}>
              Health guidance for this AQI level
            </div>
            {loading ? (
              <Skeleton width="100%" height={200} />
            ) : (
              <HealthImpactCard aqi={data?.live_aqi ?? liveAqi} />
            )}
          </div>

          {loading ? <Skeleton width="100%" height={180} style={{ marginBottom: 16 }} /> : <PollutantChart realtime={data} />}

          {loading ? <Skeleton width="100%" height={220} style={{ marginBottom: 16 }} /> : <SHAPChart shapValues={data?.shap_values} />}

          <div className="bg-slate-800/50 p-4 rounded-xl border border-slate-700 mb-4">
            <h3 className="text-sm font-semibold text-slate-300 mb-2">7-day trend</h3>
            {loading ? (
              <Skeleton width="100%" height={160} />
            ) : history.length > 0 ? (
              <ResponsiveContainer width="100%" height={160}>
                <LineChart data={history} margin={{ left: 10, right: 20, top: 10, bottom: 10 }}>
                  <XAxis
                    dataKey="timestamp"
                    tickFormatter={(t) => {
                      const d = new Date(t);
                      return Number.isNaN(d.getTime())
                        ? t
                        : d.toLocaleDateString('en', { weekday: 'short' });
                    }}
                    tick={{ fill: '#94a3b8', fontSize: 11 }}
                  />
                  <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} />
                  <Tooltip
                    labelFormatter={(t) => {
                      const d = new Date(t);
                      return Number.isNaN(d.getTime()) ? String(t) : d.toLocaleDateString();
                    }}
                    formatter={(v) => [Number(v)?.toFixed(1), 'AQI']}
                    contentStyle={{ background: '#1e293b', border: 'none', borderRadius: 8 }}
                  />
                  <ReferenceLine
                    y={100}
                    stroke="#fb923c"
                    strokeDasharray="4 4"
                    label={{ value: 'Unhealthy', fill: '#fb923c', fontSize: 10 }}
                  />
                  <Line
                    type="monotone"
                    dataKey="aqi_value"
                    stroke="#818cf8"
                    strokeWidth={2}
                    dot={{ r: 3, fill: '#818cf8' }}
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-slate-400 text-sm">Historical data not yet available for this country.</p>
            )}
          </div>

          <div className="bg-slate-800/50 p-4 rounded-xl border border-slate-700 mb-4">
            <h3 className="text-sm font-semibold text-slate-300 mb-2">14-day Forecast</h3>
            {loading ? (
              <Skeleton width="100%" height={300} />
            ) : (
              <ForecastChart forecast={forecast} />
            )}
          </div>
        </>
      )}
    </div>
  );
};

export default CountryPanel;
