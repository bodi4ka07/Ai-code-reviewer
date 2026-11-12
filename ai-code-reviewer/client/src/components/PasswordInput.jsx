import { useState } from 'react';
import { Icon } from './Icon.jsx';

// Поле пароля з кнопкою «показати / сховати»
export default function PasswordInput({ className = '', ...props }) {
  const [shown, setShown] = useState(false);
  return (
    <div className="pw">
      <input {...props} className={`input ${className}`} type={shown ? 'text' : 'password'} />
      <button
        type="button"
        className="pw-toggle"
        onClick={() => setShown((s) => !s)}
        aria-label={shown ? 'Сховати пароль' : 'Показати пароль'}
        title={shown ? 'Сховати пароль' : 'Показати пароль'}
      >
        <Icon name={shown ? 'eyeoff' : 'eye'} size={18} />
      </button>
    </div>
  );
}
