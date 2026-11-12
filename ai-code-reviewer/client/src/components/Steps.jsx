import { Icon } from './Icon.jsx';

const LABELS = ['Email', 'Лист', 'Пароль'];

// Кроки відновлення пароля: current = 0..2
export default function Steps({ current }) {
  return (
    <ol className="steps" aria-label="Кроки відновлення пароля">
      {LABELS.map((label, i) => {
        const state = i < current ? 'past' : i === current ? 'now' : '';
        return (
          <li key={label} className={state} style={{ display: 'contents' }}>
            {i > 0 && <span className={`bar${i <= current ? ' past' : ''}`} aria-hidden="true" />}
            <span className={state} style={{ display: 'flex', alignItems: 'center', gap: 8, color: state === 'now' ? 'var(--text)' : undefined }}>
              <span className="n">{state === 'past' ? <Icon name="check" size={13} /> : i + 1}</span>
              {label}
            </span>
          </li>
        );
      })}
    </ol>
  );
}
