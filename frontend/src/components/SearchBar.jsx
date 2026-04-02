import React, { useState } from 'react';

const SearchBar = ({ onSelect, countries = [] }) => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);

  const handleSearch = (val) => {
    setQuery(val);
    if (val.length < 2) {
      setResults([]);
      return;
    }

    const filtered = countries
      .filter(c => c.country_name.toLowerCase().includes(val.toLowerCase()))
      .slice(0, 5);
    setResults(filtered);
  };

  const selectCountry = (c) => {
    onSelect(c.country_code, c);
    setQuery('');
    setResults([]);
  };

  return (
    <div className="absolute top-6 left-1/2 -translate-x-1/2 w-[340px] z-[100]">
      <div className="relative">
        <input
          type="text"
          value={query}
          onChange={(e) => handleSearch(e.target.value)}
          placeholder="Search countries..."
          className="w-full bg-slate-900/80 backdrop-blur-md border border-slate-700 text-white px-5 py-3 rounded-2xl focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all font-medium"
        />
        <div className="absolute right-4 top-3.5 text-slate-500">🔍</div>
      </div>

      {results.length > 0 && (
        <div className="mt-2 bg-slate-900/90 backdrop-blur-xl border border-slate-700 rounded-2xl overflow-hidden shadow-2xl">
          {results.map(c => (
            <button
              key={c.country_code}
              onClick={() => selectCountry(c)}
              className="w-full text-left px-5 py-3 hover:bg-blue-600/20 text-white transition-colors border-b border-slate-800 last:border-0"
            >
              <b>{c.country_name}</b> <span className="text-slate-500 ml-2">AQI: {c.aqi_value}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

export default SearchBar;
