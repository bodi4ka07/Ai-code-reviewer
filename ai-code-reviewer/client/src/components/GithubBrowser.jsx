import { useState } from 'react';
import { Icon } from './Icon.jsx';

// Вибір файлу з публічних репозиторіїв GitHub. Запити йдуть з браузера до api.github.com без токена,
// тож приватні репозиторії недоступні (їх код вставляють вручну), а сервер нічого додатково не отримує.
const API = 'https://api.github.com';
const NAME_RE = /^[A-Za-z0-9-]{1,39}$/;
const REPO_RE = /^[A-Za-z0-9._-]{1,100}$/;
// Повний аналіз (лінтер + AI) для цих розширень; решта файлів з кодом перевіряється лише AI
const FULL_EXT = /\.(py|js|jsx|mjs|cjs|ts|tsx)$/i;
const OTHER_EXT = /\.(java|kt|kts|cs|go|rs|rb|php|c|h|cc|cpp|hpp|swift|dart|scala|lua|sh|ps1|sql|html|css|scss|vue|svelte|r|m|pl)$/i;
const isCode = (path) => FULL_EXT.test(path) || OTHER_EXT.test(path);
const SKIP_DIRS = new Set(['node_modules', 'dist', 'build', 'vendor', '__pycache__', '.git', 'venv', '.venv']);
const MAX_BYTES = 40000; // файл довший за ліміт символів сервер однаково відхилить
const MAX_SHOWN = 200;

async function github(path) {
  let res;
  try {
    res = await fetch(`${API}${path}`, { headers: { Accept: 'application/vnd.github+json' } });
  } catch {
    throw new Error("Не вдалося зв'язатися з GitHub. Перевірте інтернет.");
  }
  if (res.status === 404) throw new Error('Не знайдено. Перевірте назву: приватні репозиторії недоступні.');
  if (res.status === 403 || res.status === 429) {
    throw new Error('Перевищено ліміт запитів GitHub (60 на годину). Спробуйте пізніше або вставте посилання вручну.');
  }
  if (!res.ok) throw new Error(`GitHub повернув помилку (${res.status}).`);
  return res.json();
}

const sizeLabel = (bytes) => (bytes < 1024 ? `${bytes} Б` : `${(bytes / 1024).toFixed(1)} КБ`);

export default function GithubBrowser({ selectedUrl, onPick }) {
  const [query, setQuery] = useState('');
  const [repos, setRepos] = useState(null);
  const [repo, setRepo] = useState(null);
  const [files, setFiles] = useState(null);
  const [filter, setFilter] = useState('');
  const [note, setNote] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const openRepo = async (owner, name, knownRepo) => {
    setBusy(true);
    setError('');
    setNote('');
    try {
      const info = knownRepo || (await github(`/repos/${owner}/${name}`));
      const tree = await github(`/repos/${info.full_name}/git/trees/${encodeURIComponent(info.default_branch)}?recursive=1`);
      const list = (tree.tree || [])
        .filter((n) => n.type === 'blob' && isCode(n.path) && !n.path.split('/').some((p) => SKIP_DIRS.has(p)))
        .filter((n) => (n.size ?? 0) <= MAX_BYTES)
        .map((n) => ({ path: n.path, size: n.size ?? 0, full: FULL_EXT.test(n.path) }))
        .sort((a, b) => Number(b.full) - Number(a.full) || a.path.localeCompare(b.path)); // спершу файли з повним аналізом
      setRepo(info);
      setFiles(list);
      setFilter('');
      if (tree.truncated) setNote('Репозиторій дуже великий, показано лише частину файлів. Решту можна вказати посиланням.');
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const back = () => {
    setRepo(null);
    setFiles(null);
    setNote('');
  };

  // Це не <form>: компонент стоїть усередині форми рев'ю, а вкладені форми в HTML не працюють
  const search = async () => {
    const value = query.trim().replace(/^https?:\/\/github\.com\//i, '').replace(/\/+$/, '');
    setError('');
    setRepo(null);
    setFiles(null);
    setRepos(null);
    const [owner, name] = value.split('/');
    if (!NAME_RE.test(owner || '')) {
      setError("Вкажіть ім'я користувача або організації GitHub, наприклад octocat, або owner/repo.");
      return;
    }
    if (name !== undefined) {
      if (!REPO_RE.test(name)) {
        setError('Некоректна назва репозиторію.');
        return;
      }
      await openRepo(owner, name);
      return;
    }
    setBusy(true);
    try {
      const list = await github(`/users/${owner}/repos?per_page=100&sort=updated`);
      setRepos(list);
      if (list.length === 0) setError('У цього акаунта немає публічних репозиторіїв.');
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const shown = (files || []).filter((f) => f.path.toLowerCase().includes(filter.trim().toLowerCase()));
  const fileUrl = (path) => `https://github.com/${repo.full_name}/blob/${repo.default_branch}/${path}`;

  return (
    <div className="gh-browser">
      <div className="gh-head">
        <b>Знайти файл у GitHub</b>
        <span className="muted small">лише публічні репозиторії</span>
      </div>
      <div className="gh-search">
        <input
          className="input"
          aria-label="Користувач, організація або owner/repo"
          placeholder="Користувач GitHub або owner/repo"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault(); // Enter не має надсилати зовнішню форму
              if (!busy && query.trim()) search();
            }
          }}
        />
        <button type="button" className="btn ghost sm" onClick={search} disabled={busy || !query.trim()}>
          {busy ? <span className="spinner sm" style={{ borderColor: 'var(--border2)', borderTopColor: 'var(--accent)' }} /> : 'Знайти'}
        </button>
      </div>
      {error && <div className="form-error">{error}</div>}

      {repos && !repo && repos.length > 0 && (
        <ul className="gh-list" aria-label="Репозиторії">
          {repos.map((r) => (
            <li key={r.id}>
              <button type="button" className="gh-item" onClick={() => openRepo(r.owner.login, r.name, r)}>
                <span className="gh-name">{r.name}</span>
                <span className="muted small gh-meta">{[r.language, r.description].filter(Boolean).join(' · ') || 'Без опису'}</span>
              </button>
            </li>
          ))}
        </ul>
      )}

      {repo && files && (
        <>
          <div className="gh-repo">
            <button type="button" className="link" onClick={back}>
              ← Репозиторії
            </button>
            <b>{repo.full_name}</b>
            <span className="muted small">{repo.default_branch}</span>
          </div>
          {note && (
            <div className="muted small" style={{ marginBottom: 8 }}>
              {note}
            </div>
          )}
          <input
            className="input"
            aria-label="Фільтр файлів"
            placeholder={`Фільтр серед ${files.length} файлів`}
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          />
          <ul className="gh-list" aria-label="Файли">
            {shown.slice(0, MAX_SHOWN).map((f) => {
              const url = fileUrl(f.path);
              return (
                <li key={f.path}>
                  <button type="button" className={`gh-item file${selectedUrl === url ? ' on' : ''}`} onClick={() => onPick(url)}>
                    <span className="gh-name mono">{f.path}</span>
                    {!f.full && (
                      <span className="gh-tag" title="Для цієї мови лише AI-аналіз, без статичного лінтера">
                        лише AI
                      </span>
                    )}
                    <span className="muted small">{sizeLabel(f.size)}</span>
                    {selectedUrl === url && <Icon name="check" size={16} />}
                  </button>
                </li>
              );
            })}
            {shown.length === 0 && <li className="empty small">Файлів з кодом не знайдено</li>}
            {shown.length > MAX_SHOWN && (
              <li className="muted small gh-more">
                Показано {MAX_SHOWN} з {shown.length}, уточніть фільтр
              </li>
            )}
          </ul>
        </>
      )}
    </div>
  );
}
