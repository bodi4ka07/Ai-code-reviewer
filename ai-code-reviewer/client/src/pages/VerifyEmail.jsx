import { useEffect, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { api } from '../api.js';
import AuthLayout from '../components/AuthLayout.jsx';
import { Icon } from '../components/Icon.jsx';

export default function VerifyEmail() {
  const [params] = useSearchParams();
  const token = params.get('token') || '';
  const [message, setMessage] = useState('');
  const [error, setError] = useState(token ? '' : 'У посиланні немає токена. Запросіть новий лист на сторінці входу.');
  const started = useRef(false); // посилання одноразове, тож запит надсилається лише раз (StrictMode викликає ефект двічі)

  useEffect(() => {
    if (!token || started.current) return;
    started.current = true;
    api
      .verifyEmail(token)
      .then((res) => setMessage(res.message))
      .catch((err) => setError(err.message));
  }, [token]);

  return (
    <AuthLayout>
      <div className="card">
        {message ? (
          <div className="verified">
            <span className="big-check">
              <Icon name="check" size={36} />
            </span>
            <h2>Email підтверджено</h2>
            <p className="muted">{message}</p>
            <ol className="next-steps">
              <li>
                <span className="n">1</span>
                <b>Створіть проєкт</b>Згрупуйте файли за мовою.
              </li>
              <li>
                <span className="n">2</span>
                <b>Надішліть код</b>Вставте код або вкажіть файл на GitHub.
              </li>
              <li>
                <span className="n">3</span>
                <b>Отримайте оцінку</b>Проблеми й поради з посиланнями.
              </li>
            </ol>
            <Link to="/login" className="btn block">
              Увійти
            </Link>
          </div>
        ) : (
          <>
            <h2>Підтвердження email</h2>
            {!error && (
              <p className="muted">
                <span className="spinner sm" style={{ borderColor: 'var(--border2)', borderTopColor: 'var(--accent)' }} /> Перевіряємо посилання…
              </p>
            )}
            {error && <div className="form-error">{error}</div>}
            <div className="forgot center">
              <Link to="/login">Повернутися до входу</Link>
            </div>
          </>
        )}
      </div>
    </AuthLayout>
  );
}
