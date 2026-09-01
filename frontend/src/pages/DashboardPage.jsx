import { fmtTimestamp, fmtTime } from '../utils/format';
import MetricCard from '../components/MetricCard';
import { RefreshCw, AlertTriangle, WifiOff } from 'lucide-react';

const BOOL_VARS = ['motor_running', 'alarm_active', 'emergency_stop'];

export default function DashboardPage({
  snapshot, plcStatus, lastUpdated, wsState, reconnecting, triggerReconnect,
  variableConfigs,
}) {
  const connected   = snapshot?.plc_connected ?? false;
  const variables   = snapshot?.variables ?? {};
  const isStale     = !snapshot || !connected;

  // Split configs into booleans and numerics
  const boolConfigs    = variableConfigs.filter(v => v.type === 'BOOL');
  const numericConfigs = variableConfigs.filter(v => v.type !== 'BOOL');

  return (
    <div className="main-content">
      {/* Disconnected banner */}
      {wsState === 'closed' && (
        <div className="alert-banner error">
          <WifiOff size={16} />
          <span className="alert-banner-text">
            WebSocket disconnected — attempting to reconnect to backend…
          </span>
        </div>
      )}
      {wsState === 'open' && !connected && (
        <div className="alert-banner warning">
          <AlertTriangle size={16} />
          <span className="alert-banner-text">
            {plcStatus?.last_successful_read
              ? `PLC disconnected — showing last known values.`
              : `No live PLC data available. Backend is running but PLC is unreachable at ${plcStatus?.ip ?? '—'}.`}
          </span>
          <button
            className="btn btn-secondary"
            style={{ minWidth: 110 }}
            onClick={triggerReconnect}
            disabled={reconnecting}
          >
            {reconnecting ? (
              <><span className="spinner" style={{ width: 12, height: 12 }} /> Connecting…</>
            ) : (
              <><RefreshCw size={12} /> Reconnect</>
            )}
          </button>
        </div>
      )}

      {/* Summary status bar */}
      <div className="status-bar">
        <div className="status-bar-item">
          <span className="status-bar-label">PLC IP</span>
          <span className="status-bar-value mono">{plcStatus?.ip ?? '—'}</span>
        </div>
        <div className="status-bar-item">
          <span className="status-bar-label">CPU State</span>
          <span className="status-bar-value" style={{
            color: plcStatus?.cpu_state === 'RUN' ? 'var(--green)' :
                   plcStatus?.cpu_state ? 'var(--amber)' : 'var(--text-muted)',
          }}>
            {plcStatus?.cpu_state ?? '—'}
          </span>
        </div>
        <div className="status-bar-item">
          <span className="status-bar-label">Poll Interval</span>
          <span className="status-bar-value mono">
            {plcStatus?.poll_interval_seconds != null
              ? `${plcStatus.poll_interval_seconds}s` : '—'}
          </span>
        </div>
        <div className="status-bar-item">
          <span className="status-bar-label">Poll Duration</span>
          <span className="status-bar-value mono">
            {snapshot?.poll_duration_ms != null
              ? `${snapshot.poll_duration_ms.toFixed(1)} ms` : '—'}
          </span>
        </div>
        <div className="status-bar-item">
          <span className="status-bar-label">Variables</span>
          <span className="status-bar-value">{plcStatus?.total_configured_variables ?? '—'}</span>
        </div>
        <div className="status-bar-item">
          <span className="status-bar-label">Last Read</span>
          <span className="status-bar-value mono" style={{ fontSize: 12 }}>
            {lastUpdated ? fmtTime(lastUpdated).slice(0, 8) : '—'}
          </span>
        </div>
      </div>

      {/* Digital / Boolean signals */}
      {boolConfigs.length > 0 && (
        <>
          <div className="section-header">
            <span className="section-title">Digital Signals</span>
          </div>
          <div className="grid-3" style={{ marginBottom: 24 }}>
            {boolConfigs.map(cfg => (
              <MetricCard
                key={cfg.name}
                varConfig={cfg}
                value={variables[cfg.name] ?? null}
                isStale={isStale}
              />
            ))}
          </div>
        </>
      )}

      {/* Analogue / Numeric variables */}
      {numericConfigs.length > 0 && (
        <>
          <div className="section-header">
            <span className="section-title">Analogue &amp; Registers</span>
          </div>
          <div className="grid-auto">
            {numericConfigs.map(cfg => (
              <MetricCard
                key={cfg.name}
                varConfig={cfg}
                value={variables[cfg.name] ?? null}
                isStale={isStale}
              />
            ))}
          </div>
        </>
      )}

      {/* Last successful PLC read */}
      {plcStatus?.last_successful_read && (
        <p className="timestamp" style={{ marginTop: 8 }}>
          Last successful read: {fmtTimestamp(plcStatus.last_successful_read)}
        </p>
      )}
      {plcStatus?.last_error && (
        <p className="timestamp" style={{ marginTop: 4, color: 'var(--red)' }}>
          Last error: {plcStatus.last_error}
        </p>
      )}
    </div>
  );
}
