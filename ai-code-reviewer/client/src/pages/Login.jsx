import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../auth.jsx';
import { Icon } from '../components/Icon.jsx';

export default function Login() {
  const { login, register } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState('in');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    setBusy(true);
    try {
      await (mode === 'in' ? login(email, password) : register(email, password));
      navigate('/');
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth">
      <div className="hero">
        <div className="logo" style={{ padding: 0 }}>
          <span className="mark">
            <Icon name="code" />
          </span>{' '}
          AI Code Reviewer
        </div>
        <h1>
          Рев'ю коду <span>за секунди</span>, а не за дні
        </h1>
        <ul>
          <li>
            <Icon name="check" /> Баги, безпека, стиль і продуктивність в одному звіті
          </li>
          <li>
            <Icon name="check" /> Кожна порада з посиланням на PEP 8 або OWASP
          </li>
          <li>
            <Icon name="check" /> Працює на ПК і телефоні з одного коду
          </li>
        </ul>
      </div>

      <div className="auth-form">
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
          <input
            id="password"
            className="input"
            type="password"
            required
            minLength={mode === 'up' ? 8 : undefined}
            autoComplete={mode === 'in' ? 'current-password' : 'new-password'}
            placeholder="Мінімум 8 символів"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />

          {error && <div className="form-error">{error}</div>}
          <button className="btn block" disabled={busy}>
            {busy ? <span className="spinner sm" /> : 'Продовжити'}
          </button>
        </form>
      </div>
    </div>
  );
}
