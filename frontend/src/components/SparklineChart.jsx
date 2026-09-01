import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine,
} from 'recharts';
import { fmtTime, CHART_COLORS } from '../utils/format';

function MiniTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const { name, value, unit } = payload[0].payload;
  return (
    <div style={{
      background: 'var(--bg-elevated)',
      border: '1px solid var(--border)',
      borderRadius: 6,
      padding: '6px 10px',
      fontSize: 12,
    }}>
      <div style={{ color: 'var(--text-muted)', marginBottom: 2 }}>
        {fmtTime(payload[0].payload.ts)}
      </div>
      <div style={{ color: 'var(--text-primary)', fontFamily: 'JetBrains Mono, monospace' }}>
        {Number(value).toFixed(3)} <span style={{ color: 'var(--text-muted)' }}>{unit}</span>
      </div>
    </div>
  );
}

export default function SparklineChart({ varConfig, historyData, colorIndex = 0 }) {
  const { name, unit, description } = varConfig;
  const color = CHART_COLORS[colorIndex % CHART_COLORS.length];
  const label = name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

  if (!historyData || historyData.length < 2) {
    return (
      <div className="chart-card" style={{ minHeight: 120, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>Awaiting data…</span>
      </div>
    );
  }

  const latest = historyData[historyData.length - 1]?.value;

  return (
    <div className="chart-card">
      <div className="chart-header">
        <div>
          <div className="chart-title">{label}</div>
          {description && <div className="chart-subtitle">{description}</div>}
        </div>
        <div style={{ textAlign: 'right' }}>
          <span style={{
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: 18,
            fontWeight: 700,
            color: 'var(--text-primary)',
          }}>
            {latest !== undefined ? Number(latest).toFixed(2) : '—'}
          </span>
          {unit && <span style={{ fontSize: 12, color: 'var(--text-muted)', marginLeft: 4 }}>{unit}</span>}
        </div>
      </div>

      <ResponsiveContainer width="100%" height={100}>
        <LineChart data={historyData} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
          <XAxis
            dataKey="ts"
            tickFormatter={v => fmtTime(v).slice(0, 8)}
            tick={{ fontSize: 9, fill: 'var(--text-muted)', fontFamily: 'JetBrains Mono, monospace' }}
            tickLine={false}
            axisLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{ fontSize: 9, fill: 'var(--text-muted)' }}
            tickLine={false}
            axisLine={false}
            width={40}
            tickFormatter={v => Number(v).toFixed(1)}
          />
          <Tooltip content={<MiniTooltip unit={unit} />} />
          <Line
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={1.5}
            dot={false}
            activeDot={{ r: 3, fill: color }}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
