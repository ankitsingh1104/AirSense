/**
 * Health Impact Lookup Tables
 * Based on EPA and WHO AQI standards
 */

export const HEALTH_TABLE = [
  {
    min: 0,
    max: 50,
    category: 'Good',
    general: 'Air quality is satisfactory.',
    children: 'Safe for all outdoor activities.',
    elderly: 'No restrictions needed.',
    heart: 'No restrictions needed.',
    lung: 'No restrictions needed.',
    outdoor: 'Great day for outdoor exercise.',
    color: '#00e400',
    risk: 0, // 0-5 scale
  },
  {
    min: 51,
    max: 100,
    category: 'Moderate',
    general: 'Acceptable air quality. Some pollutants may concern sensitive groups.',
    children: 'Unusually sensitive children should limit prolonged outdoor exertion.',
    elderly: 'Consider reducing prolonged outdoor exertion.',
    heart: 'Consider reducing prolonged outdoor exertion.',
    lung: 'Consider reducing prolonged outdoor exertion.',
    outdoor: 'Sensitive individuals should limit prolonged outdoor exercise.',
    color: '#ffff00',
    risk: 1,
  },
  {
    min: 101,
    max: 150,
    category: 'Unhealthy for Sensitive',
    general: 'Sensitive groups may experience health effects.',
    children: 'Limit prolonged outdoor exertion. Take more breaks.',
    elderly: 'Reduce prolonged or heavy outdoor exertion.',
    heart: 'Avoid prolonged or heavy exertion. Watch for symptoms.',
    lung: 'People with asthma should follow asthma action plans.',
    outdoor: 'Reschedule strenuous outdoor activities.',
    color: '#ff7e00',
    risk: 2,
  },
  {
    min: 151,
    max: 200,
    category: 'Unhealthy',
    general: 'Everyone may begin to experience health effects.',
    children: 'Avoid prolonged outdoor exertion. Move activities indoors.',
    elderly: 'Avoid prolonged or heavy outdoor exertion.',
    heart: 'Avoid prolonged exertion. Keep medication accessible.',
    lung: 'Avoid outdoor exertion. Stay indoors if symptoms develop.',
    outdoor: 'Move workouts indoors. Wear N95 if going outside.',
    color: '#ff0000',
    risk: 3,
  },
  {
    min: 201,
    max: 300,
    category: 'Very Unhealthy',
    general: 'Health alert: serious risk for everyone.',
    children: 'Avoid all outdoor activities. Keep windows closed.',
    elderly: 'Remain indoors and keep activity levels low.',
    heart: 'Avoid all physical activity outdoors. Seek medical advice if symptoms occur.',
    lung: 'Remain indoors. Use air purifiers if available.',
    outdoor: 'Cancel all outdoor activities.',
    color: '#8f3f97',
    risk: 4,
  },
  {
    min: 301,
    max: 999,
    category: 'Hazardous',
    general: 'Health emergency. Everyone is affected.',
    children: 'Keep children indoors. Seal windows and doors.',
    elderly: 'Do not go outside. Seek medical attention if feeling unwell.',
    heart: 'Do not exert yourself. Seek medical attention immediately if symptoms appear.',
    lung: 'Do not go outside for any reason. Use maximum filtration indoors.',
    outdoor: 'No outdoor activities under any circumstances.',
    color: '#7e0023',
    risk: 5,
  },
];

export const getHealthImpact = (aqi) => {
  const aqi_num = Number(aqi) || 0;
  return (
    HEALTH_TABLE.find((r) => aqi_num >= r.min && aqi_num <= r.max) ??
    HEALTH_TABLE[HEALTH_TABLE.length - 1]
  );
};

export const getRiskBar = (risk) => {
  // Returns array of booleans for 5-dot risk visualization
  return Array.from({ length: 5 }, (_, i) => i < risk);
};
