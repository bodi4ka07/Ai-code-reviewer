import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../api.js';
import { useAuth } from '../auth.jsx';
import PasswordInput from '../components/PasswordInput.jsx';
import AuthLayout from '../components/AuthLayout.jsx';

export default function Login() {
  const { login, register } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState('in');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');
  const [needsVerify, setNeedsVerify] = useState(false); // акаунт створено, але email ще не підтверджено
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    setInfo('');
    setBusy(true);
    try {
      if (mode === 'in') {
        await login(email, password);
        navigate('/');
      } else if (await register(email, password)) {
        setNeedsVerify(true);
        setInfo(`Ми надіслали лист на ${email}. Перейдіть за посиланням у ньому, щоб завершити реєстрацію.`);
        setMode('in');
        setPassword('');
      } else {
        navigate('/');
      }
    } catch (err) {
      setError(err.message);
      setNeedsVerify(err.status === 403);
    } finally {
      setBusy(false);
    }
  };

  const resend = async () => {
    setError('');
    setBusy(true);
    try {
      const res = await api.resendVerification(email.trim());
      setInfo(res.message);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthLayout>
      <form className="card" onSubmit={submit}>
        <h2>{mode === 'in' ? 'З поверненням' : 'Створити акаунт'}</h2>
        <p className="muted">Увійдіть, щоб продовжити</p>
        <div className="seg">
          <button type="button" className={mode === 'in' ? 'on' : ''} onClick={() => setMode('in')}>
            Вхід
          </button>
          <button type="button" className={mode === 'up' ? 'on' : ''} onClick={() => setMode('up')}>
            Реєстрація
          </button>
        </div>

        <label htmlFor="email">Email</label>
        <input
          id="email"
          className="input"
          type="email"
          required
          autoComplete="email"
          placeholder="you@example.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <label htmlFor="password">Пароль</label>
        <PasswordInput
          id="password"
          required
          minLength={mode === 'up' ? 8 : undefined}
          autoComplete={mode === 'in' ? 'current-password' : 'new-password'}
          placeholder="Мінімум 8 символів"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        {mode === 'in' && (
          <div className="forgot">
            <Link to="/forgot-password">Забули пароль?</Link>
          </div>
        )}

        {info && <div className="form-success">{info}</div>}
        {error && <div className="form-error">{error}</div>}
        {needsVerify && (
          <button type="button" className="btn ghost block" disabled={busy || !email} onClick={resend}>
            Надіслати лист ще раз
          </button>
        )}
        <button className="btn block" disabled={busy}>
          {busy ? <span className="spinner sm" /> : 'Продовжити'}
        </button>
      </form>
    </AuthLayout>
  );
}
