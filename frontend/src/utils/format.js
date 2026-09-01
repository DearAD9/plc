/**
 * Shared formatting utilities for PLC variable display.
 */

/** Format a numeric value to a reasonable number of decimal places. */
export function fmtNumber(val, type) {
  if (val === null || val === undefined) return '—';
  if (typeof val === 'boolean') return val ? 'TRUE' : 'FALSE';
  if (typeof val === 'string') return val;
  if (type === 'REAL' || type === 'LREAL') return Number(val).toFixed(2);
  if (type === 'INT' || type === 'DINT') return Math.round(val).toLocaleString();
  return String(val);
}

/** Format a timestamp to HH:MM:SS.mmm */
export function fmtTime(date) {
  if (!date) return '—';
  const d = date instanceof Date ? date : new Date(date);
  return d.toLocaleTimeString('en-GB', { hour12: false }) +
    '.' + String(d.getMilliseconds()).padStart(3, '0');
}

/** Format ISO timestamp to readable local string */
export function fmtTimestamp(isoStr) {
  if (!isoStr) return '—';
  const d = new Date(isoStr);
  return d.toLocaleString('en-GB', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
    hour12: false,
  });
}

/** Returns 'connected', 'disconnected', or 'connecting' CSS class */
export function connClass(connected, wsState) {
  if (wsState === 'connecting') return 'connecting';
  return connected ? 'connected' : 'disconnected';
}

/** Human-readable uptime from seconds */
export function fmtUptime(seconds) {
  if (seconds === null || seconds === undefined) return '—';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (h > 0) return `${h}h ${m}m ${s}s`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

/** Determine metric-card CSS modifier for a variable */
export function varCardClass(name, value) {
  if (name === 'alarm_active' && value === true)  return 'alarm';
  if (name === 'emergency_stop' && value === false) return 'alarm';
  if (typeof value === 'boolean') return value ? 'bool-true' : 'bool-false';
  return '';
}

/** Recharts-friendly colour palette */
export const CHART_COLORS = [
  '#3b82f6', '#22c55e', '#f59e0b', '#a855f7', '#06b6d4', '#ef4444',
];
