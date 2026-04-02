import React, { useState, useEffect } from 'react';
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { getAQIColor } from '../utils/aqiColors';
import { apiUrl } from '../config/endpoints';

/**
 * ComparisonPanel - Side-by-side AQI comparison of two countries
 * Displays: badges, key metrics, pollutant comparison, SHAP importance comparison
 */
export default function ComparisonPanel({ 
  country1 = null,  // { code, name, aqi }
  country2 = null,  // { code, name, aqi }
  onClose = () => {} 
}) {
  const [data1, setData1] = useState(null);
  const [data2, setData2] = useState(null);
  const [loading1, setLoading1] = useState(false);
  const [loading2, setLoading2] = useState(false);
  const [error1, setError1] = useState(null);
  const [error2, setError2] = useState(null);

  // Fetch data for both countries
  useEffect(() => {
    if (!country1 || !country1.code) return;

    const fetchData = async (code, setData, setLoading, setError) => {
      setLoading(true);
      setError(null);
      setData(null);
      try {
        const [realRes, histRes] = await Promise.all([
          fetch(apiUrl(`/api/realtime/${code}`)),
          fetch(apiUrl(`/api/history/${code}?days=7`))
        ]);

        if (!realRes.ok || !histRes.ok) {
          throw new Error(`API error: ${realRes.status || histRes.status}`);
        }

        const realData = await realRes.json();
        const histData = await histRes.json();

        setData({ realtime: realData, history: histData.history || [] });
      } catch (err) {
        console.error('Comparison data fetch error:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchData(country1.code, setData1, setLoading1, setError1);
    if (country2 && country2.code) {
      fetchData(country2.code, setData2, setLoading2, setError2);
    }
  }, [country1, country2]);

  const getWinner = (val1, val2, lowerIsBetter = true) => {
    if (val1 === undefined || val2 === undefined) return null;
    return lowerIsBetter ? (val1 < val2 ? '1' : val1 > val2 ? '2' : 'tie') 
                          : (val1 > val2 ? '1' : val1 < val2 ? '2' : 'tie');
  };

  const renderWinnerBadge = (winner) => {
    if (winner === 'tie') return <span className="text-xs text-slate-400">Tie</span>;
    if (winner === '1') return <span className="text-xs text-green-400">✓</span>;
    if (winner === '2') return <span className="text-xs text-green-400">✓</span>;
  };

  const pollutantComparisonData = data1 && data2 ? Object.keys(data1.realtime.pollutants || {})
    .filter(key => data2.realtime.pollutants?.[key])
    .map(key => ({
      name: key.toUpperCase(),
      [country1.name]: data1.realtime.pollutants[key].aqi_value,
      [country2.name]: data2.realtime.pollutants[key].aqi_value
    })) : [];

  const shapeComparisonData = data1 && data2 
    ? (data1.realtime.shap_values || [])
        .filter((_, i) => (data2.realtime.shap_values || [])[i])
        .slice(0, 5)
        .map((v, i) => ({
          name: `Feature ${i + 1}`,
          [country1.name]: Math.abs(v.contribution || 0),
          [country2.name]: Math.abs((data2.realtime.shap_values[i]?.contribution || 0))
        }))
    : [];

  const countryAqiWinner = getWinner(
    data1?.realtime.live_aqi, 
    data2?.realtime.live_aqi, 
    true
  );

  const aqi1Won = countryAqiWinner === '1';
  const aqi2Won = countryAqiWinner === '2';

  return (
    <div className="fixed bottom-0 right-0 top-0 bg-slate-900/95 border-l border-slate-700 w-full md:w-[900px] overflow-y-auto z-40 text-slate-100">
      {/* Header */}
      <div className="sticky top-0 bg-slate-900 border-b border-slate-700 p-4 flex justify-between items-center">
        <h2 className="text-lg font-bold text-white">AQI Comparison</h2>
        <button
          onClick={onClose}
          className="px-3 py-1 bg-slate-700 hover:bg-slate-600 rounded text-sm font-medium transition"
        >
          ✕ Close
        </button>
      </div>

      <div className="p-6 space-y-6">
        {/* AQI Badge Comparison */}
        <div className="grid grid-cols-2 gap-4">
          {/* Country 1 */}
          <div className="space-y-3">
            <h3 className="font-semibold text-slate-300">{country1?.name}</h3>
            {loading1 ? (
              <div className="bg-slate-800 h-16 rounded animate-pulse" />
            ) : error1 ? (
              <div className="bg-red-900/20 border border-red-700 rounded p-3 text-red-300 text-sm">
                {error1}
              </div>
            ) : data1 ? (
              <div className="space-y-2">
                <div className="p-3 rounded bg-slate-800 border border-slate-700">
                  <div className="flex items-baseline gap-2">
                    <span className="text-3xl font-bold" style={{ color: getAQIColor(data1.realtime.live_aqi) }}>
                      {Math.round(data1.realtime.live_aqi)}
                    </span>
                    <span className="text-xs text-slate-400">AQI Live</span>
                  </div>
                  <div className="text-xs text-slate-400 mt-1">
                    {data1.realtime.aqi_category || 'Unknown'}
                  </div>
                </div>
                <div className="text-sm text-slate-400">
                  Predicted: <span className="text-slate-200 font-medium">{Math.round(data1.realtime.predicted_aqi || 0)}</span>
                </div>
              </div>
            ) : null}
          </div>

          {/* Country 2 */}
          <div className="space-y-3">
            <h3 className="font-semibold text-slate-300">{country2?.name}</h3>
            {loading2 ? (
              <div className="bg-slate-800 h-16 rounded animate-pulse" />
            ) : error2 ? (
              <div className="bg-red-900/20 border border-red-700 rounded p-3 text-red-300 text-sm">
                {error2}
              </div>
            ) : data2 ? (
              <div className="space-y-2">
                <div className="p-3 rounded bg-slate-800 border border-slate-700">
                  <div className="flex items-baseline gap-2">
                    <span className="text-3xl font-bold" style={{ color: getAQIColor(data2.realtime.live_aqi) }}>
                      {Math.round(data2.realtime.live_aqi)}
                    </span>
                    <span className="text-xs text-slate-400">AQI Live</span>
                  </div>
                  <div className="text-xs text-slate-400 mt-1">
                    {data2.realtime.aqi_category || 'Unknown'}
                  </div>
                </div>
                <div className="text-sm text-slate-400">
                  Predicted: <span className="text-slate-200 font-medium">{Math.round(data2.realtime.predicted_aqi || 0)}</span>
                </div>
              </div>
            ) : null}
          </div>
        </div>

        {/* Winner Announcement */}
        {data1 && data2 && (
          <div className="p-4 rounded bg-slate-800 border border-slate-700">
            <div className="text-sm text-slate-400 mb-2">
              Better Air Quality:
            </div>
            <div className="flex items-center justify-between">
              <span className={aqi1Won ? 'text-green-400 font-semibold' : 'text-slate-400'}>
                {country1?.name}
              </span>
              <span className="text-slate-500">
                {aqi1Won ? '✓ Better' : aqi2Won ? 'vs.' : 'Equal'}
              </span>
              <span className={aqi2Won ? 'text-green-400 font-semibold' : 'text-slate-400'}>
                {country2?.name}
              </span>
            </div>
            <div className="text-xs text-slate-500 mt-2">
              Difference: <span className="text-slate-300 font-medium">{Math.abs(data1.realtime.live_aqi - data2.realtime.live_aqi).toFixed(1)} AQI points</span>
            </div>
          </div>
        )}

        {/* Pollutant Comparison Chart */}
        {pollutantComparisonData.length > 0 && (
          <div className="space-y-2">
            <h3 className="font-semibold text-slate-300">Pollutant Levels</h3>
            <div className="bg-slate-800 rounded p-4 border border-slate-700">
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={pollutantComparisonData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="name" stroke="#94a3b8" />
                  <YAxis stroke="#94a3b8" />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569' }}
                    labelStyle={{ color: '#e2e8f0' }}
                  />
                  <Legend wrapperStyle={{ paddingTop: 12 }} />
                  <Bar dataKey={country1?.name} fill="#3b82f6" />
                  <Bar dataKey={country2?.name} fill="#8b5cf6" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* SHAP Importance Comparison */}
        {shapeComparisonData.length > 0 && (
          <div className="space-y-2">
            <h3 className="font-semibold text-slate-300">Feature Importance (SHAP)</h3>
            <div className="bg-slate-800 rounded p-4 border border-slate-700">
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={shapeComparisonData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="name" stroke="#94a3b8" />
                  <YAxis stroke="#94a3b8" />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569' }}
                    labelStyle={{ color: '#e2e8f0' }}
                  />
                  <Legend wrapperStyle={{ paddingTop: 12 }} />
                  <Bar dataKey={country1?.name} fill="#3b82f6" />
                  <Bar dataKey={country2?.name} fill="#8b5cf6" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* Quick Stats */}
        {data1 && data2 && (
          <div className="space-y-2">
            <h3 className="font-semibold text-slate-300">Quick Stats</h3>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div className="bg-slate-800 rounded p-3 border border-slate-700">
                <div className="text-slate-400 mb-1">Dominant Pollutant</div>
                <div className="font-medium text-blue-300">
                  {data1.realtime.dominant_pollutant?.toUpperCase() || 'N/A'}
                </div>
              </div>
              <div className="bg-slate-800 rounded p-3 border border-slate-700">
                <div className="text-slate-400 mb-1">Dominant Pollutant</div>
                <div className="font-medium text-purple-300">
                  {data2.realtime.dominant_pollutant?.toUpperCase() || 'N/A'}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Info */}
        <div className="text-xs text-slate-500 p-3 bg-slate-800 rounded border border-slate-700">
          💡 <strong>Tip:</strong> Click another country on the globe to compare with a different region. All values are live and update in real-time.
        </div>
      </div>
    </div>
  );
}
