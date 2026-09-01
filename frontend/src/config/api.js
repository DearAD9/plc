/**
 * Frontend API & WebSocket configuration.
 *
 * Configurable via Vite environment variables:
 * - Development: VITE_API_URL=http://localhost:8000
 * - Production:  VITE_API_URL=https://api.example.com (or omitted/empty for same-origin / reverse proxy)
 */

export const API_BASE_URL = (import.meta.env.VITE_API_URL || '').replace(/\/+$/, '');

/**
 * Resolves a full API URL for a given REST endpoint path.
 *
 * @param {string} path - API endpoint path (e.g. '/api/plc/status')
 * @returns {string} Fully resolved API URL or relative path
 */
export function getApiUrl(path = '') {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return API_BASE_URL ? `${API_BASE_URL}${normalizedPath}` : normalizedPath;
}

/**
 * Resolves a WebSocket URL for a given path.
 * Converts http:// -> ws:// and https:// -> wss:// when VITE_API_URL is configured.
 *
 * @param {string} path - WebSocket endpoint path (e.g. '/ws/plc')
 * @returns {string} Fully resolved WebSocket URL
 */
export function getWebSocketUrl(path = '/ws/plc') {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  if (API_BASE_URL) {
    const wsBase = API_BASE_URL
      .replace(/^http:\/\//i, 'ws://')
      .replace(/^https:\/\//i, 'wss://');
    return `${wsBase}${normalizedPath}`;
  }

  // Fallback to current host (for proxy / reverse-proxy / same-origin deployments)
  if (typeof window !== 'undefined' && window.location && window.location.host) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocol}//${window.location.host}${normalizedPath}`;
  }

  return normalizedPath;
}

