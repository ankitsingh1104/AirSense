import MiniCard from './MiniCard';
import { getAQIColor } from '../utils/aqiColors';
import { getHealthImpact } from '../utils/healthImpact';

const GlassmorphicCards = ({ cardPositions, countryData, loading, simulatedAqi, onCardClick }) => {
  if (!cardPositions?.length) return null;

  const realtime = countryData?.realtime;
  const forecast = countryData?.forecast;

  const getCardContent = (cardId) => {
    if (loading || !realtime) return { loading: true };

    switch (cardId) {
      case 'aqi':
        return {
          primary: realtime.live_aqi?.toFixed(0),
          primaryColor: getAQIColor(realtime.live_aqi),
          secondary: realtime.aqi_category,
          tertiary: `ML: ${Number(realtime.predicted_aqi ?? 0).toFixed(0)}`
        };
      case 'pollutants':
        return {
          dominant: realtime.dominant_pollutant?.toUpperCase(),
          pm25: realtime.pollutants?.pm25?.aqi_value,
          ozone: realtime.pollutants?.ozone?.aqi_value,
          no2: realtime.pollutants?.no2?.aqi_value,
          co: realtime.pollutants?.co?.aqi_value
        };
      case 'health': {
        const health = getHealthImpact(realtime.live_aqi);
        return {
          risk: health.risk,
          color: health.color,
          advice: health.general
        };
      }
      case 'forecast': {
        const rows = forecast?.forecast || [];
        return {
          sparkData: rows.map((f) => f.predicted_aqi),
          trend: forecast?.trend || 'stable'
        };
      }
      case 'shap':
        return {
          topFeature: realtime.shap_values?.[0],
          modelUsed: 'RF + XGB ensemble'
        };
      case 'simulate': {
        const live = Number(realtime.live_aqi ?? 0);
        const sim = Number(simulatedAqi ?? live);
        return {
          live,
          simulated: sim,
          delta: sim - live
        };
      }
      default:
        return { loading: true };
    }
  };

  return (
    <>
      <svg
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          width: '100vw',
          height: '100vh',
          pointerEvents: 'none',
          zIndex: 9
        }}
      >
        {cardPositions.map((card) => (
          <line
            key={card.id}
            x1={card.x + (card.w || 220) / 2}
            y1={card.y + (card.h || 132) / 2}
            x2={card.lineX}
            y2={card.lineY}
            stroke="rgba(255,255,255,0.12)"
            strokeWidth="1"
            strokeDasharray="4 4"
          />
        ))}
      </svg>

      <div
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          width: '100vw',
          height: '100vh',
          pointerEvents: 'none',
          zIndex: 10
        }}
      >
        {cardPositions.map((card, i) => (
          <MiniCard
            key={card.id}
            card={card}
            content={getCardContent(card.id)}
            index={i}
            onClick={() => onCardClick(card.id)}
          />
        ))}
      </div>
    </>
  );
};

export default GlassmorphicCards;
