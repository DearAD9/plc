import { fmtNumber, fmtTimestamp } from '../utils/format';

export default function VariablesPage({ snapshot, variableConfigs }) {
  const variables = snapshot?.variables ?? {};
  const details   = snapshot?.details   ?? {};
  const errors    = snapshot?.errors    ?? {};

  return (
    <div className="main-content">
      <div className="section-header">
        <span className="section-title">All Variables — Live Table</span>
      </div>

      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <table className="data-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>DB / Addr</th>
              <th>Type</th>
              <th>Value</th>
              <th>Unit</th>
              <th>Quality</th>
              <th>Description</th>
            </tr>
          </thead>
          <tbody>
            {variableConfigs.map(cfg => {
              const { name, db, byte, bit, type, unit, description } = cfg;
              const val     = variables[name] ?? null;
              const det     = details[name];
              const err     = errors[name];
              const quality = det?.quality ?? (err ? 'BAD' : (snapshot ? 'GOOD' : 'UNCERTAIN'));
              const addr    = bit !== undefined && bit !== null
                ? `DB${db}.DBX${byte}.${bit}` : `DB${db}.DB${byte}`;

              return (
                <tr key={name}>
                  <td>
                    <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                      {name}
                    </span>
                  </td>
                  <td>
                    <code style={{
                      fontSize: 11,
                      background: 'var(--bg-elevated)',
                      padding: '2px 6px',
                      borderRadius: 4,
                      fontFamily: 'JetBrains Mono, monospace',
                    }}>{addr}</code>
                  </td>
                  <td>
                    <span className="metric-type-badge">{type}</span>
                  </td>
                  <td style={{
                    fontFamily: 'JetBrains Mono, monospace',
                    fontSize: 13,
                    color: err ? 'var(--red)' : 'var(--text-primary)',
                  }}>
                    {err ? <span title={err}>ERR</span> : fmtNumber(val, type)}
                  </td>
                  <td style={{ color: 'var(--text-muted)' }}>{unit ?? '—'}</td>
                  <td>
                    <span className={`quality-dot quality-${quality}`} />{' '}
                    <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{quality}</span>
                  </td>
                  <td style={{ color: 'var(--text-muted)', maxWidth: 200 }}>{description ?? '—'}</td>
                </tr>
              );
            })}

            {variableConfigs.length === 0 && (
              <tr>
                <td colSpan={7} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 32 }}>
                  No variable configurations loaded.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {snapshot?.timestamp && (
        <p className="timestamp" style={{ marginTop: 12 }}>
          Snapshot timestamp: {fmtTimestamp(snapshot.timestamp)}
        </p>
      )}
    </div>
  );
}
