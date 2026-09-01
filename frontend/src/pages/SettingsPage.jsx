import { fmtTimestamp } from '../utils/format';
import { RefreshCw } from 'lucide-react';

export default function SettingsPage({
  plcStatus, health, wsState, reconnecting, triggerReconnect,
}) {
  const rows = [
    { label: 'PLC IP Address',           value: plcStatus?.ip ?? '—' },
    { label: 'Rack',                      value: plcStatus?.rack ?? '—' },
    { label: 'Slot',                      value: plcStatus?.slot ?? '—' },
    { label: 'Port',                      value: plcStatus?.port ?? '—' },
    { label: 'Poll Interval',             value: plcStatus?.poll_interval_seconds != null ? `${plcStatus.poll_interval_seconds}s` : '—' },
    { label: 'Reconnect Interval',        value: plcStatus?.reconnect_interval_seconds != null ? `${plcStatus.reconnect_interval_seconds}s` : '—' },
    { label: 'Configured Variables',      value: plcStatus?.total_configured_variables ?? '—' },
    { label: 'CPU State',                 value: plcStatus?.cpu_state ?? '—' },
    { label: 'CPU Info',                  value: plcStatus?.cpu_info ? JSON.stringify(plcStatus.cpu_info) : '—' },
    { label: 'Last Successful Read',      value: fmtTimestamp(plcStatus?.last_successful_read) },
    { label: 'Last Error',                value: plcStatus?.last_error ?? 'None' },
    { label: 'WebSocket State',           value: wsState.toUpperCase() },
    { label: 'Active WS Connections',     value: health?.active_websocket_connections ?? '—' },
    { label: 'Backend Status',            value: health?.status?.toUpperCase() ?? '—' },
    { label: 'Server Timestamp (UTC)',    value: fmtTimestamp(health?.timestamp) },
  ];

  return (
    <div className="main-content">
      <div className="section-header">
        <span className="section-title">Connection &amp; Configuration</span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <div className="card">
          <div style={{ fontWeight: 600, marginBottom: 16, fontSize: 14 }}>PLC Connection Details</div>
          {rows.slice(0, 7).map(r => (
            <div className="settings-row" key={r.label}>
              <span className="settings-label">{r.label}</span>
              <span className="settings-value">{r.value}</span>
            </div>
          ))}
        </div>

        <div className="card">
          <div style={{ fontWeight: 600, marginBottom: 16, fontSize: 14 }}>Runtime Status</div>
          {rows.slice(7).map(r => (
            <div className="settings-row" key={r.label}>
              <span className="settings-label">{r.label}</span>
              <span className="settings-value" style={{
                maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis',
                color: r.label === 'Last Error' && r.value !== 'None' ? 'var(--red)' : undefined,
              }}>
                {r.value}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Manual reconnect */}
      <div className="card" style={{ marginTop: 16 }}>
        <div style={{ fontWeight: 600, marginBottom: 8, fontSize: 14 }}>Manual Actions</div>
        <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 16 }}>
          Trigger an immediate reconnection attempt to the Siemens PLC.
          The backend will already retry automatically; this forces it now.
        </p>
        <button
          className="btn btn-primary"
          onClick={triggerReconnect}
          disabled={reconnecting}
          style={{ width: 180 }}
        >
          {reconnecting
            ? <><span className="spinner" style={{ width: 14, height: 14 }} /> Connecting…</>
            : <><RefreshCw size={14} /> Reconnect to PLC</>}
        </button>
      </div>

      <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 20 }}>
        Configuration is defined in <code>config/plc_config.json</code> and
        <code> config/settings.yaml</code> on the backend.
        This dashboard is read-only.
      </p>
    </div>
  );
}
