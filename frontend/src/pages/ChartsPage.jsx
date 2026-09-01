import SparklineChart from '../components/SparklineChart';

export default function ChartsPage({ history, variableConfigs }) {
  // Only show numeric (non-BOOL, non-STRING) variables
  const numericConfigs = variableConfigs.filter(
    v => v.type !== 'BOOL' && v.type !== 'STRING'
  );

  return (
    <div className="main-content">
      <div className="section-header">
        <span className="section-title">Live Time-Series Charts</span>
        <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 8 }}>
          Last 60 samples · updates in real-time
        </span>
      </div>

      {numericConfigs.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: 48, color: 'var(--text-muted)' }}>
          No numeric variables configured.
        </div>
      ) : (
        <div className="chart-grid">
          {numericConfigs.map((cfg, idx) => (
            <SparklineChart
              key={cfg.name}
              varConfig={cfg}
              historyData={history[cfg.name] ?? []}
              colorIndex={idx}
            />
          ))}
        </div>
      )}
    </div>
  );
}
