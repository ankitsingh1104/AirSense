import React from 'react';
import { ComposedChart, Area, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { getAQIColor } from '../utils/aqiColors';

/**
 * ForecastChart - Display 7-14 day AQI forecast with confidence band
 * Shows forecast line, upper/lower bounds, and model confidence
 */
export default function ForecastChart({ forecast = {}, mode = 'panel' }) {
  const points = forecast.forecast || forecast.forecast_points || [];
  const model_used = forecast.model_used || forecast.model || 'unknown';
  const error = forecast.error || null;
  const isModal = mode === 'modal';
  const safeNum = (value, fallback = 0) => {
    const n = Number(value);
    return Number.isFinite(n) ? n : fallback;
  };

  if (error) {
    return (
      <div className={`bg-red-900/20 border border-red-700 rounded ${isModal ? 'p-4 text-base' : 'p-3 text-sm'} text-red-300`}>
        Forecast unavailable: {error}
      </div>
    );
  }

  if (!points || points.length === 0) {
    return (
      <div className={`bg-slate-800 rounded border border-slate-700 flex items-center justify-center ${isModal ? 'p-6 h-80' : 'p-4 h-60'}`}>
        <div className={`${isModal ? 'text-base' : 'text-sm'} text-slate-400`}>No forecast data available</div>
      </div>
    );
  }

  // Format data for Recharts
  const chartData = points.map(point => ({
    date_label: point.date_label || new Date(point.timestamp || point.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    forecast: safeNum(point.predicted_aqi ?? point.forecast),
    upper: safeNum(point.upper_bound),
    lower: safeNum(point.lower_bound),
    confidence: ((safeNum(point.confidence, 0.8)) * 100).toFixed(0)
  }));

  // Model labels
  const modelLabel = {
    'prophet': '📈 Prophet',
    'lstm': '🧠 LSTM',
    'moving_average': '📊 Moving Avg'
  }[model_used] || `Model: ${model_used}`;

  return (
    <div className={isModal ? 'space-y-4' : 'space-y-3'}>
      {/* Header */}
      <div className="flex justify-between items-center">
        <h3 className={`${isModal ? 'text-xl' : 'text-base'} font-semibold text-slate-200`}>14-Day Forecast</h3>
        <div className={`${isModal ? 'text-sm' : 'text-xs'} text-slate-400`}>{modelLabel}</div>
      </div>

      {/* Chart */}
      <div className={`bg-slate-800 rounded border border-slate-700 ${isModal ? 'p-6' : 'p-4'}`}>
        <ResponsiveContainer width="100%" height={isModal ? 430 : 280}>
          <ComposedChart data={chartData} margin={{ top: 10, right: 20, left: -20, bottom: 20 }}>
            <defs>
              <linearGradient id="forecastGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.1} />
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
            <XAxis 
              dataKey="date_label" 
              stroke="#94a3b8"
              tick={{ fill:'#64748b', fontSize: isModal ? 13 : 10 }}
              interval={1}
            />
            <YAxis 
              stroke="#94a3b8"
              fontSize={isModal ? 14 : 12}
              domain={[0, 'dataMax + 20']}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#1e293b',
                border: '1px solid #475569',
                borderRadius: '6px',
                padding: '8px'
              }}
              labelStyle={{ color: '#e2e8f0' }}
              formatter={(value, name) => {
                const n = safeNum(value);
                if (name === 'forecast') return [n.toFixed(1), 'Forecast'];
                if (name === 'upper') return [n.toFixed(1), 'Upper Bound'];
                if (name === 'lower') return [n.toFixed(1), 'Lower Bound'];
                return [value, name];
              }}
            />
            
            {/* Confidence band */}
            <Area
              type="monotone"
              dataKey="upper"
              fill="#3b82f6"
              stroke="none"
              fillOpacity={0.1}
              name="Confidence Band"
            />
            <Area
              type="monotone"
              dataKey="lower"
              fill="#3b82f6"
              stroke="none"
              fillOpacity={0}
              name="Confidence Band"
            />

            {/* Forecast line */}
            <Line
              type="monotone"
              dataKey="forecast"
              stroke="#3b82f6"
              strokeWidth={isModal ? 3 : 2.5}
              dot={{ fill: '#3b82f6', r: isModal ? 4 : 3 }}
              activeDot={{ r: isModal ? 7 : 5 }}
              name="Forecast"
            />

            <Legend wrapperStyle={{ paddingTop: isModal ? '16px' : '12px', fontSize: isModal ? 13 : 12 }} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* Stats Footer */}
      <div className={`grid grid-cols-3 ${isModal ? 'gap-3 text-sm' : 'gap-2 text-xs'}`}>
        <div className={`bg-slate-800 rounded border border-slate-700 ${isModal ? 'p-4' : 'p-2'}`}>
          <div className={`${isModal ? 'mb-2' : 'mb-1'} text-slate-400`}>Days Forecast</div>
          <div className="text-slate-200 font-semibold">{points.length}</div>
        </div>
        <div className={`bg-slate-800 rounded border border-slate-700 ${isModal ? 'p-4' : 'p-2'}`}>
          <div className={`${isModal ? 'mb-2' : 'mb-1'} text-slate-400`}>Avg Confidence</div>
          <div className="text-slate-200 font-semibold">
            {(points.reduce((a, p) => a + (p.confidence ?? 0.8), 0) / points.length * 100).toFixed(0)}%
          </div>
        </div>
        <div className={`bg-slate-800 rounded border border-slate-700 ${isModal ? 'p-4' : 'p-2'}`}>
          <div className={`${isModal ? 'mb-2' : 'mb-1'} text-slate-400`}>Day 14 Forecast</div>
          <div className="font-semibold" style={{ color: getAQIColor((points[points.length - 1]?.predicted_aqi ?? points[points.length - 1]?.forecast) || 0) }}>
            {((points[points.length - 1]?.predicted_aqi ?? points[points.length - 1]?.forecast)?.toFixed(0)) || 'N/A'}
          </div>
        </div>
      </div>
    </div>
  );
}
