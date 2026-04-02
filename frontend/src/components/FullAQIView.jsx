import { getAQIColor } from '../utils/aqiColors';

const safeNum = (value, fallback = 0) => {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
};

const FullAQIView = ({ realtime, mode = 'panel' }) => {
  const isModal = mode === 'modal';
  const liveAqi = safeNum(realtime?.live_aqi, 0);
  const predictedAqi = safeNum(realtime?.predicted_aqi, liveAqi);
  const delta = predictedAqi - liveAqi;
  const deltaColor = delta > 5 ? '#ef4444' : delta < -5 ? '#22c55e' : '#94a3b8';

  return (
    <div className={`grid grid-cols-[1fr_auto_1fr] items-center ${isModal ? 'gap-4 mb-4' : 'gap-2 mb-2'}`}>
      <div className={`bg-slate-800 rounded-xl border border-slate-700 ${isModal ? 'p-6 min-h-[200px]' : 'p-4 min-h-[140px]'}`}>
        <p className={`${isModal ? 'text-sm' : 'text-xs'} text-slate-400 uppercase font-semibold`}>Live AQI</p>
        <p style={{ color: getAQIColor(liveAqi), fontSize: isModal ? 72 : 44, fontWeight: 800, lineHeight: isModal ? '74px' : '46px' }}>{liveAqi.toFixed(1)}</p>
        <p className={`${isModal ? 'text-sm mt-2' : 'text-xs mt-1'} text-slate-300`}>{realtime?.aqi_category || 'Unknown'}</p>
      </div>

      <div className={`${isModal ? 'text-xl' : 'text-sm'} font-semibold`} style={{ color: deltaColor }}>
        {`${delta > 0 ? '▲' : '▼'} ${Math.abs(delta).toFixed(1)}`}
      </div>

      <div className={`bg-slate-800 rounded-xl border border-slate-700 ${isModal ? 'p-6 min-h-[200px]' : 'p-4 min-h-[140px]'}`}>
        <p className={`${isModal ? 'text-sm' : 'text-xs'} text-slate-400 uppercase font-semibold`}>ML Predicted</p>
        <p style={{ color: getAQIColor(predictedAqi), fontSize: isModal ? 72 : 44, fontWeight: 800, lineHeight: isModal ? '74px' : '46px' }}>{predictedAqi.toFixed(1)}</p>
        <p className={`${isModal ? 'text-sm mt-2' : 'text-xs mt-1'} text-slate-300`}>
          {`RF: ${safeNum(realtime?.rf_prediction).toFixed(1)} / XGB: ${safeNum(realtime?.xgb_prediction).toFixed(1)}`}
        </p>
      </div>
    </div>
  );
};

export default FullAQIView;
