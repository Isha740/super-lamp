import { useEffect, useState } from "react";
import { api } from "../api.js";

const bare = (u) => u.replace(/^https?:\/\//, "");

export default function Dashboard({ onLogout }) {
  const [links, setLinks] = useState([]);
  const [url, setUrl] = useState("");
  const [note, setNote] = useState(null); // { type: "error" | "info", text }
  const [result, setResult] = useState(null);
  const [counts, setCounts] = useState({}); // short_code -> clicks, shown on demand
  const [copied, setCopied] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  // A 401 from the API means the login expired
  const handle = (err) => {
    if (err.status === 401) return onLogout();
    setNote({ type: "error", text: err.message });
  };

  useEffect(() => {
    api.listLinks().then(setLinks).catch(handle).finally(() => setLoading(false));
  }, []);

  async function shorten(e) {
    e.preventDefault();
    setNote(null);
    setBusy(true);
    try {
      const link = await api.createLink(url);
      setLinks((prev) => [link, ...prev.filter((l) => l.short_code !== link.short_code)]);
      setResult({ ...link, id: Date.now(), original: url });
      setUrl("");
    } catch (err) {
      setResult(null);
      if (err.status === 400) setNote({ type: "info", text: err.message });
      else handle(err);
    } finally {
      setBusy(false);
    }
  }

  async function viewCount(code) {
    try {
      const res = await api.getClicks(code);
      setCounts((c) => ({ ...c, [code]: res.clicks }));
    } catch (err) {
      handle(err);
    }
  }

  async function remove(code) {
    if (!confirm("Delete this short link? It will stop working.")) return;
    try {
      await api.deleteLink(code);
      setLinks((prev) => prev.filter((l) => l.short_code !== code));
      if (result && result.short_code === code) setResult(null);
    } catch (err) {
      handle(err);
    }
  }

  async function copy(code, text) {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(code);
      setTimeout(() => setCopied(""), 1500);
    } catch {
      setNote({ type: "error", text: "Could not copy. Select the link and copy it manually." });
    }
  }

  return (
    <>
      <section className="hero">
        <h1>Make long links short.</h1>
        <p className="lede">Paste a link below. We only shorten it when the short version is actually shorter.</p>
        <form onSubmit={shorten} className="bar">
          <input
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="Paste a long link here"
            aria-label="Long URL"
            required
          />
          <button className="btn-primary" disabled={busy}>{busy ? "Shortening..." : "Shorten link"}</button>
        </form>
        {note && <p className={`note ${note.type}`}>{note.text}</p>}

        {result && (
          <div className="result" key={result.id}>
            <span className="was">{result.original}</span>
            <div className="now">
              <a className="short" href={result.short_url} target="_blank" rel="noreferrer">{bare(result.short_url)}</a>
              <button className="btn-quiet" onClick={() => copy("result", result.short_url)}>
                {copied === "result" ? "Copied" : "Copy link"}
              </button>
            </div>
          </div>
        )}
      </section>

      <section>
        <div className="list-head">
          <h2>Your links</h2>
          <span className="muted">{links.length} total</span>
        </div>
        {loading ? (
          <p className="empty">Loading your links...</p>
        ) : links.length === 0 ? (
          <p className="empty">You have no links yet. Paste one above to create your first.</p>
        ) : (
          <ul className="links">
            {links.map((l) => {
              const n = counts[l.short_code];
              return (
                <li key={l.short_code}>
                  <div className="link-main">
                    <a className="short" href={l.short_url} target="_blank" rel="noreferrer">{bare(l.short_url)}</a>
                    <span className="orig" title={l.long_url}>{l.long_url}</span>
                  </div>
                  <div className="link-actions">
                    {n !== undefined && (
                      <span className="count"><b>{n}</b> {n === 1 ? "click" : "clicks"}</span>
                    )}
                    <button className="btn-quiet" onClick={() => viewCount(l.short_code)}>
                      {n !== undefined ? "Refresh count" : "View count"}
                    </button>
                    <button className="btn-quiet" onClick={() => copy(l.short_code, l.short_url)}>
                      {copied === l.short_code ? "Copied" : "Copy"}
                    </button>
                    <button className="btn-quiet danger" onClick={() => remove(l.short_code)}>Delete</button>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </>
  );
}
