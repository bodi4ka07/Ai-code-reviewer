import { useState } from 'react';
import { api } from '../api.js';
import { CATEGORIES, SEVERITIES } from '../utils.js';
import { Icon } from './Icon.jsx';

export default function CommentCard({ comment, reviewId, selected, onSelect }) {
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState('');
  const [error, setError] = useState('');
  const [asking, setAsking] = useState(false);

  const ask = async (e) => {
    e.preventDefault();
    if (!question.trim()) return;
    setAsking(true);
    setError('');
    try {
      const res = await api.ask(reviewId, question.trim(), comment.id);
      setAnswer(res.answer);
    } catch (err) {
      setError(err.message);
    } finally {
      setAsking(false);
    }
  };

  return (
    <div
      className={`card comment ${comment.category}${selected ? ' sel' : ''}`}
      onClick={() => onSelect(comment.line_number)}
    >
      <div className="top">
        <span className={`badge ${comment.category}`}>
          <Icon name={comment.category} size={13} />
          {CATEGORIES[comment.category]}
        </span>
        <span className={`badge ${comment.severity}`}>
          <span className="dot" />
          {SEVERITIES[comment.severity]}
        </span>
        {comment.line_number != null && <span className="line mono">рядок {comment.line_number}</span>}
      </div>
      <p>{comment.message}</p>
      <div className="tip">💡 {comment.suggestion}</div>
      {comment.reference && (
        <div className="ref">
          <Icon name="book" size={14} />
          {comment.reference}
        </div>
      )}

      <form className="ask" onSubmit={ask} onClick={(e) => e.stopPropagation()}>
        <input
          className="input"
          placeholder="Запитати AI: чому це погано? покажи виправлений варіант"
          value={question}
          maxLength={1000}
          onChange={(e) => setQuestion(e.target.value)}
        />
        <button className="btn sm" disabled={asking || !question.trim()}>
          {asking ? <span className="spinner sm" /> : 'Запитати'}
        </button>
      </form>
      {error && <div className="form-error">{error}</div>}
      {answer && (
        <div className="answer" onClick={(e) => e.stopPropagation()}>
          {answer}
        </div>
      )}
    </div>
  );
}
