import { Icon } from './Icon.jsx';

// Спільна оболонка для входу, відновлення пароля та створення нового пароля
export default function AuthLayout({ children }) {
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
      <div className="auth-form">{children}</div>
    </div>
  );
}
