import { fmtNumber, varCardClass } from '../utils/format';

const TYPE_LABELS = {
  BOOL: 'BOOL', BYTE: 'BYTE', WORD: 'WORD', DWORD: 'DWORD',
  INT: 'INT', DINT: 'DINT', REAL: 'REAL', LREAL: 'LREAL', STRING: 'STR',
};

function BoolDisplay({ value, name }) {
  if (value === null || value === undefined) {
    return <span className="metric-value null">—</span>;
  }
  const isAlarm =
    (name === 'alarm_active' && value === true) ||
    (name === 'emergency_stop' && value === false);
  const label = value ? 'TRUE' : 'FALSE';
  return (
    <span className={`bool-badge ${value ? 'true' : 'false'}`}>
      <span className={`conn-dot ${isAlarm ? 'pulse' : ''}`} />
      {label}
    </span>
  );
}

export default function MetricCard({ varConfig, value, isStale }) {
  const { name, type, unit, description } = varConfig;
  const cardClass = ['metric-card', isStale ? 'stale' : '', varCardClass(name, value)]
    .filter(Boolean).join(' ');

  const isBool = type === 'BOOL';
  const isString = type === 'STRING';
  const label = name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

  return (
    <div className={cardClass}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span className="metric-label">{label}</span>
        <span className="metric-type-badge">{TYPE_LABELS[type] ?? type}</span>
      </div>

      {isBool ? (
        <BoolDisplay value={value} name={name} />
      ) : isString ? (
        <div className="metric-value" style={{ fontSize: 14, wordBreak: 'break-all' }}>
          {value ?? <span className="null">—</span>}
        </div>
      ) : (
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
          <span className={`metric-value ${value === null || value === undefined ? 'null' : ''}`}>
            {value === null || value === undefined ? '—' : fmtNumber(value, type)}
          </span>
          {unit && <span className="metric-unit">{unit}</span>}
        </div>
      )}

      {description && <p className="metric-description">{description}</p>}
    </div>
  );
}
