import React, { useEffect, useState } from 'react';
import { listAPIs, createAPI, deleteAPI } from '../services/apis';
import type { APIItem } from '../services/apis';
import ApiList from '../components/ApiList';
import { Link } from 'react-router-dom';

export default function APIs() {
  const [items, setItems] = useState<APIItem[]>([]);
  const [name, setName] = useState('');
  const [version, setVersion] = useState('v1');
  const [desc, setDesc] = useState('');

  useEffect(() => {
    fetchList();
  }, []);

  async function fetchList() {
    try {
      const res = await listAPIs();
      setItems(res);
    } catch (e) {
      console.error('failed to fetch apis', e);
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    try {
      const created = await createAPI({ name, version, description: desc });
      setItems((s) => [created, ...s]);
      setName('');
      setDesc('');
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to create API');
    }
  }

  async function handleDelete(id: number) {
    if (!confirm('Delete API?')) return;
    try {
      await deleteAPI(id);
      setItems((s) => s.filter((x) => x.id !== id));
    } catch (e) {
      console.error('delete failed', e);
    }
  }

  return (
    <div>
      <h2>API Management</h2>
      <div style={{ marginBottom: 12 }}>
        <Link to="/apis/create"><button>Create API</button></Link>
      </div>
      <form onSubmit={handleCreate} style={{ marginBottom: 16 }}>
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Name" required />
        <input value={version} onChange={(e) => setVersion(e.target.value)} placeholder="Version" style={{ marginLeft: 8 }} />
        <input value={desc} onChange={(e) => setDesc(e.target.value)} placeholder="Description" style={{ marginLeft: 8 }} />
        <button type="submit" style={{ marginLeft: 8 }}>Create</button>
      </form>

      <ApiList items={items} onDelete={handleDelete} />
    </div>
  );
}
