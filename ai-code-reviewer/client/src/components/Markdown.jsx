import ReactMarkdown from 'react-markdown';

// react-markdown не виконує сирий HTML і прибирає небезпечні посилання, тому відповіді AI показувати безпечно
const components = {
  a: ({ node, ...props }) => <a {...props} target="_blank" rel="noopener noreferrer" />,
};

export default function Markdown({ children }) {
  return (
    <div className="md">
      <ReactMarkdown components={components}>{children}</ReactMarkdown>
    </div>
  );
}
