import { useState } from "react";
import { session } from "./api.js";
import AuthForm from "./components/AuthForm.jsx";
import Dashboard from "./components/Dashboard.jsx";

function Wordmark() {
  return (
    <span className="brand">
      <svg width="28" height="14" viewBox="0 0 28 14" aria-hidden="true">
        <rect width="28" height="4" rx="2" />
        <rect y="10" width="14" height="4" rx="2" />
      </svg>
      shortly
    </span>
  );
}

export default function App() {
  const [token, setToken] = useState(session.token);

  const logout = () => {
    session.clear();
    setToken(null);
  };

  return (
    <>
      <header>
        <Wordmark />
        {token && (
          <div className="who">
            <span>{session.username}</span>
            <button className="btn-quiet" onClick={logout}>Log out</button>
          </div>
        )}
      </header>
      <main>
        {token ? <Dashboard onLogout={logout} /> : <AuthForm onAuth={() => setToken(session.token)} />}
      </main>
    </>
  );
}
