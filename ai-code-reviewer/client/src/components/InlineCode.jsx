// Текст коментаря з `інлайн-кодом`: фрагменти між зворотними лапками виводяться моноширинним шрифтом.
// Рендериться як React-вузли (не HTML), тож розмітка з відповіді AI не виконується.
export default function InlineCode({ children }) {
  const parts = String(children ?? '').split(/`([^`\n]+)`/);
  return parts.map((part, i) =>
    i % 2 === 1 ? (
      <code key={i} className="inline-code">
        {part}
      </code>
    ) : (
      part
    ),
  );
}
