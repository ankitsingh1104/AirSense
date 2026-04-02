import React, { useEffect, useRef, useState, useMemo } from 'react';
import Globe from 'globe.gl';
import { getAQIColor } from '../utils/aqiColors';

// Suppress globe.gl internal Three.js deprecation warnings
const _warn = console.warn.bind(console);
console.warn = (...args) => {
  if (args[0]?.includes?.('THREE.Clock')) return;
  _warn(...args);
};

const containerStyle = { width: '100%', height: '100vh' };

const GlobeContainer = ({ 
  globeRef,
  data = [], 
  countryDataMap,
  selectedCountry,
  simulatedAqi,
  interactionState,
  STATES,
  onCountryClick, 
  onGlobeBackgroundClick,
  hoveredCountry, 
  setHoveredCountry 
}) => {
  const containerRef = useRef(null);
  const globeInstanceRef = useRef(null);
  const ignoreNextGlobeClickRef = useRef(false);
  const [countries, setCountries] = useState({ features: [] });

  // 1. Load GeoJSON ONCE on mount
  useEffect(() => {
    fetch('https://raw.githubusercontent.com/vasturiano/globe.gl/master/example/datasets/ne_110m_admin_0_countries.geojson')
      .then(res => res.json())
      .then(setCountries);
  }, []);

  // 2. Initialize Globe Instance ONCE on mount
  useEffect(() => {
    if (globeInstanceRef.current || !containerRef.current) return;

    const globe = Globe()(containerRef.current);
    globeInstanceRef.current = globe;
    if (globeRef) globeRef.current = globe;

    // Static configuration
    globe
      .globeImageUrl('https://unpkg.com/three-globe/example/img/earth-blue-marble.jpg')
      .backgroundImageUrl('//unpkg.com/three-globe/example/img/night-sky.png')
      .atmosphereColor('#4488ff')
      .atmosphereAltitude(0.15)
      .polygonSideColor(() => 'rgba(255, 255, 255, 0.05)')
      .polygonStrokeColor(() => 'rgba(255, 255, 255, 0.2)');

    globe.controls().autoRotate = true;
    globe.controls().autoRotateSpeed = 0.3;

    return () => {
      if (globeInstanceRef.current) {
        globeInstanceRef.current._destructor();
        globeInstanceRef.current = null;
        if (globeRef) globeRef.current = null;
      }
    };
  }, [globeRef]);

  // 3. Handle Resize WITHOUT remounting
  useEffect(() => {
    const observer = new ResizeObserver(() => {
      if (globeInstanceRef.current && containerRef.current) {
        globeInstanceRef.current.width(containerRef.current.clientWidth);
        globeInstanceRef.current.height(containerRef.current.clientHeight);
      }
    });
    if (containerRef.current) observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  // 4. Map data to country code for quick lookup
  const dataMap = useMemo(() => {
    if (countryDataMap && Object.keys(countryDataMap).length > 0) {
      return countryDataMap;
    }
    return data.reduce((acc, item) => {
      if (item.country_code) {
        acc[item.country_code.toUpperCase()] = item;
      }
      return acc;
    }, {});
  }, [data, countryDataMap]);

  useEffect(() => {
    const sampleSnapshot = Object.entries(dataMap)[0];
    const sampleGeo = countries?.features?.[0]?.properties?.ISO_A2;
    if (sampleSnapshot || sampleGeo) {
      console.log('Sample snapshot item:', sampleSnapshot);
      console.log('Sample GeoJSON code:', sampleGeo);
    }
  }, [dataMap, countries]);

  const getFeatureCenter = (feat) => {
    const dataItem = dataMap[feat.properties.ISO_A2] || {};
    if (Number.isFinite(dataItem.lat) && Number.isFinite(dataItem.lon)) {
      return { lat: dataItem.lat, lon: dataItem.lon };
    }

    const ring = feat?.geometry?.coordinates?.[0];
    if (Array.isArray(ring) && ring.length > 0) {
      let minLng = Infinity;
      let maxLng = -Infinity;
      let minLat = Infinity;
      let maxLat = -Infinity;
      ring.forEach((p) => {
        if (!Array.isArray(p) || p.length < 2) return;
        minLng = Math.min(minLng, p[0]);
        maxLng = Math.max(maxLng, p[0]);
        minLat = Math.min(minLat, p[1]);
        maxLat = Math.max(maxLat, p[1]);
      });
      if (Number.isFinite(minLat) && Number.isFinite(minLng)) {
        return { lat: (minLat + maxLat) / 2, lon: (minLng + maxLng) / 2 };
      }
    }

    return { lat: 0, lon: 0 };
  };

  // 5. Update Polygons Data ONLY when features load
  useEffect(() => {
    if (!globeInstanceRef.current || !countries.features.length) return;
    globeInstanceRef.current.polygonsData(countries.features);
  }, [countries.features]);

  // 6. Update Visuals ONLY when data or hover state changes
  useEffect(() => {
    if (!globeInstanceRef.current) return;

    globeInstanceRef.current
      .polygonCapColor(feat => {
        const code = feat.properties.ISO_A2;
        const countryData =
          dataMap[code]
          ?? dataMap[code?.toUpperCase()]
          ?? dataMap[code?.toLowerCase()];
        const selectedOverride = selectedCountry && code === selectedCountry.code && simulatedAqi !== null
          ? simulatedAqi
          : countryData?.aqi_value;
        const baseColor = selectedOverride !== undefined && selectedOverride !== null
          ? getAQIColor(selectedOverride)
          : '#1a1a2e';
        const shouldDim = STATES && interactionState !== STATES.IDLE && selectedCountry && code !== selectedCountry.code;
        return shouldDim ? `${baseColor}55` : baseColor;
      })
      .polygonAltitude(feat => 
        (hoveredCountry && hoveredCountry.properties.ISO_A2 === feat.properties.ISO_A2) || (selectedCountry && selectedCountry.code === feat.properties.ISO_A2)
          ? 0.04
          : 0.01
      )
      .polygonLabel(feat => {
        const countryData = dataMap[feat.properties.ISO_A2];
        const aqi = countryData ? countryData.aqi_value : 'N/A';
        const category = countryData ? countryData.aqi_category : 'No Data';
        const color = getAQIColor(countryData?.aqi_value);
        
        return `
          <div style="background: #111827; padding: 12px; border-radius: 8px; border: 1px solid #374151; color: white;">
            <b style="font-size: 14px;">${feat.properties.NAME}</b><br/>
            <div style="margin-top: 4px;">
              AQI: <span style="color: ${color}; font-weight: bold;">${aqi}</span>
            </div>
            <div style="font-size: 11px; color: #9ca3af;">${category}</div>
          </div>
        `;
      })
      .onPolygonHover(setHoveredCountry)
      .onPolygonClick(feat => {
        ignoreNextGlobeClickRef.current = true;
        const code = feat.properties.ISO_A2;
        const countryData = dataMap[code] || {};
        const center = getFeatureCenter(feat);
        if (onCountryClick) {
          onCountryClick({
            code,
            name: feat.properties.NAME || countryData.country_name || code,
            lat: center.lat,
            lon: center.lon,
            aqi: countryData?.aqi_value ?? 0
          });
        }
      });

    globeInstanceRef.current.onGlobeClick(() => {
      if (ignoreNextGlobeClickRef.current) {
        ignoreNextGlobeClickRef.current = false;
        return;
      }
      if (STATES && interactionState !== STATES.IDLE && onGlobeBackgroundClick) {
        onGlobeBackgroundClick();
      }
    });
  }, [
    dataMap,
    hoveredCountry,
    interactionState,
    onCountryClick,
    onGlobeBackgroundClick,
    simulatedAqi,
    selectedCountry,
    setHoveredCountry,
    STATES
  ]);

  useEffect(() => {
    const controls = globeInstanceRef.current?.controls?.();
    if (!controls || !STATES) return;
    controls.autoRotate = interactionState === STATES.IDLE;
  }, [interactionState, STATES]);

  return <div ref={containerRef} style={containerStyle} />;
};

export default GlobeContainer;
