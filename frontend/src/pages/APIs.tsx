import React, { useEffect, useState } from 'react';
import { listAPIs, createAPI, deleteAPI } from '../services/apis';
import type { APIItem } from '../services/apis';
import ApiList from '../components/ApiList';
import { Link as RouterLink } from 'react-router-dom';
import { Container, Typography, Box, TextField, Button, Stack } from '@mui/material';

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
    <Container maxWidth="md" sx={{ pt: 2 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h5">API Management</Typography>
        <Button variant="contained" component={RouterLink} to="/apis/create">Create API</Button>
      </Box>

      <Box component="form" onSubmit={handleCreate} sx={{ mb: 2 }}>
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} alignItems="center">
          <TextField label="Name" value={name} onChange={(e) => setName(e.target.value)} required size="small" />
          <TextField label="Version" value={version} onChange={(e) => setVersion(e.target.value)} size="small" />
          <TextField label="Description" value={desc} onChange={(e) => setDesc(e.target.value)} size="small" sx={{ flex: 1 }} />
          <Button type="submit" variant="contained">Create</Button>
        </Stack>
      </Box>

      <ApiList items={items} onDelete={handleDelete} />
    </Container>
  );
}
