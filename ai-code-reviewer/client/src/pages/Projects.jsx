import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../api.js';
import { Icon } from '../components/Icon.jsx';
import { LANGUAGES, languageLabel, scoreColor } from '../utils.js';

export default function Projects() {
  const navigate = useNavigate();
  const [projects, setProjects] = useState(null);
  const [stats, setStats] = useState({});
  const [error, setError] = useState('');
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ name: '', description: '', language: 'python' });
  const [formError, setFormError] = useState('');

  useEffect(() => {
    let cancelled = false;
    api
      .projects()
      .then(async (list) => {
        if (cancelled) return;
        setProjects(list);
        // Статистика для карток: помилка по одному проєкту не ламає список
        const entries = await Promise.all(list.map((p) => api.projectStats(p.id).then((s) => [p.id, s]).catch(() => [p.id, null])));
        if (!cancelled) setStats(Object.fromEntries(entries));
      })
      .catch((e) => !cancelled && setError(e.message));
    return () => {
      cancelled = true;
    };
  }, []);

  const create = async (e) => {
    e.preventDefault();
    setFormError('');
    try {
      const project = await api.createProject({
        name: form.name.trim(),
        description: form.description.trim() || null,
        language: form.language,
      });
      navigate(`/projects/${project.id}`);
    } catch (err) {
      setFormError(err.message);
    }
  };

  const remove = async (e, project) => {
    e.preventDefault();
    e.stopPropagation();
    if (!window.confirm(`Видалити проєкт «${project.name}» разом з усіма рев'ю?`)) return;
    try {
      await api.deleteProject(project.id);
      setProjects((list) => list.filter((p) => p.id !== project.id));
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Проєкти</h1>
          <p className="muted">Оберіть проєкт, щоб побачити історію та статистику</p>
        </div>
        <button className="btn" onClick={() => setCreating((v) => !v)}>
          <Icon name="plus" /> Новий проєкт
        </button>
      </div>

      {error && <div className="form-error">{error}</div>}

      {creating && (
        <form className="card create-form" onSubmit={create}>
          <div className="row2">
            <div>
              <label htmlFor="pname">Назва</label>
              <input id="pname" className="input" required maxLength={255} autoFocus value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </div>
            <div>
              <label htmlFor="plang">Мова за замовчуванням</label>
              <select id="plang" className="input" value={form.language} onChange={(e) => setForm({ ...form, language: e.target.value })}>
                {LANGUAGES.map((l) => (
                  <option key={l.value} value={l.value}>
                    {l.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <label htmlFor="pdesc">Опис (необов'язково)</label>
          <input id="pdesc" className="input" maxLength={1000} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          {formError && <div className="form-error">{formError}</div>}
          <button className="btn">Створити</button>
        </form>
      )}

      {projects === null && !error ? (
        <div className="splash">
          <span className="spinner" />
        </div>
      ) : (
        <div className="grid g3">
          {(projects || []).map((p) => {
            const s = stats[p.id];
            const avg = s && s.average_score != null ? Math.round(s.average_score) : null;
            return (
              <Link key={p.id} to={`/projects/${p.id}`} className="card proj">
                <div className="row">
                  <div>
                    <b className="proj-name">{p.name}</b>
                    <div className="muted small">{p.description || 'Без опису'}</div>
                  </div>
                  <span className="lang">{languageLabel(p.language)}</span>
                </div>
                <div className="meta">
                  <div>
                    <div className="big" style={{ color: scoreColor(avg) }}>
                      {avg ?? '—'}
                    </div>
                    <div className="muted small">{s ? `${s.total_reviews} рев'ю` : ' '}</div>
                  </div>
                  <button className="icon-btn" title="Видалити проєкт" onClick={(e) => remove(e, p)}>
                    <Icon name="trash" />
                  </button>
                </div>
              </Link>
            );
          })}
          {projects && projects.length === 0 && (
            <div className="empty card">Проєктів ще немає. Створіть перший, щоб надіслати код на рев'ю.</div>
          )}
        </div>
      )}
    </>
  );
}
