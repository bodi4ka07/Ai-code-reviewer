import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { api, getToken, setToken, setUnauthorizedHandler } from './api.js';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(Boolean(getToken()));

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(logout);
    if (!getToken()) return;
    api
      .me()
      .then(setUser)
      .catch(() => setToken(null))
      .finally(() => setLoading(false));
  }, [logout]);

  const login = useCallback(async (email, password) => {
    const { access_token } = await api.login(email, password);
    setToken(access_token);
    setUser(await api.me());
  }, []);

  // Вхід за готовим токеном (після повернення з GitHub)
  const loginWithToken = useCallback(async (token) => {
    setToken(token);
    try {
      setUser(await api.me());
    } catch (e) {
      setToken(null);
      throw e;
    }
  }, []);

  const register = useCallback(
    // Повертає true, якщо потрібно підтвердити email (вхід можливий лише після переходу за посиланням з листа)
    async (email, password) => {
      const created = await api.register(email, password);
      if (!created.email_verified) return true;
      await login(email, password);
      return false;
    },
    [login],
  );

  const value = useMemo(
    () => ({ user, loading, login, loginWithToken, register, logout }),
    [user, loading, login, loginWithToken, register, logout],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export const useAuth = () => useContext(AuthContext);
