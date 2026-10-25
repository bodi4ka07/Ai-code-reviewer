import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { api } from '../api.js';
import { Icon } from '../components/Icon.jsx';
import { LANGUAGES, languageLabel } from '../utils.js';

const MAX_CHARS = 20000;

export default function NewReview() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [project, setProject] = useState(null);
  const [tab, setTab] = useState('paste');
  const [code, setCode] = useState('');
  const [url, setUrl] = useState('');
  const [language, setLanguage] = useState('auto');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.project(id).then(setProject).catch((e) => setError(e.message));
  }, [id]);

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    const body = { project_id: id };
    if (tab === 'paste') body.code_snippet = code;
    else body.github_url = url.trim();
    if (language !== 'auto') body.language = language;

    setBusy(true);
    try {
      const review = await api.createReview(body);
      navigate(`/reviews/${review.id}`);
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  };

  const empty = tab === 'paste' ? !code.trim() : !url.trim();

  return (
    <>
      <div className="page-head">
        <div>
          <div className="crumb">
            <Link to={`/projects/${id}`}>{project ? project.name : 'Проєкт'}</Link> <Icon name="chevron" size={14} /> Нове рев'ю
          </div>
          <h1>Надіслати код на рев'ю</h1>
        </div>
      </div>

      <form className="card" onSubmit={submit}>
        <div className="tabs">
          <button type="button" className={tab === 'paste' ? 'on' : ''} onClick={() => setTab('paste')}>
            <Icon name="code" /> Вставити код
          </button>
          <button type="button" className={tab === 'url' ? 'on' : ''} onClick={() => setTab('url')}>
            <Icon name="link" /> Посилання на GitHub
          </button>
        </div>

        {tab === 'paste' ? (
          <>
            <textarea
              className="input code-input"
              spellCheck="false"
              placeholder="Вставте код для перевірки"
              maxLength={MAX_CHARS}
              value={code}
              onChange={(e) => setCode(e.target.value)}
            />
            <div className="muted small">
              {code.length} / {MAX_CHARS} символів
            </div>
          </>
        ) : (
          <>
            <label htmlFor="ghurl" style={{ marginTop: 0 }}>
              URL файлу
            </label>
            <input
              id="ghurl"
              className="input mono"
              placeholder="https://github.com/owner/repo/blob/main/app/main.py"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
            />
            <div className="muted small">Підтримуються лише публічні файли з github.com. Для приватних вставте код вручну.</div>
          </>
        )}

        <label htmlFor="lang">Мова коду</label>
        <select id="lang" className="input narrow" value={language} onChange={(e) => setLanguage(e.target.value)}>
          <option value="auto">
            Авто{project ? ` (${languageLabel(project.language)} або за розширенням файлу)` : ''}
          </option>
          {LANGUAGES.map((l) => (
            <option key={l.value} value={l.value}>
              {l.label}
            </option>
          ))}
        </select>

        {error && <div className="form-error">{error}</div>}
        <button className="btn" disabled={busy || empty}>
          {busy ? <span className="spinner sm" /> : <Icon name="send" />} Надіслати
        </button>
      </form>
    </>
  );
}
