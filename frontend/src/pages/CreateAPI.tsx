import { useState, useEffect } from 'react';
import { Container, Typography, TextField, Button, RadioGroup, FormControlLabel, Radio, Box, Alert, Stack } from '@mui/material';
import { createAPI, getAPI, updateAPI } from '../services/apis';
import { useNavigate } from 'react-router-dom';
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
    <Container maxWidth="md" sx={{ py: 2 }}>
      <Typography variant="h4" gutterBottom>{editId ? 'Update API' : 'Create API'}</Typography>
      {success && (
        <Alert severity="success" action={<Box>
          <Button size="small" onClick={() => navigate(`/apis/${(success as any).id}`)}>View API</Button>
          <Button size="small" onClick={() => { setSuccess(null); setName(''); setDescription(''); }}>Create another</Button>
        </Box>} sx={{ mb: 2 }}>API created successfully.</Alert>
      )}

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <Box component="form" onSubmit={handleCreate} sx={{ display: 'grid', gap: 3 }}>
        <Box>
          <Typography variant="h6" gutterBottom>API Details</Typography>
          <Stack spacing={2}>
            <TextField label="Name" value={name} onChange={(e) => setName(e.target.value)} fullWidth required />
            <TextField label="Description" value={description} onChange={(e) => setDescription(e.target.value)} fullWidth multiline rows={2} />
            <TextField label="Version" value={version} onChange={(e) => setVersion(e.target.value)} />
            <Box sx={{ mt: 1 }}>
              <Typography variant="subtitle2">Type</Typography>
              <RadioGroup row value={type} onChange={(e) => setType(e.target.value)}>
                <FormControlLabel value="rest" control={<Radio />} label="REST API" />
                <FormControlLabel value="graphql" control={<Radio />} label="GraphQL API" />
              </RadioGroup>
            </Box>
          </Stack>
        </Box>

        <Box>
          <Typography variant="h6" gutterBottom>Configuration Format</Typography>
          <RadioGroup row value={format} onChange={(e) => setFormat(e.target.value)}>
            <FormControlLabel value="resource" control={<Radio />} label="Resource Form" />
            <FormControlLabel value="json" control={<Radio />} label="JSON / YAML" />
            <FormControlLabel value="terraform" control={<Radio />} label="Terraform IAC" />
          </RadioGroup>

          <Box sx={{ mt: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
              <Typography>JSON</Typography>
              <Button size="small" onClick={() => setSample(JSON.stringify({ openapi: '3.0.0', info: { title: name || 'MyAPI', description: description || 'My new API', version } }, null, 2))}>Download Sample</Button>
            </Box>
            <TextField value={sample} onChange={(e) => setSample(e.target.value)} multiline rows={8} fullWidth variant="outlined" />
          </Box>
        </Box>

        <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1 }}>
          <Button onClick={() => navigate(-1)}>Cancel</Button>
          <Button variant="contained" color="primary" type="submit" disabled={loading}>
            {editId ? (loading ? 'Updating…' : 'Update API') : (loading ? 'Creating…' : 'Create API')}
          </Button>
        </Box>
      </Box>
    </Container>
  );
}
