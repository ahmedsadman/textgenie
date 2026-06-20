import { useEffect, useState } from "react";
import "./App.css";

interface HealthResponse {
  status: string;
  message: string;
}

function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/health")
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data: HealthResponse) => setHealth(data))
      .catch((err) => setError(err.message));
  }, []);

  return (
    <div className="app">
      <h1>TextGenie</h1>
      {error && <p className="error">Backend error: {error}</p>}
      {health && (
        <div className="status">
          <p>Status: {health.status}</p>
          <p>{health.message}</p>
        </div>
      )}
      {!health && !error && <p>Connecting to backend...</p>}
    </div>
  );
}

export default App;
