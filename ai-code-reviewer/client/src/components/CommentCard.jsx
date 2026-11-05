import { useState } from 'react';
import { api } from '../api.js';
import { CATEGORIES, SEVERITIES } from '../utils.js';
import { Icon } from './Icon.jsx';
import StreamedMarkdown from './StreamedMarkdown.jsx';
import InlineCode from './InlineCode.jsx';

// questions: уже збережені питання та відповіді саме до цього коментаря
export default function CommentCard({ comment, reviewId, questions, selected, onSelect, onAsked }) {
  const [question, setQuestion] = useState('');
  const [error, setError] = useState('');
  const [asking, setAsking] = useState(false);
  const [freshId, setFreshId] = useState(null); // щойно отримана відповідь показується поступово

  const ask = async (e) => {
    e.preventDefault();
    const text = question.trim();
    if (!text) return;
    setAsking(true);
    setError('');
    try {
      const saved = await api.ask(reviewId, text, comment.id);
      setFreshId(saved.id);
      onAsked(saved);
      setQuestion('');
    } catch (err) {
      setError(err.message);
    } finally {
      setAsking(false);
    }
  };

  const stop = (e) => e.stopPropagation();

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
      <p>
        <InlineCode>{comment.message}</InlineCode>
      </p>
      <div className="tip">
        💡 <InlineCode>{comment.suggestion}</InlineCode>
      </div>
      {comment.reference && (
        <div className="ref">
          <Icon name="book" size={14} />
          {comment.reference}
        </div>
      )}

      {questions.length > 0 && (
        <div className="qa" onClick={stop}>
          {questions.map((q) => (
            <div key={q.id} className="qa-item">
              <div className="qa-q">{q.question}</div>
              <div className="answer">
                <StreamedMarkdown animate={q.id === freshId}>{q.answer}</StreamedMarkdown>
              </div>
            </div>
          ))}
        </div>
      )}

      <form className="ask" onSubmit={ask} onClick={stop}>
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
    </div>
  );
}
