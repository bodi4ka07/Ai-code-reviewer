import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth.jsx';
import AuthLayout from '../components/AuthLayout.jsx';

// Сюди GitHub-вхід повертає користувача: токен лежить у фрагменті адреси (#token=...), тож до сервера й логів він не потрапляє
export default function GithubCallback() {
  const { loginWithToken } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState('');
  const started = useRef(false); // StrictMode викликає ефект двічі

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    const token = new URLSearchParams(window.location.hash.slice(1)).get('token');
    window.history.replaceState(null, '', window.location.pathname); // токен не лишається в адресному рядку та історії
    if (!token) {
      setError('Не вдалося завершити вхід через GitHub. Спробуйте ще раз.');
      return;
    }
    loginWithToken(token)
      .then(() => navigate('/', { replace: true }))
      .catch(() => setError('Не вдалося завершити вхід через GitHub. Спробуйте ще раз.'));
  }, [loginWithToken, navigate]);

  return (
    <AuthLayout mode="in">
      <div className="card">
        <h2>Вхід через GitHub</h2>
        {error ? (
          <>
            <div className="form-error">{error}</div>
            <div className="forgot center">
              <Link to="/login">Повернутися до входу</Link>
            </div>
          </>
        ) : (
          <p className="muted">
            <span className="spinner sm" style={{ borderColor: 'var(--border2)', borderTopColor: 'var(--accent)' }} /> Завершуємо вхід…
          </p>
        )}
      </div>
    </AuthLayout>
  );
}
