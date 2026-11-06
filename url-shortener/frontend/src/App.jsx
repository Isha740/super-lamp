import { useState } from "react";
import { session } from "./api.js";
import AuthForm from "./components/AuthForm.jsx";
import Dashboard from "./components/Dashboard.jsx";

export default function App() {
  const [token, setToken] = useState(session.token);

  const logout = () => {
    session.clear();
    setToken(null);
  };

  return (
    <>
      <header>
        <span className="brand">Shortly</span>
        {token && (
          <div className="who">
            <span>{session.username}</span>
            <button className="ghost" onClick={logout}>Log out</button>
          </div>
        )}
      </header>
      <main>
        {token ? (
          <Dashboard onLogout={logout} />
        ) : (
          <AuthForm onAuth={() => setToken(session.token)} />
        )}
      </main>
    </>
  );
}
