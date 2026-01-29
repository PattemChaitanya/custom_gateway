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
  const [validationError, setValidationError] = useState<string | null>(null);
  const [uiMeta, setUiMeta] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  async function handleCreate(e?: React.FormEvent) {
    if (e) e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      // build payload that matches backend expectations
      const payload: any = { name, version, description, type, format };
      const now = new Date().toISOString();
      const existingCreatedAt = uiMeta?.ui?.createdAt;
      // include config according to selected format
      if (format === 'json' || format === 'resource') {
        // parse JSON/YAML-as-JSON into object and attach UI metadata under _meta.ui
        try {
          const parsed = JSON.parse(sample);
          // attach UI metadata without overwriting existing keys
          const cfg = { ...parsed };
          cfg._meta = { ...(cfg._meta || {}), ui: { ...(cfg._meta?.ui || {}), type, format, createdAt: existingCreatedAt || now, updatedAt: now } };
          payload.config = cfg;
        } catch (parseErr) {
          throw new Error('Invalid JSON in configuration');
        }
      } else if (format === 'terraform') {
        // terraform is text/HCL; keep original body but store UI metadata in an object
        payload.config = { _meta: { ...(uiMeta || {}), ui: { ...(uiMeta?.ui || {}), type, format, createdAt: existingCreatedAt || now, updatedAt: now } }, body: sample };
      } else {
        // fallback: store raw sample with metadata
        payload.config = { _meta: { ...(uiMeta || {}), ui: { ...(uiMeta?.ui || {}), type, format, createdAt: existingCreatedAt || now, updatedAt: now } }, body: sample };
      }

      if (editId) {
        const res = await updateAPI(editId, payload);
        setSuccess({ id: (res as any).id || editId });
      } else {
        const res = await createAPI(payload);
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
        // populate UI fields when editing if available inside config._meta.ui
        if ((api as any).config !== undefined && (api as any).config !== null) {
          const cfg = (api as any).config;
          if (typeof cfg === 'string') {
            // older entries might store raw string
            setSample(cfg);
            setUiMeta(null);
          } else if (cfg._meta && cfg._meta.ui) {
            const ui = cfg._meta.ui;
            setUiMeta(cfg._meta);
            if (ui.type) setType(ui.type);
            if (ui.format) setFormat(ui.format);
            // remove _meta for display
            const displayCfg: any = { ...cfg };
            delete displayCfg._meta;
            try {
              setSample(JSON.stringify(displayCfg, null, 2));
            } catch (e) {
              setSample(String(displayCfg));
            }
          } else if (cfg.body && typeof cfg.body === 'string') {
            // terraform-like stored shape
            setUiMeta(cfg._meta || null);
            setSample(cfg.body);
          } else {
            try {
              setSample(JSON.stringify(cfg, null, 2));
            } catch (e) {
              setSample(String(cfg));
            }
          }
        }
      } catch (e) {
        console.error('failed to load api', e);
      }
    })();
  }, [editId]);

  // validate configuration based on selected format and type
  function validateConfig(value: string, fmt: string, t: string) {
    if (!value || value.trim().length === 0) {
      return 'Configuration cannot be empty';
    }

    // JSON / YAML choice: if it looks like JSON try parse, otherwise accept as YAML (no YAML parser installed)
    if (fmt === 'json') {
      try {
        JSON.parse(value);
      } catch (e) {
        return 'Invalid JSON. If you intended to provide YAML, choose the YAML option or enter valid JSON.';
      }
    }

    // resource form - expect JSON structure
    if (fmt === 'resource') {
      try {
        JSON.parse(value);
      } catch (e) {
        return 'Resource form expects a valid JSON object.';
      }
    }

    // terraform - do a lightweight sanity check (must contain at least one "resource" or "provider" keyword)
    if (fmt === 'terraform') {
      const lowered = value.toLowerCase();
      if (!lowered.includes('resource') && !lowered.includes('provider') && !lowered.includes('terraform')) {
        return 'Terraform configuration should contain HCL (e.g. resource / provider blocks).';
      }
    }

    // GraphQL type basic heuristic: expect 'query', 'mutation', 'type', or 'schema' somewhere
    if (t === 'graphql') {
      const lowered = value.toLowerCase();
      if (!lowered.includes('query') && !lowered.includes('mutation') && !lowered.includes('type') && !lowered.includes('schema')) {
        return 'GraphQL config should contain SDL or query/mutation definitions.';
      }
    }

    return null;
  }

  // run validation when sample/type/format change
  useEffect(() => {
    const err = validateConfig(sample, format, type);
    setValidationError(err);
  }, [sample, format, type]);

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
      {validationError && <Alert severity="warning" sx={{ mb: 2 }}>{validationError}</Alert>}

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
          <Button variant="contained" color="primary" type="submit" disabled={loading || Boolean(validationError)}>
            {editId ? (loading ? 'Updating…' : 'Update API') : (loading ? 'Creating…' : 'Create API')}
          </Button>
        </Box>
      </Box>
    </Container>
  );
}
