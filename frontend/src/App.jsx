import { useState, useEffect } from 'react';
import './index.css';
import { usePLC } from './hooks/usePLC';
import { getApiUrl } from './config/api';
import Header from './components/Header';
import DashboardPage from './pages/DashboardPage';
import VariablesPage from './pages/VariablesPage';
import ChartsPage    from './pages/ChartsPage';
import SettingsPage  from './pages/SettingsPage';

const TABS = ['Dashboard', 'Variables', 'Charts', 'Settings'];

export default function App() {
  const [activeTab, setActiveTab]           = useState('Dashboard');
  const [variableConfigs, setVariableConfigs] = useState([]);

  const {
    snapshot, plcStatus, health, wsState, lastUpdated,
    reconnecting, history, triggerReconnect,
  } = usePLC();

  // Fetch variable config once on mount (read from /api/plc/variables)
  useEffect(() => {
    fetch(getApiUrl('/api/plc/variables'))
      .then(r => r.ok ? r.json() : [])
      .then(data => setVariableConfigs(Array.isArray(data) ? data : []))
      .catch(() => {});
  }, []);

  const commonProps = { snapshot, plcStatus, health, lastUpdated, wsState, reconnecting, triggerReconnect, variableConfigs };

  return (
    <div className="page-wrapper">
      <Header
        wsState={wsState}
        plcStatus={plcStatus}
        health={health}
        activeTab={activeTab}
        onTabChange={setActiveTab}
      />
      <main style={{ flex: 1 }}>
        {activeTab === 'Dashboard'  && <DashboardPage {...commonProps} />}
        {activeTab === 'Variables'  && <VariablesPage snapshot={snapshot} variableConfigs={variableConfigs} />}
        {activeTab === 'Charts'     && <ChartsPage history={history} variableConfigs={variableConfigs} />}
        {activeTab === 'Settings'   && <SettingsPage {...commonProps} />}
      </main>
      <footer style={{
        borderTop: '1px solid var(--border)',
        padding: '10px 24px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        background: 'var(--bg-surface)',
      }}>
        <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
          PLC Monitor · Read-only dashboard · Siemens Snap7
        </span>
        <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
          WS: <strong style={{ color: wsState === 'open' ? 'var(--green)' : 'var(--red)' }}>
            {wsState.toUpperCase()}
          </strong>
          {' · '}{variableConfigs.length} tags configured
        </span>
      </footer>
    </div>
  );
}
