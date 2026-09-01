/**
 * usePLC hook — manages WebSocket connection + periodic REST polling.
 * WebSocket: /ws/plc             (live snapshots, configured via VITE_API_URL)
 * REST:      GET /api/plc/status (connection metadata)
 *            GET /api/health     (backend health)
 *            POST /api/plc/reconnect (manual reconnect trigger)
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { getApiUrl, getWebSocketUrl } from '../config/api';

const STATUS_INTERVAL_MS   = 5000;
const MAX_HISTORY_POINTS   = 60;  // 60 data points kept per numeric variable

export function usePLC() {
  const [snapshot, setSnapshot]     = useState(null);
  const [plcStatus, setPlcStatus]   = useState(null);
  const [health, setHealth]         = useState(null);
  const [wsState, setWsState]       = useState('connecting'); // connecting | open | closed
  const [lastUpdated, setLastUpdated] = useState(null);
  const [reconnecting, setReconnecting] = useState(false);

  // history: { [varName]: [{ ts: Date, value: number }] }
  const [history, setHistory]       = useState({});

  const wsRef       = useRef(null);
  const reconnTimer = useRef(null);
  const mountedRef  = useRef(true);

  // ── REST helpers ──────────────────────────────────────────────────────
  const fetchStatus = useCallback(async () => {
    try {
      const [statusRes, healthRes] = await Promise.all([
        fetch(getApiUrl('/api/plc/status')),
        fetch(getApiUrl('/api/health')),
      ]);
      if (statusRes.ok) setPlcStatus(await statusRes.json());
      if (healthRes.ok) setHealth(await healthRes.json());
    } catch (_) {
      // Backend unreachable — keep previous values
    }
  }, []);

  const triggerReconnect = useCallback(async () => {
    if (reconnecting) return;
    setReconnecting(true);
    try {
      const res = await fetch(getApiUrl('/api/plc/reconnect'), { method: 'POST' });
      if (res.ok) await fetchStatus();
    } finally {
      setReconnecting(false);
    }
  }, [reconnecting, fetchStatus]);

  // ── History updater ───────────────────────────────────────────────────
  const pushHistory = useCallback((variables) => {
    const now = new Date();
    setHistory(prev => {
      const next = { ...prev };
      for (const [key, val] of Object.entries(variables)) {
        if (typeof val === 'number') {
          const arr = prev[key] ? [...prev[key]] : [];
          arr.push({ ts: now, value: val });
          if (arr.length > MAX_HISTORY_POINTS) arr.shift();
          next[key] = arr;
        }
      }
      return next;
    });
  }, []);

  // ── WebSocket ─────────────────────────────────────────────────────────
  const connectWS = useCallback(() => {
    if (!mountedRef.current) return;
    if (wsRef.current) wsRef.current.close();

    setWsState('connecting');
    const wsUrl = getWebSocketUrl('/ws/plc');
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      if (!mountedRef.current) return;
      setWsState('open');
      clearTimeout(reconnTimer.current);
      fetchStatus();
    };

    ws.onmessage = (evt) => {
      if (!mountedRef.current) return;
      try {
        const data = JSON.parse(evt.data);
        setSnapshot(data);
        setLastUpdated(new Date());
        if (data.variables) pushHistory(data.variables);
      } catch (_) { /* ignore parse errors */ }
    };

    ws.onclose = () => {
      if (!mountedRef.current) return;
      setWsState('closed');
      // Exponential back-off reconnect (1 s, capped)
      reconnTimer.current = setTimeout(connectWS, 1000);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [fetchStatus, pushHistory]);

  useEffect(() => {
    mountedRef.current = true;
    connectWS();
    const pollId = setInterval(fetchStatus, STATUS_INTERVAL_MS);
    return () => {
      mountedRef.current = false;
      clearTimeout(reconnTimer.current);
      clearInterval(pollId);
      wsRef.current?.close();
    };
  }, [connectWS, fetchStatus]);

  return {
    snapshot,
    plcStatus,
    health,
    wsState,
    lastUpdated,
    reconnecting,
    history,
    triggerReconnect,
    refetch: fetchStatus,
  };
}
