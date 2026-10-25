import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { api } from '../api.js';
import { AreaChart, Donut } from '../components/Charts.jsx';
import { Icon } from '../components/Icon.jsx';
import { CATEGORIES, formatDate, languageLabel, scoreColor, STATUS_LABELS } from '../utils.js';

export default function Project() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    Promise.all([api.project(id), api.projectStats(id), api.projectReviews(id)])
      .then(([project, stats, reviews]) => !cancelled && setData({ project, stats, reviews }))
      .catch((e) => !cancelled && setError(e.message));
    return () => {
      cancelled = true;
    };
  }, [id]);

  const remove = async () => {
    if (!window.confirm(`Видалити проєкт «${data.project.name}» разом з усіма рев'ю?`)) return;
    try {
      await api.deleteProject(id);
      navigate('/');
    } catch (err) {
      setError(err.message);
    }
  };

  if (error) {
    return (
      <div className="card">
        <div className="form-error">{error}</div>
        <Link to="/" className="btn ghost">
          До проєктів
        </Link>
      </div>
    );
  }
  if (!data) {
    return (
      <div className="splash">
        <span className="spinner" />
      </div>
    );
  }

  const { project, stats, reviews } = data;
  const issues = stats.categories.reduce((a, c) => a + c.count, 0);

  return (
    <>
      <div className="page-head">
        <div>
          <div className="crumb">
            <Link to="/">Проєкти</Link> <Icon name="chevron" size={14} /> {project.name}
          </div>
          <h1>{project.name}</h1>
          <p className="muted">
            {languageLabel(project.language)}
            {project.description ? ` · ${project.description}` : ''}
          </p>
        </div>
        <div className="actions">
          <button className="btn ghost" onClick={remove}>
            <Icon name="trash" /> Видалити
          </button>
          <Link to={`/projects/${id}/new`} className="btn">
            <Icon name="plus" /> Нове рев'ю
          </Link>
        </div>
      </div>

      <div className="kpis">
        <div className="card kpi">
          <div className="muted">Середня оцінка</div>
          <div className="v" style={{ color: scoreColor(stats.average_score) }}>
            {stats.average_score != null ? Math.round(stats.average_score) : '—'}
          </div>
        </div>
        <div className="card kpi">
          <div className="muted">Рев'ю</div>
          <div className="v">{stats.total_reviews}</div>
        </div>
        <div className="card kpi">
          <div className="muted">Завершено</div>
          <div className="v">{stats.completed_reviews}</div>
        </div>
        <div className="card kpi">
          <div className="muted">Знайдено проблем</div>
          <div className="v">{issues}</div>
        </div>
      </div>

      <div className="two">
        <div className="card">
          <h3>Динаміка оцінки</h3>
          <p className="muted small">Останні завершені рев'ю</p>
          <AreaChart history={stats.score_history} />
        </div>
        <div className="card">
          <h3>За категоріями</h3>
          <p className="muted small">Розподіл проблем</p>
          <Donut categories={stats.categories} labels={CATEGORIES} />
        </div>
      </div>

      <div className="card history">
        <h3>Історія рев'ю</h3>
        {reviews.length === 0 ? (
          <div className="empty">Рев'ю ще немає. Надішліть перший код на перевірку.</div>
        ) : (
          <div className="scroll-x">
            <table>
              <thead>
                <tr>
                  <th>Дата</th>
                  <th>Мова</th>
                  <th>Оцінка</th>
                  <th>Статус</th>
                </tr>
              </thead>
              <tbody>
                {reviews.map((r) => (
                  <tr key={r.id} onClick={() => navigate(`/reviews/${r.id}`)}>
                    <td>{formatDate(r.created_at)}</td>
                    <td>{languageLabel(r.language)}</td>
                    <td style={{ fontWeight: 700, color: scoreColor(r.overall_score) }}>{r.overall_score ?? '—'}</td>
                    <td>
                      <span className={`badge ${r.status}`}>
                        <span className="dot" />
                        {STATUS_LABELS[r.status]}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
