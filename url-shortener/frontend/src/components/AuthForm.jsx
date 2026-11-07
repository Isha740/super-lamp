import { useState } from "react";
import { api, session } from "../api.js";

export default function AuthForm({ onAuth }) {
  const [mode, setMode] = useState("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [busy, setBusy] = useState(false);
  const isLogin = mode === "login";

  async function submit(e) {
    e.preventDefault();
    setError("");
    setInfo("");
    setBusy(true);
    try {
      if (!isLogin) {
        await api.register(username, password);
        setInfo("Account created. Log in to continue.");
        setMode("login");
        setPassword("");
      } else {
        const res = await api.login(username, password);
        session.save(res.access_token, res.username);
        onAuth();
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  function toggle() {
    setError("");
    setInfo("");
    setMode(isLogin ? "register" : "login");
  }

  return (
    <div className="auth">
      <div>
        <h1>Long links in. Short links out.</h1>
        <p className="lede">Shorten a link, share it anywhere, and see how many people opened it.</p>
      </div>
      <div className="panel">
        <h2>{isLogin ? "Log in" : "Create your account"}</h2>
        {info && <div className="flash success">{info}</div>}
        {error && <div className="flash error">{error}</div>}
        <form onSubmit={submit}>
          <label>
            Username
            <input value={username} onChange={(e) => setUsername(e.target.value)} required minLength={3} autoFocus />
          </label>
          <label>
            Password
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} />
          </label>
          <button className="btn-primary" disabled={busy}>
            {busy ? "Please wait..." : isLogin ? "Log in" : "Create account"}
          </button>
        </form>
        <p className="switch">
          {isLogin ? "New here? " : "Already have an account? "}
          <button type="button" onClick={toggle}>{isLogin ? "Create an account" : "Log in"}</button>
        </p>
      </div>
    </div>
  );
}
