import { useEffect, useRef, useState } from 'react';
import { Link, NavLink, useNavigate, useParams } from 'react-router-dom';
import { api } from '../api.js';
import { Icon } from '../components/Icon.jsx';
import Markdown from '../components/Markdown.jsx';

export default function Chat() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [chats, setChats] = useState(null);
  const [current, setCurrent] = useState(null);
  const [text, setText] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const bottomRef = useRef(null);

  useEffect(() => {
    api.chats().then(setChats).catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    setCurrent(null);
    setError('');
    if (!id) return undefined;
    let cancelled = false;
    api
      .chat(id)
      .then((c) => !cancelled && setCurrent(c))
      .catch((e) => !cancelled && setError(e.message));
    return () => {
      cancelled = true;
    };
  }, [id]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: 'end' });
  }, [current?.messages.length, sending]);

  const newChat = async () => {
    try {
      const chat = await api.createChat();
      setChats((list) => [chat, ...(list || [])]);
      navigate(`/chat/${chat.id}`);
    } catch (err) {
      setError(err.message);
    }
  };

  const removeChat = async (chat, e) => {
    e.preventDefault();
    e.stopPropagation();
    if (!window.confirm(`Видалити чат «${chat.title}»?`)) return;
    try {
      await api.deleteChat(chat.id);
      setChats((list) => list.filter((c) => c.id !== chat.id));
      if (chat.id === id) navigate('/chat');
    } catch (err) {
      setError(err.message);
    }
  };

  const send = async (e) => {
    e.preventDefault();
    const content = text.trim();
    if (!content || sending || !current) return;

    const chatId = current.id;
    const pending = { id: 'pending', role: 'user', content, created_at: new Date().toISOString() };
    const onlyThisChat = (fn) => (c) => (c && c.id === chatId ? fn(c) : c); // користувач міг перейти в інший чат

    setSending(true);
    setError('');
    setText('');
    setCurrent(onlyThisChat((c) => ({ ...c, messages: [...c.messages, pending] })));
    try {
      const res = await api.sendChatMessage(chatId, content);
      setCurrent(
        onlyThisChat((c) => ({
          ...c,
          title: res.chat.title,
          messages: [...c.messages.filter((m) => m.id !== 'pending'), res.user_message, res.assistant_message],
        })),
      );
      setChats((list) => [res.chat, ...(list || []).filter((x) => x.id !== res.chat.id)]);
    } catch (err) {
      setCurrent(onlyThisChat((c) => ({ ...c, messages: c.messages.filter((m) => m.id !== 'pending') })));
      setText((t) => t || content);
      setError(err.message);
    } finally {
      setSending(false);
    }
  };

  const onKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) send(e);
  };

  return (
    <div className={`chat-layout${id ? ' has-chat' : ''}`}>
      <div className="chat-list card">
        <div className="chat-list-head">
          <h3>Чати</h3>
          <button className="btn sm" onClick={newChat} title="Новий чат">
            <Icon name="plus" size={16} /> Новий
          </button>
        </div>
        <div className="chat-items">
          {chats === null && !error && <div className="empty small">Завантаження…</div>}
          {chats && chats.length === 0 && <div className="empty small">Чатів ще немає</div>}
          {(chats || []).map((c) => (
            <NavLink key={c.id} to={`/chat/${c.id}`} className="chat-item">
              <span className="chat-title">{c.title}</span>
              <button className="icon-btn" title="Видалити чат" onClick={(e) => removeChat(c, e)}>
                <Icon name="trash" size={16} />
              </button>
            </NavLink>
          ))}
        </div>
      </div>

      <div className="chat-pane card">
        {!id ? (
          <div className="chat-empty">
            <Icon name="chat" size={40} />
            <h3>Чат з AI про код</h3>
            <p className="muted">Питайте про помилки, патерни, вразливості. Створіть новий чат або оберіть наявний.</p>
            <button className="btn" onClick={newChat}>
              <Icon name="plus" /> Новий чат
            </button>
          </div>
        ) : (
          <>
            <div className="chat-head">
              <Link to="/chat" className="chat-back">
                ← Чати
              </Link>
              <b>{current ? current.title : ' '}</b>
            </div>

            <div className="chat-messages">
              {!current && !error && (
                <div className="splash">
                  <span className="spinner" />
                </div>
              )}
              {current && current.messages.length === 0 && (
                <div className="empty">Поставте перше питання. Код можна вставляти прямо в повідомлення.</div>
              )}
              {current?.messages.map((m) => (
                <div key={m.id} className={`msg ${m.role}`}>
                  {m.role === 'assistant' ? <Markdown>{m.content}</Markdown> : <div className="msg-text">{m.content}</div>}
                </div>
              ))}
              {sending && (
                <div className="msg assistant thinking">
                  <span className="spinner sm dark" /> AI думає…
                </div>
              )}
              <div ref={bottomRef} />
            </div>

            {error && <div className="form-error">{error}</div>}
            <form className="chat-input" onSubmit={send}>
              <textarea
                className="input"
                rows={2}
                maxLength={4000}
                placeholder="Напишіть питання. Enter надсилає, Shift+Enter новий рядок"
                value={text}
                disabled={!current}
                onChange={(e) => setText(e.target.value)}
                onKeyDown={onKeyDown}
              />
              <button className="btn" disabled={sending || !text.trim() || !current}>
                <Icon name="send" />
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  );
}
