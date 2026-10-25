export const LANGUAGES = [
  { value: 'python', label: 'Python' },
  { value: 'javascript', label: 'JavaScript' },
  { value: 'typescript', label: 'TypeScript' },
  { value: 'other', label: 'Інша (лише AI)' },
];

export const languageLabel = (code) => (LANGUAGES.find((l) => l.value === code) || { label: code }).label;

export const CATEGORIES = {
  bug: 'Баги',
  security: 'Безпека',
  style: 'Стиль',
  performance: 'Продуктивність',
};

export const SEVERITIES = { critical: 'Критично', warning: 'Увага', info: 'Інфо' };
export const SEVERITY_RANK = { critical: 3, warning: 2, info: 1 };

export const STATUS_LABELS = {
  pending: 'в черзі',
  processing: 'обробляється',
  done: 'готово',
  failed: 'помилка',
};

// Бекенд повертає UTC без суфікса часової зони, тому додаємо Z
export function parseDate(value) {
  if (!value) return null;
  return new Date(/Z|[+-]\d\d:?\d\d$/.test(value) ? value : `${value}Z`);
}

export function formatDate(value) {
  const d = parseDate(value);
  return d ? d.toLocaleString('uk-UA', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) : '';
}

export const scoreColor = (score) =>
  score == null ? 'var(--faint)' : score >= 75 ? 'var(--ok)' : score >= 55 ? 'var(--warn)' : 'var(--crit)';
