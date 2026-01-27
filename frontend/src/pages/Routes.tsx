import { useMemo, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import './Routes.css';

type RouteRow = {
  resource: string;
  method: string;
  auth: string;
  integration: string;
};

const SAMPLE: RouteRow[] = [
  { resource: '/user/register', method: 'ANY', auth: 'API Key', integration: 'Lambda Function' },
  { resource: '/user/login', method: 'POST', auth: 'API Key', integration: 'Lambda Function' },
  { resource: '/user/{id}', method: 'GET', auth: 'API Key', integration: 'HTTP Backend' },
  { resource: '/user/{id}', method: 'PATCH', auth: 'API Key', integration: 'Lambda Function' },
  { resource: '/task', method: 'PUT', auth: 'API Key', integration: 'HTTP Backend' },
  { resource: '/task/{id}', method: 'POST', auth: 'API Key', integration: 'Lambda Function' },
  { resource: '/authenticate', method: 'GET', auth: 'API Key', integration: 'HTTP Backend' },
  { resource: '/auth/token', method: 'POST', auth: 'JWT', integration: 'HTTP Backend' },
  { resource: '/profile', method: 'GET', auth: 'GET', integration: 'HTTP Backend' },
  { resource: '/metrics', method: 'GET', auth: 'GET', integration: 'HTTP Backend' },
  { resource: '/config', method: 'GET', auth: 'GET', integration: 'HTTP Backend' },
  { resource: '/settings', method: 'GET', auth: 'GET', integration: 'HTTP Backend' },
];

export default function Routes() {
  const { id } = useParams();
  const [filter, setFilter] = useState('');
  const [showCount] = useState(50);

  const rows = useMemo(() => {
    if (!filter) return SAMPLE.slice(0, showCount);
    const f = filter.toLowerCase();
    return SAMPLE.filter((r) => r.resource.toLowerCase().includes(f) || r.method.toLowerCase().includes(f)).slice(0, showCount);
  }, [filter, showCount]);

  return (
    <div className="routes-root">
      <aside className="routes-left">
        <h3>APIs</h3>
        <ul>
          <li className="api-title">MyAPI</li>
          <li><Link to={`/apis/${id}/routes`}>Resources</Link></li>
          <li className="active">Methods ({SAMPLE.length})</li>
          <li>Settings</li>
        </ul>
      </aside>

      <main className="routes-main">
        <div className="routes-header">
          <h2>Routes</h2>
          <div className="actions">
            <button className="btn primary">Create Method</button>
            <button className="btn">Actions</button>
          </div>
        </div>

        <div className="routes-controls">
          <label>API Filter</label>
          <select defaultValue={id || 'MyAPI'}>
            <option>MyAPI</option>
          </select>
          <label style={{ marginLeft: 12 }}>Show</label>
          <select defaultValue={String(showCount)}>
            <option>10</option>
            <option>25</option>
            <option>50</option>
          </select>
          <input className="search" placeholder="Search routes..." value={filter} onChange={(e) => setFilter(e.target.value)} />
        </div>

        <table className="routes-table">
          <thead>
            <tr>
              <th>Resource</th>
              <th>Method</th>
              <th>Auth</th>
              <th>Integration</th>
              <th>Caching</th>
              <th>Rate Limit</th>
              <th>Edit</th>
              <th>Metrics</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i}>
                <td>{r.resource}</td>
                <td><span className={`badge method-${r.method.toLowerCase()}`}>{r.method}</span></td>
                <td>{r.auth}</td>
                <td>{r.integration}</td>
                <td>Disabled</td>
                <td>Disabled</td>
                <td><button className="link">Edit</button></td>
                <td><button className="icon">▮▮▮</button></td>
              </tr>
            ))}
          </tbody>
        </table>

        <div className="routes-footer">Showing 1 to {rows.length} of {SAMPLE.length} entries</div>
      </main>
    </div>
  );
}
