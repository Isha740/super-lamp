import { useEffect, useState } from "react";
import { api } from "../api.js";

export default function Dashboard({ onLogout }) {
  const [links, setLinks] = useState([]);
  const [url, setUrl] = useState("");
  const [msg, setMsg] = useState(null); // { type, text }
  const [counts, setCounts] = useState({}); // short_code -> number (shown on demand)
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  // Any 401 from the API means the token expired
  const handle = (err) => {
    if (err.status === 401) return onLogout();
    setMsg({ type: "error", text: err.message });
  };

  useEffect(() => {
    api.listLinks().then(setLinks).catch(handle).finally(() => setLoading(false));
  }, []);

  async function shorten(e) {
    e.preventDefault();
    setMsg(null);
    setBusy(true);
    try {
      const link = await api.createLink(url);
      setLinks((prev) => [link, ...prev.filter((l) => l.short_code !== link.short_code)]);
      setMsg({ type: "success", text: `Short URL: ${link.short_url}` });
      setUrl("");
    } catch (err) {
      // the "already short enough" case comes back as a 400 with a friendly message
      if (err.status === 400) setMsg({ type: "info", text: err.message });
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
    if (!confirm("Delete this short link?")) return;
    try {
      await api.deleteLink(code);
      setLinks((prev) => prev.filter((l) => l.short_code !== code));
    } catch (err) {
      handle(err);
    }
  }

  async function copy(text) {
    try {
      await navigator.clipboard.writeText(text);
      setMsg({ type: "success", text: "Copied to clipboard." });
    } catch {
      setMsg({ type: "error", text: "Could not copy automatically." });
    }
  }

  return (
    <>
      <div className="card">
        <h2>Shorten a URL</h2>
        {msg && <div className={`flash ${msg.type}`}>{msg.text}</div>}
        <form onSubmit={shorten} className="row">
          <input
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="Paste your long URL here"
            required
          />
          <button disabled={busy}>{busy ? "..." : "Shorten"}</button>
        </form>
      </div>

      <div className="card">
        <h2>Your links</h2>
        {loading ? (
          <p className="muted">Loading...</p>
        ) : links.length === 0 ? (
          <p className="muted">No links yet. Shorten your first URL above.</p>
        ) : (
          <div className="scroll">
            <table>
              <thead>
                <tr><th>Short URL</th><th>Original</th><th>Clicks</th><th></th></tr>
              </thead>
              <tbody>
                {links.map((l) => (
                  <tr key={l.short_code}>
                    <td><a href={l.short_url} target="_blank" rel="noreferrer">{l.short_url}</a></td>
                    <td className="long" title={l.long_url}>{l.long_url}</td>
                    <td>
                      {counts[l.short_code] !== undefined ? (
                        <strong>{counts[l.short_code]}</strong>
                      ) : null}{" "}
                      <button className="ghost" onClick={() => viewCount(l.short_code)}>
                        {counts[l.short_code] !== undefined ? "Refresh" : "View count"}
                      </button>
                    </td>
                    <td className="actions">
                      <button className="ghost" onClick={() => copy(l.short_url)}>Copy</button>
                      <button className="ghost danger" onClick={() => remove(l.short_code)}>Delete</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
