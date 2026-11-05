import { useEffect, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { api } from '../api.js';
import AuthLayout from '../components/AuthLayout.jsx';

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
        <h2>Підтвердження email</h2>
        {!message && !error && (
          <p className="muted">
            <span className="spinner sm" /> Перевіряємо посилання…
          </p>
        )}
        {message && <div className="form-success">{message}</div>}
        {error && <div className="form-error">{error}</div>}
        <div className="forgot center">
          <Link to="/login">{message ? 'Увійти' : 'Повернутися до входу'}</Link>
        </div>
      </div>
    </AuthLayout>
  );
}
