import { useState, useEffect, useRef, useCallback } from 'react'

/**
 * Custom hook for managing WebSocket connection with exponential backoff.
 */
export const useWebSocket = (url, onSnapshot, onUpdate) => {
  const [status, setStatus] = useState('connecting');
  const [lastUpdated, setLastUpdated] = useState(null);
  const wsRef = useRef(null);
  const reconnectTimeout = useRef(null);
  const attemptRef = useRef(0);
  const delays = [1000, 2000, 4000, 8000, 8000];

  const connect = useCallback(() => {
    // Clear any existing connection cleanly
    if (wsRef.current) {
      wsRef.current.onclose = null; // prevent reconnect trigger from old socket
      wsRef.current.close();
    }

    const wsUrl = url || `ws://${window.location.hostname}:8000/ws/stream`
    console.log('Connecting to WebSocket:', wsUrl);
    setStatus('connecting');
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('WebSocket Connected');
      setStatus('connected');
      attemptRef.current = 0; // reset backoff on success
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);

        if (msg.type === 'snapshot') {
          if (onSnapshot) onSnapshot(msg.data);
          if (msg.ts) setLastUpdated(new Date(msg.ts));
        } else if (msg.type === 'update') {
          if (onUpdate) onUpdate(msg.data, msg.ts);
          if (msg.ts) setLastUpdated(new Date(msg.ts));
        }
      } catch (e) {
        console.error('WS parse error:', e);
      }
    };

    ws.onerror = (e) => {
      console.error('WebSocket Error:', e);
      setStatus('reconnecting');
    };

    ws.onclose = () => {
      console.log('WebSocket Closed. Reconnecting...');
      setStatus('reconnecting');
      const delay = delays[Math.min(attemptRef.current, delays.length - 1)];
      attemptRef.current += 1;
      reconnectTimeout.current = setTimeout(connect, delay);
    };
  }, [url, onSnapshot, onUpdate]);

  useEffect(() => {
    // Delay initial connection by one tick to survive React Strict Mode 
    // double-invoke without the "closed before established" error
    const initTimeout = setTimeout(connect, 100);
    
    return () => {
      clearTimeout(initTimeout);
      clearTimeout(reconnectTimeout.current);
      if (wsRef.current) {
        wsRef.current.onclose = null; // prevent reconnect on intentional unmount
        wsRef.current.close();
      }
    };
  }, [connect]);

  return { status, lastUpdated };
}
