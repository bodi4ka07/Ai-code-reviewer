import { useState } from 'react';
import { api } from '../api.js';
import CodeView from './CodeView.jsx';
import { Icon } from './Icon.jsx';

const EXTENSIONS = { python: 'py', javascript: 'js', typescript: 'ts' };

// Ім'я для завантаження: fixed_<ім'я файлу з GitHub> або fixed.<розширення мови>
function downloadName(review) {
  const fromUrl = review.github_url ? review.github_url.split('/').pop() : '';
  return fromUrl ? `fixed_${fromUrl}` : `fixed.${EXTENSIONS[review.language] || 'txt'}`;
}

// Виправлений AI варіант файлу: генерується на вимогу, лише показується й завантажується (ніколи не виконується)
export default function FixedCode({ review }) {
  const [fixed, setFixed] = useState(review.fixed_code || '');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const generate = async () => {
    setBusy(true);
    setError('');
    try {
      const res = await api.fixReview(review.id);
      setFixed(res.fixed_code);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const download = () => {
    const url = URL.createObjectURL(new Blob([fixed], { type: 'text/plain;charset=utf-8' }));
    const a = document.createElement('a');
    a.href = url;
    a.download = downloadName(review);
    a.click();
    URL.revokeObjectURL(url);
  };

  if (!fixed) {
    return (
      <div className="card fix-cta">
        <div>
          <h3>Виправлений код</h3>
          <p className="muted small">AI врахує всі зауваження й поверне повний файл. Його можна переглянути, скопіювати або завантажити.</p>
        </div>
        <button className="btn" onClick={generate} disabled={busy}>
          {busy ? <span className="spinner sm" /> : <Icon name="check" />} {busy ? 'Виправляємо…' : 'Показати виправлений код'}
        </button>
        {error && <div className="form-error">{error}</div>}
      </div>
    );
  }

  return (
    <>
      <div className="fix-head">
        <h3 className="section-title" style={{ margin: 0 }}>
          Виправлений код
        </h3>
        <div className="actions">
          <button className="btn sm" onClick={download}>
            Завантажити
          </button>
        </div>
      </div>
      <p className="muted small fix-note">Це пропозиція AI. Перегляньте зміни й перевірте код, перш ніж використовувати.</p>
      <CodeView code={fixed} language={review.language} issues={{}} activeLine={null} fileLabel={downloadName(review)} />
      {error && <div className="form-error">{error}</div>}
    </>
  );
}
