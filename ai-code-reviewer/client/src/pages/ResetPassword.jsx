import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { api } from '../api.js';
import PasswordInput from '../components/PasswordInput.jsx';
import AuthLayout from '../components/AuthLayout.jsx';
import PasswordStrength from '../components/PasswordStrength.jsx';
import Steps from '../components/Steps.jsx';

export default function ResetPassword() {
  const [params] = useSearchParams();
  const token = params.get('token') || '';
  const [password, setPassword] = useState('');
  const [repeat, setRepeat] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState(token ? '' : 'У посиланні немає токена. Запросіть нове посилання.');
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    if (password !== repeat) {
      setError('Паролі не збігаються');
      return;
    }
    setBusy(true);
    try {
      const res = await api.resetPassword(token, password);
      setMessage(res.message);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthLayout>
      <form className="card" onSubmit={submit}>
        <Steps current={message ? 3 : 2} />
        <h2>Новий пароль</h2>
        <p className="muted">Придумайте новий пароль для входу.</p>

        {message ? (
          <>
            <div className="form-success">{message}</div>
            <Link to="/login" className="btn block">
              Увійти
            </Link>
          </>
        ) : (
          <>
            <label htmlFor="password">Новий пароль</label>
            <PasswordInput
              id="password"
              required
              minLength={8}
              autoComplete="new-password"
              placeholder="Мінімум 8 символів"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            <PasswordStrength password={password} />
            <label htmlFor="repeat">Повторіть пароль</label>
            <PasswordInput
              id="repeat"
              required
              minLength={8}
              autoComplete="new-password"
              value={repeat}
              onChange={(e) => setRepeat(e.target.value)}
            />
            {error && <div className="form-error">{error}</div>}
            <button className="btn block" disabled={busy || !token}>
              {busy ? <span className="spinner sm" /> : 'Змінити пароль'}
            </button>
            {error && !token && (
              <div className="forgot center">
                <Link to="/forgot-password">Запросити нове посилання</Link>
              </div>
            )}
          </>
        )}
      </form>
    </AuthLayout>
  );
}
