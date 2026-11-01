import { useEffect, useRef, useState } from 'react';
import Markdown from './Markdown.jsx';

const MAX_TOTAL_MS = 3000;
const MAX_STEP_MS = 120;

const prefersReducedMotion = () =>
  typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;

// Відповідь AI вже отримана повністю; тут вона лише поступово показується рядками.
// animate=false (історія) показує текст одразу.
export default function StreamedMarkdown({ children, animate = false, onProgress }) {
  const lines = children.split('\n');
  const [shown, setShown] = useState(animate && !prefersReducedMotion() ? 0 : lines.length);
  const progress = useRef(onProgress);
  progress.current = onProgress;

  useEffect(() => {
    if (shown >= lines.length) return undefined;
    const step = Math.min(MAX_STEP_MS, MAX_TOTAL_MS / lines.length);
    const timer = setTimeout(() => {
      setShown((n) => n + 1);
      progress.current?.();
    }, step);
    return () => clearTimeout(timer);
  }, [shown, lines.length]);

  return <Markdown>{shown >= lines.length ? children : lines.slice(0, shown).join('\n')}</Markdown>;
}
