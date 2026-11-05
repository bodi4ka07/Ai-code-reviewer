import { Icon } from './Icon.jsx';

// Спільна оболонка для входу, реєстрації, відновлення пароля та підтвердження email
const COPY = {
  in: {
    title: (
      <>
        Ваші рев'ю вже <span>чекають</span>.
      </>
    ),
    text: 'Увійдіть, щоб повернутися до проєктів, історії перевірок і розмов з ШІ про ваш код.',
  },
  up: {
    title: (
      <>
        Помилки видно ще до <span>продакшну</span>.
      </>
    ),
    text: 'Зареєструйтесь, надішліть файл і за хвилину отримайте оцінку, список проблем та готові виправлення.',
  },
};

// mode: 'in' (вхід) або 'up' (реєстрація та інші екрани); визначає заголовок і текст ліворуч
export default function AuthLayout({ children, mode = 'up' }) {
  const copy = COPY[mode] || COPY.up;
  return (
    <div className="auth">
      <div className="hero">
        <div className="hero-top">
          <div className="logo" style={{ padding: 0 }}>
            <span className="mark">
              <Icon name="code" />
            </span>
            AI Code Reviewer
          </div>
          <span className="pill">Semgrep + ШІ</span>
        </div>

        <div className="hero-text">
          <h1>{copy.title}</h1>
          <p>{copy.text}</p>
        </div>

        {/* Декоративний приклад результату, не реальні дані */}
        <div className="preview" aria-hidden="true">
          <div className="pv-card">
            <div className="pv-head">
              <span className="dots">
                <i />
                <i />
                <i />
              </span>
              <span>auth_service.py</span>
              <span style={{ width: 40 }} />
            </div>
            <div className="pv-code">
              <div>
                <b>4</b>
                <span>
                  <span className="tk-k">def</span> <span className="tk-f">login</span>(db, name, password):
                </span>
              </div>
              <div className="bad">
                <b>5</b>
                <span>
                  {'    q = '}
                  <span className="tk-s">{"f\"SELECT * ... '{name}'\""}</span>
                </span>
              </div>
              <div>
                <b>6</b>
                <span>{'    row = db.execute(q).fetchone()'}</span>
              </div>
            </div>
          </div>
          <div className="pv-issue">
            <div className="row">
              <span className="tag">Критично</span>SQL-ін'єкція
            </div>
            <span>Використайте параметризований запит.</span>
          </div>
          <div className="pv-score">
            <svg width="72" height="72" viewBox="0 0 140 140">
              <circle cx="70" cy="70" r="58" fill="var(--surface)" stroke="var(--border2)" strokeWidth="14" />
              <circle
                cx="70"
                cy="70"
                r="58"
                fill="none"
                stroke="var(--ok)"
                strokeWidth="14"
                strokeLinecap="round"
                strokeDasharray="364.4"
                strokeDashoffset="102"
                transform="rotate(-90 70 70)"
              />
            </svg>
            <span>72</span>
          </div>
        </div>

        <div className="hero-tags">
          <span>Python · JS · TS</span>
          <span>Баги, безпека, стиль</span>
          <span>Чат про ваш код</span>
        </div>
      </div>
      <div className="auth-form">{children}</div>
    </div>
  );
}
