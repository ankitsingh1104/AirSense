import React, { useState, useCallback, useEffect, useRef } from 'react';
import GlobeContainer from './components/Globe';
import SearchBar from './components/SearchBar';
import LiveBadge from './components/LiveBadge';
import AQILegend from './components/AQILegend';
import GlassmorphicCards from './components/GlassmorphicCards';
import ExpandedCardModal from './components/ExpandedCardModal';
import { useWebSocket } from './hooks/useWebSocket';
import useGlobeData from './hooks/useGlobeData';
import { useCountryInteraction } from './hooks/useCountryInteraction';

const MemoizedGlobe = React.memo(({ globeRef, data, countryDataMap, selectedCountry, simulatedAqi, interactionState, STATES, onCountryClick, onGlobeBackgroundClick, hoveredCountry, setHoveredCountry }) => (
  <GlobeContainer 
    globeRef={globeRef}
    data={data} 
    countryDataMap={countryDataMap}
    selectedCountry={selectedCountry}
    simulatedAqi={simulatedAqi}
    interactionState={interactionState}
    STATES={STATES}
    onCountryClick={onCountryClick}
    onGlobeBackgroundClick={onGlobeBackgroundClick}
    hoveredCountry={hoveredCountry}
    setHoveredCountry={setHoveredCountry}
  />
));

function App() {
  const globeRef = useRef(null);
  const [globeData, setGlobeData] = useState([]);
  const [hoveredCountry, setHoveredCountry] = useState(null);
  const [pulsingCountries, setPulsingCountries] = useState(new Set());

  // Initialize globe data using the new hook
  const { countryDataMap, setCountryDataMap, count, setCount, loading: initialLoading } = useGlobeData();

  // Update globeData when the initial snapshot arrives
  useEffect(() => {
    if (Object.keys(countryDataMap).length > 0) {
      setGlobeData(Object.values(countryDataMap));
    }
  }, [countryDataMap]);

  // Handle live updates from backend via WebSockets
  const handleWsSnapshot = useCallback((snapshot) => {
    const map = {};
    (snapshot || []).forEach((item) => {
      if (item.country_code) {
        map[item.country_code.toUpperCase()] = item;
      }
    });
    setCountryDataMap(map);
    setCount(Object.keys(map).length);
  }, [setCountryDataMap, setCount]);

  const handleWsUpdate = useCallback((updatedCountries, timestamp) => {
    setCountryDataMap((prev) => {
      const next = { ...prev };
      (updatedCountries || []).forEach((country) => {
        if (country.country_code) {
          const key = country.country_code.toUpperCase();
          next[key] = { ...(next[key] || {}), ...country };
          setPulsingCountries((p) => {
            const n = new Set(p);
            n.add(key);
            return n;
          });
          setTimeout(() => {
            setPulsingCountries((p) => {
              const n = new Set(p);
              n.delete(key);
              return n;
            });
          }, 2000);
        }
      });
      setCount(Object.keys(next).length);
      return next;
    });

    if (timestamp) {
      setGlobeData((prev) => prev.map((item) => {
        const code = item.country_code ? item.country_code.toUpperCase() : '';
        const update = (updatedCountries || []).find((u) => (u.country_code || '').toUpperCase() === code);
        if (!update) return item;
        return {
          ...item,
          aqi_value: update.live_aqi ?? item.aqi_value,
          aqi_category: update.aqi_category ?? item.aqi_category,
          dominant_pollutant: update.dominant_pollutant ?? item.dominant_pollutant,
          source: 'live',
          last_updated: timestamp,
        };
      }));
    }
  }, [setCountryDataMap, setCount]);

  const { status, lastUpdated } = useWebSocket(undefined, handleWsSnapshot, handleWsUpdate);

  const {
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
    clearSimulatedAqi
  } = useCountryInteraction(globeRef);

  // Normalize globe/search payloads into interaction payload shape.
  const handleSelectCountry = useCallback((selection, countryObj) => {
    const fromSelection = typeof selection === 'object' && selection !== null ? selection : {};
    const code = (fromSelection.code || selection || countryObj?.country_code || '').toUpperCase();
    if (!code) return;

    const snapshot = countryDataMap[code] || countryObj || {};
    selectCountry({
      code,
      name: fromSelection.name || snapshot.country_name || 'Unknown',
      lat: Number(fromSelection.lat ?? snapshot.lat ?? 0),
      lon: Number(fromSelection.lon ?? snapshot.lon ?? 0),
      aqi: Number(fromSelection.aqi ?? snapshot.aqi_value ?? 0)
    });
  }, [countryDataMap, selectCountry]);

  return (
    <div className="relative w-screen h-screen bg-[#020617] overflow-hidden">
      {/* 3D Globe with dynamic updates */}
      <MemoizedGlobe 
        globeRef={globeRef}
        data={globeData} 
        countryDataMap={countryDataMap}
        pulsingCountries={pulsingCountries}
        selectedCountry={selectedCountry}
        simulatedAqi={simulatedAqi}
        interactionState={state}
        STATES={STATES}
        onCountryClick={handleSelectCountry}
        onGlobeBackgroundClick={dismiss}
        hoveredCountry={hoveredCountry}
        setHoveredCountry={setHoveredCountry}
      />

      {/* Floating UI Elements */}
      <LiveBadge status={status} lastUpdated={lastUpdated} />
      <SearchBar onSelect={handleSelectCountry} countries={globeData} />
      <AQILegend count={globeData.length || count} />

      {/* New cinematic cards overlay */}
      {(state === STATES.CARDS || state === STATES.EXPANDED) && (
        <GlassmorphicCards
          cardPositions={cardPositions}
          countryData={countryData}
          loading={loading}
          selectedCountry={selectedCountry}
          simulatedAqi={simulatedAqi}
          onCardClick={expandCard}
        />
      )}

      {/* Expanded floating modal */}
      {state === STATES.EXPANDED && expandedCard && (
        <ExpandedCardModal
          cardId={expandedCard}
          countryData={countryData}
          selectedCountry={selectedCountry}
          simulatedAqi={simulatedAqi}
          onSimulatedAqiChange={setSimulatedAqi}
          onSimulationReset={clearSimulatedAqi}
          onClose={collapseCard}
        />
      )}

      {/* Legacy right panel kept for rollback; intentionally not rendered */}
      {/*
      {selectedCountry && (
        <CountryPanel
          countryCode={selectedCountry.code}
          countryName={selectedCountry.name}
          initialAqi={selectedCountry.aqi}
          onClose={dismiss}
        />
      )}
      */}

      {state !== STATES.IDLE && (
        <div
          style={{
            position: 'fixed',
            bottom: 24,
            left: '50%',
            transform: 'translateX(-50%)',
            background: 'rgba(0,0,0,0.5)',
            backdropFilter: 'blur(8px)',
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: 20,
            padding: '6px 16px',
            color: 'rgba(255,255,255,0.4)',
            fontSize: 12,
            pointerEvents: 'none',
            zIndex: 5
          }}
        >
          Press Esc or click the globe to dismiss
        </div>
      )}

      {/* Loading Overlay */}
      {initialLoading && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center z-[1000]">
          <div className="flex flex-col items-center gap-4">
            <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
            <p className="text-white font-medium">
              Initialising Globe...
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
