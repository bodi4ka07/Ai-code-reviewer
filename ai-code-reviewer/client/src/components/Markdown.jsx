import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { copyText } from '../utils.js';

// Текст усередині елемента React (код у блоці ```...``` приходить як вкладені вузли)
function textOf(node) {
  if (node == null || typeof node === 'boolean') return '';
  if (typeof node === 'string' || typeof node === 'number') return String(node);
  if (Array.isArray(node)) return node.map(textOf).join('');
  return textOf(node.props?.children);
}

// Блок коду у відповіді AI з кнопкою «Копіювати»
function CodeBlock({ node, children, ...props }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    if (await copyText(textOf(children).replace(/\n$/, ''))) {
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    }
  };
  return (
    <div className="md-code">
      <button type="button" className="md-copy" onClick={copy}>
        {copied ? 'Скопійовано' : 'Копіювати'}
      </button>
      <pre {...props}>{children}</pre>
    </div>
  );
}

// react-markdown не виконує сирий HTML і прибирає небезпечні посилання, тому відповіді AI показувати безпечно
const components = {
  a: ({ node, ...props }) => <a {...props} target="_blank" rel="noopener noreferrer" />,
  pre: CodeBlock,
};

export default function Markdown({ children }) {
  return (
    <div className="md">
      <ReactMarkdown components={components}>{children}</ReactMarkdown>
    </div>
  );
}
