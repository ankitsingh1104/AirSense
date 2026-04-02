import { useCallback, useEffect, useState } from 'react';

export const STATES = {
  IDLE: 'idle',
  ZOOMING: 'zooming',
  CARDS: 'cards',
  EXPANDED: 'expanded'
};

const CARD_DEFINITIONS = [
  { id: 'aqi', label: 'AQI', icon: '◉', angle: -100 },
  { id: 'pollutants', label: 'Pollutants', icon: '⬡', angle: -40 },
  { id: 'health', label: 'Health', icon: '♥', angle: 20 },
  { id: 'forecast', label: 'Forecast', icon: '◈', angle: 80 },
  { id: 'shap', label: 'Why this?', icon: '◇', angle: 140 },
  { id: 'simulate', label: 'What-If', icon: '⟲', angle: 200 }
];

export function computeCardPositions(country, globe) {
  if (!globe || !country) return [];

  const center = globe.getScreenCoords?.(country.lat, country.lon, 0.005);
  if (!center || !Number.isFinite(center.x) || !Number.isFinite(center.y)) return [];

  const { x: cx, y: cy } = center;
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  const radius = Math.min(280, Math.max(190, Math.min(vw, vh) * 0.24));
  const cardW = 220;
  const cardH = 132;

  return CARD_DEFINITIONS.map((card) => {
    const angleRad = (card.angle * Math.PI) / 180;
    const x = cx + radius * Math.cos(angleRad);
    const y = cy + radius * Math.sin(angleRad);

    return {
      ...card,
      w: cardW,
      h: cardH,
      x: Math.max(10, Math.min(vw - cardW - 10, x - cardW / 2)),
      y: Math.max(10, Math.min(vh - cardH - 10, y - cardH / 2)),
      lineX: cx + radius * 0.45 * Math.cos(angleRad),
      lineY: cy + radius * 0.45 * Math.sin(angleRad)
    };
  });
}

export const useCountryInteraction = (globeRef) => {
  const [state, setState] = useState(STATES.IDLE);
  const [selectedCountry, setSelectedCountry] = useState(null);
  const [countryData, setCountryData] = useState(null);
  const [expandedCard, setExpandedCard] = useState(null);
  const [cardPositions, setCardPositions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [simulatedAqi, setSimulatedAqi] = useState(null);

  const selectCountry = useCallback(async (country) => {
    if (!country?.code) return;

    setState(STATES.ZOOMING);
    setSelectedCountry(country);
    setCountryData(null);
    setExpandedCard(null);
    setSimulatedAqi(null);
    setLoading(true);

    const dataPromise = Promise.all([
      fetch(`/api/realtime/${country.code}`).then((r) => r.json()),
      fetch(`/api/forecast/${country.code}?days=14&refresh=true`).then((r) => r.json()),
      fetch(`/api/history/${country.code}?days=7`).then((r) => (r.ok ? r.json() : [])).catch(() => [])
    ]);

    globeRef.current?.pointOfView(
      { lat: country.lat, lng: country.lon, altitude: 0.4 },
      1000
    );

    const controls = globeRef.current?.controls?.();
    if (controls) {
      controls.autoRotate = false;
    }

    setTimeout(() => {
      const positions = computeCardPositions(country, globeRef.current);
      setCardPositions(positions);
      setState(STATES.CARDS);
    }, 1100);

    try {
      const [realtime, forecast, history] = await dataPromise;
      setCountryData({ realtime, forecast, history });
    } finally {
      setLoading(false);
    }
  }, [globeRef]);

  const expandCard = useCallback((cardId) => {
    setExpandedCard(cardId);
    setState(STATES.EXPANDED);
  }, []);

  const collapseCard = useCallback(() => {
    setExpandedCard(null);
    setState(STATES.CARDS);
  }, []);

  const dismiss = useCallback(() => {
    setState(STATES.IDLE);
    setSelectedCountry(null);
    setCountryData(null);
    setExpandedCard(null);
    setCardPositions([]);
    setSimulatedAqi(null);

    globeRef.current?.pointOfView({ lat: 20, lng: 0, altitude: 1.8 }, 1200);

    setTimeout(() => {
      const controls = globeRef.current?.controls?.();
      if (controls) {
        controls.autoRotate = true;
        controls.autoRotateSpeed = 0.3;
      }
    }, 1300);
  }, [globeRef]);

  useEffect(() => {
    const handler = (e) => {
      if (e.key === 'Escape') {
        if (state === STATES.EXPANDED) collapseCard();
        else if (state === STATES.CARDS) dismiss();
      }
    };

    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [state, collapseCard, dismiss]);

  return {
    state,
    STATES,
    selectedCountry,
    countryData,
    expandedCard,
    simulatedAqi,
    cardPositions,
    loading,
    selectCountry,
    expandCard,
    collapseCard,
    dismiss,
    setSimulatedAqi,
    clearSimulatedAqi: () => setSimulatedAqi(null)
  };
};
