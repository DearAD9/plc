import { connClass, fmtTimestamp } from '../utils/format';

export default function Header({ wsState, plcStatus, health, activeTab, onTabChange }) {
  const connected = plcStatus?.connected ?? false;
  const pillClass = connClass(connected, wsState);
  const pillText  =
    wsState === 'connecting' ? 'CONNECTING' :
    connected ? 'CONNECTED' : 'DISCONNECTED';

  return (
    <header className="header">
      <div className="header-brand">
        <div className="header-brand-icon">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
               stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="2" y="3" width="20" height="14" rx="2"/>
            <line x1="8" y1="21" x2="16" y2="21"/>
            <line x1="12" y1="17" x2="12" y2="21"/>
          </svg>
        </div>
        <div>
          <div className="header-brand-title">PLC Monitor</div>
          <div className="header-brand-sub">
            {plcStatus?.ip ?? '—'} · Rack {plcStatus?.rack ?? '—'} Slot {plcStatus?.slot ?? '—'}
          </div>
        </div>
      </div>

      <nav className="nav-tabs">
        {['Dashboard', 'Variables', 'Charts', 'Settings'].map(tab => (
          <button
            key={tab}
            className={`nav-tab ${activeTab === tab ? 'active' : ''}`}
            onClick={() => onTabChange(tab)}
          >
            {tab}
          </button>
        ))}
      </nav>

      <div className="header-right">
        <span className="timestamp" style={{ display: 'none' }}>
          {fmtTimestamp(health?.timestamp)}
        </span>
        <div className={`conn-pill ${pillClass}`}>
          <span className={`conn-dot ${wsState === 'connecting' ? 'pulse' : ''}`} />
          {pillText}
        </div>
      </div>
    </header>
  );
}
