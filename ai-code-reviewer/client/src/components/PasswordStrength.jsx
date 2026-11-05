// Підказка надійності пароля для користувача. Це лише індикатор: сервер вимагає лише 8 символів.
export function passwordScore(password) {
  if (!password) return 0;
  let score = 0;
  if (password.length >= 8) score += 1;
  if (password.length >= 12) score += 1;
  if (/[a-zа-яіїєґ]/.test(password) && /[A-ZА-ЯІЇЄҐ]/.test(password)) score += 1;
  if (/\d/.test(password) && /[^A-Za-zА-Яа-яІіЇїЄєҐґ0-9]/.test(password)) score += 1;
  return Math.min(score, 4);
}

const LEVELS = [
  { label: 'Занадто короткий', color: 'var(--crit)' },
  { label: 'Слабкий', color: 'var(--crit)' },
  { label: 'Середній', color: 'var(--warn)' },
  { label: 'Добрий', color: 'var(--ok)' },
  { label: 'Надійний', color: 'var(--ok)' },
];

export default function PasswordStrength({ password }) {
  if (!password) return null;
  const score = passwordScore(password);
  const { label, color } = LEVELS[score];
  return (
    <div className="strength" style={{ '--c': color }} aria-live="polite">
      <div className="bars" aria-hidden="true">
        {[1, 2, 3, 4].map((i) => (
          <i key={i} className={i <= score ? 'on' : ''} />
        ))}
      </div>
      <b>{label}</b>
    </div>
  );
}
