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

// Українська множина: 1 рядок, 2 рядки, 5 рядків
export function plural(n, one, few, many) {
  const m10 = n % 10;
  const m100 = n % 100;
  if (m10 === 1 && m100 !== 11) return one;
  if (m10 >= 2 && m10 <= 4 && (m100 < 12 || m100 > 14)) return few;
  return many;
}

// Копіює текст у буфер обміну; на небезпечному (http) origin, де clipboard API недоступний, використовує запасний спосіб
export async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    const area = document.createElement('textarea');
    area.value = text;
    area.style.position = 'fixed';
    area.style.opacity = '0';
    document.body.appendChild(area);
    area.select();
    let ok = false;
    try {
      ok = document.execCommand('copy');
    } catch {
      ok = false;
    }
    area.remove();
    return ok;
  }
}

export const scoreColor = (score) =>
  score == null ? 'var(--faint)' : score >= 75 ? 'var(--ok)' : score >= 55 ? 'var(--warn)' : 'var(--crit)';
