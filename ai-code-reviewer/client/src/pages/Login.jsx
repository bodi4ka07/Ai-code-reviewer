import { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { api } from '../api.js';
import { useAuth } from '../auth.jsx';
import PasswordInput from '../components/PasswordInput.jsx';
import PasswordStrength from '../components/PasswordStrength.jsx';
import AuthLayout from '../components/AuthLayout.jsx';

const PROVIDER_NAMES = { github: 'GitHub', google: 'Google' };

// Повідомлення про помилку входу через зовнішнього провайдера за кодом із адреси повернення
function providerError(provider, code) {
  const name = PROVIDER_NAMES[provider];
  const known = {
    denied: `Вхід через ${name} скасовано.`,
    state: `Не вдалося підтвердити запит на вхід через ${name}. Спробуйте ще раз.`,
    no_email: `В акаунті ${name} немає підтвердженої електронної пошти. Підтвердьте її або зареєструйтесь за email.`,
    unverified: `Електронну пошту акаунта ${name} не підтверджено. Підтвердьте її або зареєструйтесь за email.`,
    inactive: 'Цей акаунт вимкнено.',
  };
  return known[code] || `Не вдалося увійти через ${name}. Спробуйте ще раз.`;
}

const GoogleMark = () => (
  <svg aria-hidden="true" width="20" height="20" viewBox="0 0 48 48">
    <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z" />
    <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z" />
    <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z" />
    <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z" />
  </svg>
);

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
  const [providers, setProviders] = useState({}); // які способи входу налаштовано на сервері
  const [params] = useSearchParams();

  useEffect(() => {
    api
      .providers()
      .then(setProviders)
      .catch(() => setProviders({}));
  }, []);

  // Повернення від провайдера з помилкою: ?github_error=<код> або ?google_error=<код>
  useEffect(() => {
    for (const provider of Object.keys(PROVIDER_NAMES)) {
      const code = params.get(`${provider}_error`);
      if (code) setError(providerError(provider, code));
    }
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

        {(providers.google || providers.github) && (
          <>
            {providers.google && (
              <a className="btn ghost block github-btn" href="/api/auth/google/login">
                <GoogleMark /> Продовжити з Google
              </a>
            )}
            {providers.github && (
              <a className="btn ghost block github-btn" href="/api/auth/github/login">
                <GithubMark /> Продовжити з GitHub
              </a>
            )}
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
