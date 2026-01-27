import { useState, useEffect } from 'react';
import { Container, Typography, TextField, Button, RadioGroup, FormControlLabel, Radio, Box, Alert } from '@mui/material';
import { createAPI, getAPI, updateAPI } from '../services/apis';
import { useNavigate } from 'react-router-dom';
import './CreateAPI.css';
import { useParams } from 'react-router-dom';

export default function CreateAPI() {
  const params = useParams();
  const editId = params.id ? Number(params.id) : null;
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [version, setVersion] = useState('1.0.0');
  const [type, setType] = useState('rest');
  const [format, setFormat] = useState('resource');
  const [sample, setSample] = useState(JSON.stringify({ openapi: '3.0.0', info: { title: 'MyAPI', description: 'My new API', version: '1.0.0' } }, null, 2));
  const [success, setSuccess] = useState<{ id?: number; email?: string } | null>(null as any);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  async function handleCreate(e?: React.FormEvent) {
    if (e) e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      if (editId) {
        const res = await updateAPI(editId, { name, version, description });
        setSuccess({ id: (res as any).id || editId });
      } else {
        const res = await createAPI({ name, version, description });
        setSuccess({ id: (res as any).id });
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || String(err));
    } finally {
      setLoading(false);
    }
  }

  // load when editing
  useEffect(() => {
    if (!editId) return;
    (async () => {
      try {
        const api = await getAPI(editId);
        setName(api.name || '');
        setDescription(api.description || '');
        setVersion(api.version || '1.0.0');
      } catch (e) {
        console.error('failed to load api', e);
      }
    })();
  }, [editId]);

  return (
    <Container maxWidth="md" className="create-api-root">
      <Typography variant="h4" gutterBottom>Create API</Typography>
      {success ? (
        <Alert severity="success" action={<Box>
          <Button size="small" onClick={() => navigate(`/apis/${(success as any).id}`)}>View API</Button>
          <Button size="small" onClick={() => { setSuccess(null); setName(''); setDescription(''); }}>Create another</Button>
        </Box>}>API created successfully.</Alert>
      ) : null}

      {error ? <Alert severity="error">{error}</Alert> : null}

      <form onSubmit={handleCreate} className="create-api-form">
        <div className="section">
          <Typography variant="h6">API Details</Typography>
          <TextField label="Name" value={name} onChange={(e) => setName(e.target.value)} fullWidth required />
          <TextField label="Description" value={description} onChange={(e) => setDescription(e.target.value)} fullWidth multiline rows={2} style={{ marginTop: 12 }} />
          <TextField label="Version" value={version} onChange={(e) => setVersion(e.target.value)} style={{ marginTop: 12 }} />
          <Box style={{ marginTop: 12 }}>
            <Typography variant="subtitle2">Type</Typography>
            <RadioGroup row value={type} onChange={(e) => setType(e.target.value)}>
              <FormControlLabel value="rest" control={<Radio />} label="REST API" />
              <FormControlLabel value="graphql" control={<Radio />} label="GraphQL API" />
            </RadioGroup>
          </Box>
        </div>

        <div className="section">
          <Typography variant="h6">Configuration Format</Typography>
          <RadioGroup row value={format} onChange={(e) => setFormat(e.target.value)}>
            <FormControlLabel value="resource" control={<Radio />} label="Resource Form" />
            <FormControlLabel value="json" control={<Radio />} label="JSON / YAML" />
            <FormControlLabel value="terraform" control={<Radio />} label="Terraform IAC" />
          </RadioGroup>

          <div className="editor">
            <div className="editor-header">JSON <Button size="small" onClick={() => setSample(JSON.stringify({ openapi: '3.0.0', info: { title: name || 'MyAPI', description: description || 'My new API', version } }, null, 2))}>Download Sample</Button></div>
            <textarea value={sample} onChange={(e) => setSample(e.target.value)} rows={8} />
          </div>
        </div>

        <div style={{ marginTop: 12, display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
          <Button onClick={() => navigate(-1)}>Cancel</Button>
          <Button variant="contained" color="primary" type="submit" disabled={loading} onClick={handleCreate}>{loading ? 'Creating…' : 'Create API'}</Button>
        </div>
      </form>
    </Container>
  );
}
