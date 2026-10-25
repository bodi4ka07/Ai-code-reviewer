import { formatDate, scoreColor } from '../utils.js';

export function Sparkline({ values, color, width = 110, height = 36 }) {
  if (values.length < 2) return <svg width={width} height={height} aria-hidden="true" />;
  const max = Math.max(...values);
  const min = Math.min(...values);
  const points = values
    .map((v, i) => {
      const x = (i * width) / (values.length - 1);
      const y = height - 4 - ((v - min) / (max - min || 1)) * (height - 8);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(' ');
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} aria-hidden="true">
      <polyline points={points} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

// history: [{ score, date, review_id }] у хронологічному порядку
export function AreaChart({ history }) {
  if (history.length === 0) return <div className="empty">Ще немає завершених рев'ю</div>;

  const W = 560;
  const H = 220;
  const px = 34;
  const py = 18;
  const x = (i) => (history.length === 1 ? (px + W - 12) / 2 : px + (i * (W - px - 12)) / (history.length - 1));
  const y = (v) => py + (1 - v / 100) * (H - py * 2);
  const pts = history.map((p, i) => [x(i), y(p.score)]);
  const line = pts.map((q, i) => `${i ? 'L' : 'M'}${q[0].toFixed(1)} ${q[1].toFixed(1)}`).join(' ');
  const area = `${line} L${pts[pts.length - 1][0]} ${H - py} L${pts[0][0]} ${H - py}Z`;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Динаміка оцінки" className="chart">
      <defs>
        <linearGradient id="areaFill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="var(--accent)" stopOpacity=".35" />
          <stop offset="1" stopColor="var(--accent)" stopOpacity="0" />
        </linearGradient>
        <linearGradient id="lineStroke" x1="0" x2="1">
          <stop offset="0" stopColor="var(--accent)" />
          <stop offset="1" stopColor="var(--accent2)" />
        </linearGradient>
      </defs>
      {[0, 25, 50, 75, 100].map((v) => (
        <g key={v}>
          <line x1={px} x2={W - 8} y1={y(v)} y2={y(v)} stroke="var(--border)" strokeDasharray="3 5" />
          <text x="0" y={y(v) + 4} fill="var(--faint)" fontSize="11">
            {v}
          </text>
        </g>
      ))}
      {history.length > 1 && <path d={area} fill="url(#areaFill)" />}
      {history.length > 1 && (
        <path d={line} fill="none" stroke="url(#lineStroke)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
      )}
      {pts.map((q, i) => (
        <circle key={history[i].review_id} cx={q[0]} cy={q[1]} r="5" fill="var(--surface)" stroke={scoreColor(history[i].score)} strokeWidth="2.5">
          <title>{`${formatDate(history[i].date)}: ${history[i].score}`}</title>
        </circle>
      ))}
    </svg>
  );
}

const CAT_COLORS = {
  bug: 'var(--bug)',
  security: 'var(--security)',
  style: 'var(--style)',
  performance: 'var(--performance)',
};

// categories: [{ category, count }]
export function Donut({ categories, labels }) {
  const total = categories.reduce((a, c) => a + c.count, 0);
  if (total === 0) return <div className="empty">Проблем не знайдено</div>;

  const R = 56;
  const C = 2 * Math.PI * R;
  let offset = 0;
  const segments = categories.map((c) => {
    const len = (c.count / total) * C;
    const seg = (
      <circle
        key={c.category}
        cx="70"
        cy="70"
        r={R}
        fill="none"
        stroke={CAT_COLORS[c.category]}
        strokeWidth="16"
        strokeDasharray={`${Math.max(len - 3, 0)} ${C}`}
        strokeDashoffset={-offset}
      />
    );
    offset += len;
    return seg;
  });

  return (
    <div className="donut-wrap">
      <div className="donut">
        <svg viewBox="0 0 140 140" aria-hidden="true">
          <circle cx="70" cy="70" r={R} fill="none" stroke="var(--border)" strokeWidth="16" />
          {segments}
        </svg>
        <div className="c">
          <div>
            {total}
            <small>проблем</small>
          </div>
        </div>
      </div>
      <div className="legend">
        {categories.map((c) => (
          <div key={c.category}>
            <i style={{ background: CAT_COLORS[c.category] }} />
            {labels[c.category]}
            <b>{c.count}</b>
          </div>
        ))}
      </div>
    </div>
  );
}

export function ScoreRing({ score }) {
  const R = 52;
  const C = 2 * Math.PI * R;
  return (
    <div className="ring">
      <svg viewBox="0 0 120 120" aria-hidden="true">
        <circle cx="60" cy="60" r={R} fill="none" stroke="var(--border)" strokeWidth="10" />
        <circle
          cx="60"
          cy="60"
          r={R}
          fill="none"
          stroke={scoreColor(score)}
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={C}
          strokeDashoffset={C * (1 - score / 100)}
        />
      </svg>
      <div className="num">
        <div>
          {score}
          <small>із 100</small>
        </div>
      </div>
    </div>
  );
}
