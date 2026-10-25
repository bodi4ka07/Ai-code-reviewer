import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api } from '../api.js';
import { ScoreRing } from '../components/Charts.jsx';
import CodeView from '../components/CodeView.jsx';
import CommentCard from '../components/CommentCard.jsx';
import { Icon } from '../components/Icon.jsx';
import { CATEGORIES, languageLabel, SEVERITY_RANK } from '../utils.js';

const POLL_MS = 2000;
const STEPS = [
  ['Прийнято в чергу', 'Задачу поставлено на обробку'],
  ['Статичний аналіз і пошук по документації', 'Лінтер та RAG по стандартах'],
  ['Аналіз Gemini', 'Формування звіту'],
  ["Рев'ю готове", 'Результат збережено'],
];

function Progress({ status }) {
  const current = status === 'pending' ? 0 : 1; // 1 і 2 виконуються у фоні разом
  return (
    <div className="card progress">
      <h3>Статус рев'ю</h3>
      <p className="muted small">Оновлюється автоматично</p>
      <div className="stepper">
        {STEPS.map(([title, text], i) => {
          const cls = i < current ? 'complete' : i === current || (current === 1 && i === 2) ? 'active' : '';
          return (
            <div key={title} className={`step ${cls}`}>
              <div className="ic">{cls === 'complete' ? <Icon name="check" size={14} /> : i + 1}</div>
              <div>
                <b>{title}</b>
                <span>{text}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function Review() {
  const { id } = useParams();
  const [review, setReview] = useState(null);
  const [error, setError] = useState('');
  const [filter, setFilter] = useState('all');
  const [activeLine, setActiveLine] = useState(null);
  const [selected, setSelected] = useState(null);

  const active = review && (review.status === 'pending' || review.status === 'processing');

  useEffect(() => {
    let cancelled = false;
    let timer;
    const load = async () => {
      try {
        const data = await api.review(id);
        if (cancelled) return;
        setReview(data);
        if (data.status === 'pending' || data.status === 'processing') timer = setTimeout(load, POLL_MS);
      } catch (e) {
        if (!cancelled) setError(e.message);
      }
    };
    load();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [id]);

  // Найсерйозніша проблема на кожному рядку для підсвітки в коді
  const issues = useMemo(() => {
    const map = {};
    for (const c of review?.comments || []) {
      if (c.line_number == null) continue;
      const cur = map[c.line_number];
      if (!cur || SEVERITY_RANK[c.severity] > SEVERITY_RANK[cur]) map[c.line_number] = c.severity;
    }
    return map;
  }, [review]);

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
  if (!review) {
    return (
      <div className="splash">
        <span className="spinner" />
      </div>
    );
  }

  const comments = review.comments;
  const counts = Object.fromEntries(Object.keys(CATEGORIES).map((k) => [k, comments.filter((c) => c.category === k).length]));
  const visible = comments.filter((c) => filter === 'all' || c.category === filter);
  const back = `/projects/${review.project_id}`;

  const select = (line, commentId) => {
    setActiveLine(line);
    setSelected(commentId);
  };

  return (
    <>
      <div className="page-head">
        <div>
          <div className="crumb">
            <Link to={back}>Проєкт</Link> <Icon name="chevron" size={14} /> Рев'ю
          </div>
          <h1>
            Результат рев'ю{' '}
            <span className={`badge ${review.status}`}>
              <span className="dot" />
              {{ pending: 'в черзі', processing: 'обробляється', done: 'готово', failed: 'помилка' }[review.status]}
            </span>
          </h1>
        </div>
        <Link to={`${back}/new`} className="btn ghost">
          Нове рев'ю
        </Link>
      </div>

      {active && <Progress status={review.status} />}

      {review.status === 'failed' && (
        <div className="card failed">
          <h3>Не вдалося виконати рев'ю</h3>
          <p>{review.error_message || 'Невідома помилка.'}</p>
          <Link to={`${back}/new`} className="btn">
            Спробувати ще раз
          </Link>
        </div>
      )}

      {review.status === 'done' && (
        <>
          <div className="card summary">
            <ScoreRing score={review.overall_score} />
            <div>
              <h3>Підсумок</h3>
              <p className="muted">{review.summary}</p>
              <div className="chips">
                {Object.entries(CATEGORIES).map(([k, label]) =>
                  counts[k] ? (
                    <span key={k} className={`badge ${k}`}>
                      {label} · {counts[k]}
                    </span>
                  ) : null,
                )}
                {comments.length === 0 && <span className="badge done">Проблем не знайдено</span>}
              </div>
            </div>
          </div>

          <div className="split">
            <div className="sticky">
              {review.code_snippet ? (
                <CodeView
                  code={review.code_snippet}
                  language={review.language}
                  issues={issues}
                  activeLine={activeLine}
                  fileLabel={review.github_url ? review.github_url.split('/').pop() : languageLabel(review.language)}
                />
              ) : (
                <div className="card empty">Код недоступний</div>
              )}
            </div>
            <div>
              <div className="filters">
                <button className={`chip${filter === 'all' ? ' on' : ''}`} onClick={() => setFilter('all')}>
                  Усі <em>{comments.length}</em>
                </button>
                {Object.entries(CATEGORIES).map(([k, label]) => (
                  <button key={k} className={`chip${filter === k ? ' on' : ''}`} onClick={() => setFilter(k)}>
                    {label} <em>{counts[k]}</em>
                  </button>
                ))}
              </div>
              {visible.map((c) => (
                <CommentCard
                  key={c.id}
                  comment={c}
                  reviewId={review.id}
                  selected={selected === c.id}
                  onSelect={(line) => select(line, c.id)}
                />
              ))}
              {visible.length === 0 && <div className="empty">Немає коментарів</div>}
            </div>
          </div>
        </>
      )}
    </>
  );
}
