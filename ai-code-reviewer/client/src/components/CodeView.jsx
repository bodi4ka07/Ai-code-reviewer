import { useEffect, useRef } from 'react';

const KEYWORDS = {
  python: 'def return import from as try except finally pass with if elif else for while class in not and or is None True False lambda yield raise await async',
  js: 'function return const let var if else for while class new import export from try catch finally throw await async in of typeof this null undefined true false switch case break continue default interface type extends implements',
};
const BUILTINS = 'eval exec open print console document require';

const KEYWORD_SETS = {
  python: new Set(KEYWORDS.python.split(' ')),
  javascript: new Set(KEYWORDS.js.split(' ')),
  typescript: new Set(KEYWORDS.js.split(' ')),
};
const BUILTIN_SET = new Set(BUILTINS.split(' '));

// Простий токенізатор: повертає масив { type, text }, який рендериться як React-елементи (без innerHTML)
// Групи: 1 коментар, 2 рядок, 3 слово
const PY_RE = /(#.*$)|("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')|\b([A-Za-z_]\w*)\b/g;
const JS_RE = /(\/\/.*$)|("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'|`(?:[^`\\]|\\.)*`)|\b([A-Za-z_$][\w$]*)\b/g;

export function tokenize(line, language) {
  const keywords = KEYWORD_SETS[language] || new Set();
  const re = new RegExp((language === 'python' ? PY_RE : JS_RE).source, 'g');
  const tokens = [];
  let last = 0;
  let m;
  while ((m = re.exec(line))) {
    if (m.index > last) tokens.push({ type: 'plain', text: line.slice(last, m.index) });
    const [text, comment, str, word] = m;
    let type = 'plain';
    if (comment) type = 'c';
    else if (str) type = 's';
    else if (word) {
      const next = line[m.index + text.length];
      if (keywords.has(word)) type = 'k';
      else if (BUILTIN_SET.has(word)) type = 'b';
      else if (next === '(') type = 'f';
    }
    tokens.push({ type, text });
    last = m.index + text.length;
  }
  if (last < line.length) tokens.push({ type: 'plain', text: line.slice(last) });
  return tokens;
}

const SEV_COLOR = { critical: 'var(--crit)', warning: 'var(--warn)', info: 'var(--info)' };

// issues: { [lineNumber]: 'critical' | 'warning' | 'info' }
export default function CodeView({ code, language, issues, activeLine, fileLabel }) {
  const activeRef = useRef(null);

  useEffect(() => {
    if (activeRef.current) activeRef.current.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }, [activeLine]);

  const lines = code.split('\n');
  return (
    <div className="code-box">
      <div className="code-head">
        <div className="dots">
          <i />
          <i />
          <i />
        </div>
        <span className="mono">{fileLabel}</span>
      </div>
      <pre className="code">
        {lines.map((text, i) => {
          const n = i + 1;
          const sev = issues[n];
          const cls = `ln${sev ? ' bad' : ''}${activeLine === n ? ' active' : ''}`;
          return (
            <div
              key={n}
              className={cls}
              style={sev ? { '--c': SEV_COLOR[sev] } : undefined}
              ref={activeLine === n ? activeRef : undefined}
            >
              <span className="n">{n}</span>
              <span className="t">
                {tokenize(text, language).map((t, j) => (
                  <span key={j} className={t.type === 'plain' ? undefined : `tk-${t.type}`}>
                    {t.text}
                  </span>
                ))}
                {text === '' && ' '}
              </span>
            </div>
          );
        })}
      </pre>
    </div>
  );
}
