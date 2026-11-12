import { useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api.js';
import AuthLayout from '../components/AuthLayout.jsx';
import Steps from '../components/Steps.jsx';

export default function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    setBusy(true);
    try {
      const res = await api.forgotPassword(email.trim());
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
        <Steps current={message ? 1 : 0} />
        <h2>Забули пароль?</h2>
        <p className="muted">Вкажіть email акаунта, і ми надішлемо посилання для створення нового пароля.</p>

        {message ? (
          <div className="form-success">{message}</div>
        ) : (
          <>
            <label htmlFor="email">Email</label>
            <input
              id="email"
              className="input"
              type="email"
              required
              autoFocus
              autoComplete="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            {error && <div className="form-error">{error}</div>}
            <button className="btn block" disabled={busy}>
              {busy ? <span className="spinner sm" /> : 'Надіслати посилання'}
            </button>
          </>
        )}
        <div className="forgot center">
          <Link to="/login">Повернутися до входу</Link>
        </div>
      </form>
    </AuthLayout>
  );
}
