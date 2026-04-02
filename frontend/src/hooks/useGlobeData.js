import { useState, useEffect } from 'react';

const useGlobeData = () => {
  const [countryDataMap, setCountryDataMap] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [count, setCount] = useState(0);

  useEffect(() => {
    const fetchSnapshot = async () => {
      try {
        console.log('Fetching globe snapshot...');
        const res = await fetch('/api/globe/snapshot');
        console.log('Response status:', res.status);
        if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        const data = await res.json();
        console.log('Snapshot data count:', data.length);
        
        // Build a map keyed by ISO_A2 country code for fast globe lookup
        const map = {};
        data.forEach(item => {
          if (item.country_code) {
            map[item.country_code.toUpperCase()] = item;
          }
        });
        console.log(`Loaded ${Object.keys(map).length} countries into map`);
        setCountryDataMap(map);
        setCount(Object.keys(map).length);
      } catch (err) {
        console.error('Failed to fetch globe snapshot:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchSnapshot();
  }, []);

  return { countryDataMap, setCountryDataMap, loading, error, count, setCount };
};

export default useGlobeData;
