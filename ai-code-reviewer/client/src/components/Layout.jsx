import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth.jsx';
import { useTheme } from '../theme.js';
import { Icon } from './Icon.jsx';

export default function Layout() {
  const { user, logout } = useAuth();
  const [theme, toggleTheme] = useTheme();
  const navigate = useNavigate();

  const exit = () => {
    logout();
    navigate('/login');
  };
  const initials = (user?.email || '?').slice(0, 2).toUpperCase();
  const themeIcon = theme === 'dark' ? 'sun' : 'moon';

  return (
    <div className="shell">
      <aside>
        <div className="logo">
          <span className="mark">
            <Icon name="code" />
          </span>{' '}
          Code Reviewer
        </div>
        <NavLink to="/" end className="nav-item">
          <Icon name="grid" /> Проєкти
        </NavLink>
        <NavLink to="/chat" className="nav-item">
          <Icon name="chat" /> Чат
        </NavLink>
        <div className="side-foot">
          <button className="theme" onClick={toggleTheme}>
            <Icon name={themeIcon} /> {theme === 'dark' ? 'Світла тема' : 'Темна тема'}
          </button>
          <div className="user">
            <div className="avatar">{initials}</div>
            <div className="user-info">
              <div className="user-email">{user?.email}</div>
              <button className="link" onClick={exit}>
                Вийти
              </button>
            </div>
          </div>
        </div>
      </aside>

      <main>
        <Outlet />
      </main>

      <nav className="tabbar">
        <NavLink to="/" end>
          <Icon name="grid" size={22} />
          Проєкти
        </NavLink>
        <NavLink to="/chat">
          <Icon name="chat" size={22} />
          Чат
        </NavLink>
        <button onClick={toggleTheme}>
          <Icon name={themeIcon} size={22} />
          Тема
        </button>
        <button onClick={exit}>
          <Icon name="logout" size={22} />
          Вийти
        </button>
      </nav>
    </div>
  );
}
