import { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { api } from '../api.js';
import { useAuth } from '../auth.jsx';
import PasswordInput from '../components/PasswordInput.jsx';
import PasswordStrength from '../components/PasswordStrength.jsx';
import AuthLayout from '../components/AuthLayout.jsx';

const GITHUB_ERRORS = {
  denied: 'Вхід через GitHub скасовано.',
  state: 'Не вдалося підтвердити запит на вхід через GitHub. Спробуйте ще раз.',
  no_email: 'У вашому GitHub-акаунті немає підтвердженої електронної пошти. Підтвердіть її на GitHub або зареєструйтесь за email.',
  inactive: 'Цей акаунт вимкнено.',
};
const GITHUB_ERROR_DEFAULT = 'Не вдалося увійти через GitHub. Спробуйте ще раз.';

const GithubMark = () => (
  <svg aria-hidden="true" width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
    <path d="M12 .5a11.5 11.5 0 0 0-3.64 22.4c.58.1.79-.25.79-.56v-2c-3.2.7-3.88-1.37-3.88-1.37-.52-1.33-1.28-1.69-1.28-1.69-1.04-.71.08-.7.08-.7 1.15.08 1.76 1.19 1.76 1.19 1.03 1.76 2.7 1.25 3.36.96.1-.75.4-1.25.73-1.54-2.55-.29-5.24-1.28-5.24-5.69 0-1.26.45-2.28 1.19-3.09-.12-.29-.52-1.46.11-3.05 0 0 .97-.31 3.17 1.18a11 11 0 0 1 5.77 0c2.2-1.49 3.17-1.18 3.17-1.18.63 1.59.23 2.76.11 3.05.74.81 1.19 1.83 1.19 3.09 0 4.42-2.69 5.39-5.25 5.68.41.36.78 1.06.78 2.14v3.17c0 .31.21.67.8.56A11.5 11.5 0 0 0 12 .5z" />
  </svg>
);

export default function Login() {
  const { login, register } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState('in');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');
  const [needsVerify, setNeedsVerify] = useState(false); // акаунт створено, але email ще не підтверджено
  const [busy, setBusy] = useState(false);
  const [github, setGithub] = useState(false); // чи налаштовано вхід через GitHub на сервері
  const [params] = useSearchParams();

  useEffect(() => {
    api
      .providers()
      .then((p) => setGithub(Boolean(p.github)))
      .catch(() => setGithub(false));
  }, []);

  // Повернення з GitHub із помилкою: ?github_error=<код>
  useEffect(() => {
    const code = params.get('github_error');
    if (code) setError(GITHUB_ERRORS[code] || GITHUB_ERROR_DEFAULT);
  }, [params]);

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    setInfo('');
    if (mode === 'up' && password !== confirm) {
      setError('Паролі не збігаються');
      return;
    }
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
        setConfirm('');
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
    <AuthLayout mode={mode}>
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

        {github && (
          <>
            <a className="btn ghost block github-btn" href="/api/auth/github/login">
              <GithubMark /> Продовжити з GitHub
            </a>
            <div className="or-divider">
              <span>або за email</span>
            </div>
          </>
        )}

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
        {mode === 'up' && <PasswordStrength password={password} />}
        {mode === 'up' && (
          <>
            <label htmlFor="confirm">Повторіть пароль</label>
            <PasswordInput
              id="confirm"
              required
              autoComplete="new-password"
              placeholder="Введіть пароль ще раз"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
            />
          </>
        )}
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
