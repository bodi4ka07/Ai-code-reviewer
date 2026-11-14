import { useEffect } from 'react';

const KEYBOARD_MIN_HEIGHT = 120; // на скільки має зменшитись видима область, щоб вважати клавіатуру відкритою

const isTextField = (el) =>
  el instanceof HTMLElement && el.matches('input:not([type=checkbox]):not([type=radio]), textarea, select');

// На телефоні відкрита клавіатура підіймає нижню панель, тож поки вона відкрита, на <html> стоїть клас `typing`.
// Стан визначається за висотою видимої області, а не за фокусом: кнопка «Назад» закриває клавіатуру,
// але поле вводу лишається в фокусі. --vvh це поточна висота видимої області (без клавіатури).
export function useKeyboardState() {
  useEffect(() => {
    const root = document.documentElement;
    const viewport = window.visualViewport;

    if (!viewport) {
      // Резерв для браузерів без visualViewport: орієнтуємось на фокус
      const onFocusIn = (e) => isTextField(e.target) && root.classList.add('typing');
      const onFocusOut = () => root.classList.remove('typing');
      document.addEventListener('focusin', onFocusIn);
      document.addEventListener('focusout', onFocusOut);
      return () => {
        document.removeEventListener('focusin', onFocusIn);
        document.removeEventListener('focusout', onFocusOut);
        root.classList.remove('typing');
      };
    }

    let fullHeight = viewport.height; // найбільша видима висота, тобто без клавіатури
    const update = () => {
      fullHeight = Math.max(fullHeight, viewport.height);
      root.style.setProperty('--vvh', `${viewport.height}px`);
      root.classList.toggle('typing', fullHeight - viewport.height > KEYBOARD_MIN_HEIGHT);
    };
    const resetFullHeight = () => {
      fullHeight = 0;
      setTimeout(update, 300); // після повороту екрана розміри встановлюються не одразу
    };

    update();
    viewport.addEventListener('resize', update);
    window.addEventListener('orientationchange', resetFullHeight);
    return () => {
      viewport.removeEventListener('resize', update);
      window.removeEventListener('orientationchange', resetFullHeight);
      root.classList.remove('typing');
      root.style.removeProperty('--vvh');
    };
  }, []);
}
