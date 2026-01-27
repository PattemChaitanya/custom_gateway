import { useState } from 'react';
import { useParams } from 'react-router-dom';
import './APIDetail.css';
import api from '../services/api';

export default function APIDetail() {
  const params = useParams();
  const apiId = params.id;
  const [method, setMethod] = useState('POST');
  const [path, setPath] = useState('/register');
  const [body, setBody] = useState('{\n  "email": "test@example.com",\n  "password": "mypassword"\n}');
  const [response, setResponse] = useState<string>('');
  const [latency, setLatency] = useState<number | null>(null);

  async function handleTest() {
    setResponse('');
    const start = performance.now();
    try {
      const resp = await api.request({ method: method as any, url: path, data: JSON.parse(body) });
      const end = performance.now();
      setLatency(Math.round(end - start));
      setResponse(JSON.stringify(resp.data, null, 2));
    } catch (err: any) {
      const end = performance.now();
      setLatency(Math.round(end - start));
      setResponse(err?.response?.data ? JSON.stringify(err.response.data, null, 2) : String(err));
    }
  }

  return (
    <div className="api-detail-root">
      <aside className="left-nav">
        <h3>MyAPI</h3>
        <ul>
          <li>/</li>
          <li className="active">/register</li>
          <li>/login</li>
          <li>/users</li>
        </ul>
      </aside>

      <main className="method-panel">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2>ANY <span className="path">{path}</span></h2>
          <div>MyAPI / {apiId}</div>
        </div>
        <div className="panels">
          <section className="panel">
            <h4>Method Request</h4>
            <div className="row"><label>Authorization</label><div>API Key</div></div>
            <div className="row"><label>Request Body Model</label><div>UserRegisterSchema</div></div>
          </section>

          <section className="panel">
            <h4>Request Validation</h4>
            <div>Params Body: None</div>
          </section>

          <section className="panel">
            <h4>Logs</h4>
            <pre className="log">START Request:\nReceived request: {path}\nAuthorization: API Key\nEND Request</pre>
          </section>
        </div>
      </main>

      <aside className="test-panel">
        <div className="testing-box">
          <h4>TESTING</h4>
          <div className="form-row"><label>Method:</label>
            <select value={method} onChange={(e) => setMethod(e.target.value)}>
              <option>GET</option>
              <option>POST</option>
              <option>PUT</option>
              <option>DELETE</option>
            </select>
          </div>
          <div className="form-row"><label>Path:</label>
            <input value={path} onChange={(e) => setPath(e.target.value)} />
          </div>
          <div className="form-row"><label>Request Body</label>
            <textarea value={body} onChange={(e) => setBody(e.target.value)} rows={8} />
          </div>
          <button onClick={handleTest}>Test</button>
          <div className="metrics">
            <div>Latency {latency ? `${latency} ms` : '—'}</div>
          </div>
          <div className="response">
            <h5>Response</h5>
            <pre>{response}</pre>
          </div>
        </div>
      </aside>
    </div>
  );
}
