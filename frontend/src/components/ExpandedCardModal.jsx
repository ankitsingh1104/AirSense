import FullAQIView from './FullAQIView';
import PollutantChart from './PollutantChart';
import HealthImpactCard from './HealthImpactCard';
import ForecastChart from './ForecastChart';
import SHAPChart from './SHAPChart';
import SimulatorCard from './SimulatorCard';

const CARD_LABELS = {
  aqi: 'Air Quality Index',
  pollutants: 'Pollutant Breakdown',
  health: 'Health Impact',
  forecast: '14-Day Forecast',
  shap: 'Prediction Explanation',
  simulate: 'Sensitivity Simulator'
};

const getFlagEmoji = (countryCode) => {
  if (!countryCode) return '🌍';
  return countryCode
    .toUpperCase()
    .split('')
    .map((char) => String.fromCodePoint(127397 + char.charCodeAt(0)))
    .join('');
};

const ModalCardContent = ({ cardId, realtime, forecast, selectedCountry, simulatedAqi, onSimulatedAqiChange, onSimulationReset }) => {
  switch (cardId) {
    case 'aqi':
      return <FullAQIView realtime={realtime} mode="modal" />;
    case 'pollutants':
      return <PollutantChart realtime={realtime} mode="modal" />;
    case 'health':
      return <HealthImpactCard aqi={realtime?.live_aqi} mode="modal" />;
    case 'forecast':
      return <ForecastChart forecast={forecast} mode="modal" />;
    case 'shap':
      return <SHAPChart shapValues={realtime?.shap_values} mode="modal" />;
    case 'simulate':
      return (
        <SimulatorCard
          realtime={realtime}
          selectedCountry={selectedCountry}
          simulatedAqi={simulatedAqi}
          onSimulatedAqiChange={onSimulatedAqiChange}
          onSimulationReset={onSimulationReset}
        />
      );
    default:
      return null;
  }
};

const ExpandedCardModal = ({ cardId, countryData, selectedCountry, simulatedAqi, onSimulatedAqiChange, onSimulationReset, onClose }) => {
  const realtime = countryData?.realtime;
  const forecast = countryData?.forecast;
  const isForecast = cardId === 'forecast';
  const isSimulator = cardId === 'simulate';
  const modalWidth = isForecast || isSimulator ? 'min(1100px, 96vw)' : 'min(860px, 94vw)';

  if (!cardId) return null;

  return (
    <>
      <div
        onClick={onClose}
        style={{
          position: 'fixed',
          inset: 0,
          background: 'rgba(2, 6, 23, 0.35)',
          backdropFilter: 'blur(2px)',
          WebkitBackdropFilter: 'blur(2px)',
          zIndex: 30,
          animation: 'fadeIn 0.2s ease both'
        }}
      />

      <div
        style={{
          position: 'fixed',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%,-50%)',
          width: modalWidth,
          maxHeight: '86vh',
          overflowY: 'auto',
          background: 'linear-gradient(160deg, rgba(12, 20, 38, 0.97), rgba(7, 12, 24, 0.95))',
          backdropFilter: 'blur(26px) saturate(220%)',
          WebkitBackdropFilter: 'blur(26px) saturate(220%)',
          border: '1px solid rgba(255,255,255,0.24)',
          borderRadius: 26,
          boxShadow: '0 26px 90px rgba(0,0,0,0.68), inset 0 1px 0 rgba(255,255,255,0.16), 0 0 28px rgba(59,130,246,0.12)',
          zIndex: 31,
          padding: isForecast || isSimulator ? '34px 38px' : '30px 34px',
          color: 'white',
          animation: 'modalEnter 0.35s cubic-bezier(0.34,1.56,0.64,1) both'
        }}
      >
        <style>{`
          @keyframes fadeIn { from{opacity:0} to{opacity:1} }
          @keyframes modalEnter {
            from { opacity:0; transform:translate(-50%,-50%) scale(0.88); }
            to   { opacity:1; transform:translate(-50%,-50%) scale(1); }
          }
        `}</style>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
          <div>
            <span style={{ fontSize: 26, marginRight: 12 }}>{getFlagEmoji(selectedCountry?.code)}</span>
            <span style={{ fontSize: 24, fontWeight: 700 }}>{selectedCountry?.name}</span>
            <span
              style={{
                marginLeft: 14,
                fontSize: 14,
                color: 'rgba(255,255,255,0.68)',
                textTransform: 'uppercase',
                letterSpacing: '0.08em'
              }}
            >
              {CARD_LABELS[cardId]}
            </span>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'rgba(255,255,255,0.16)',
              border: '1px solid rgba(255,255,255,0.26)',
              borderRadius: 10,
              color: 'white',
              width: 40,
              height: 40,
              fontSize: 22,
              cursor: 'pointer',
              lineHeight: 1,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
          >
            ×
          </button>
        </div>

        <div style={{ minHeight: isForecast || isSimulator ? 500 : 360 }}>
          <ModalCardContent
            cardId={cardId}
            realtime={realtime}
            forecast={forecast}
            selectedCountry={selectedCountry}
            simulatedAqi={simulatedAqi}
            onSimulatedAqiChange={onSimulatedAqiChange}
            onSimulationReset={onSimulationReset}
          />
        </div>
      </div>
    </>
  );
};

export default ExpandedCardModal;
