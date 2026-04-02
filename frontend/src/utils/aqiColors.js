/**
 * Standard EPA AQI Color Mapping
 */
export const getAQIColor = (aqi) => {
  if (aqi === null || aqi === undefined || Number.isNaN(Number(aqi))) return '#1a1a2e'; // Unknown
  const v = Number(aqi);
  if (v <= 50) return '#00e400';  // Good
  if (v <= 100) return '#ffff00'; // Moderate
  if (v <= 150) return '#ff7e00'; // Unhealthy for Sensitive
  if (v <= 200) return '#ff0000'; // Unhealthy
  if (v <= 300) return '#8f3f97'; // Very Unhealthy
  return '#7e0023';                // Hazardous
};

export const getAQICategory = (aqi) => {
  if (aqi === null || aqi === undefined) return 'Unknown';
  if (aqi <= 50) return 'Good';
  if (aqi <= 100) return 'Moderate';
  if (aqi <= 150) return 'Unhealthy for Sensitive Groups';
  if (aqi <= 200) return 'Unhealthy';
  if (aqi <= 300) return 'Very Unhealthy';
  return 'Hazardous';
};

export const getPollutantColor = (pollutant) => {
  const colors = {
    co: '#94a3b8',
    ozone: '#38bdf8',
    no2: '#fb923c',
    'pm2.5': '#f87171',
    'pm25': '#f87171'
  };
  return colors[pollutant.toLowerCase()] || '#ffffff';
};
