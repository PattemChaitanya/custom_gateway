import { useState } from 'react';
import { useParams } from 'react-router-dom';
import api from '../services/api';
import { Container, Grid, Paper, Typography, Box, TextField, Select, MenuItem, Button } from '@mui/material';

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
    <Container maxWidth="lg" sx={{ py: 2 }}>
      <Grid container spacing={2}>
        <Grid item xs={12} md={3}>
          <Paper sx={{ p: 2, bgcolor: 'background.paper', color: 'text.primary' }} elevation={1}>
            <Typography variant="h6">MyAPI</Typography>
            <Box component="nav" sx={{ mt: 1 }}>
              <Typography component="div">/</Typography>
              <Typography component="div" sx={{ fontWeight: 700, mt: 0.5 }}>/register</Typography>
              <Typography component="div">/login</Typography>
              <Typography component="div">/users</Typography>
            </Box>
          </Paper>
        </Grid>

        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2, bgcolor: 'background.paper', color: 'text.primary' }} elevation={1}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Typography variant="h6">
                {method} <Box component="span" sx={{ fontWeight: 600, ml: 1 }}>{path}</Box>
              </Typography>
              <Typography variant="body2">MyAPI / {apiId}</Typography>
            </Box>

            <Box sx={{ display: 'grid', gridTemplateColumns: '1fr', gap: 2, mt: 2 }}>
              <Paper sx={{ p: 2, bgcolor: 'background.default' }} elevation={0}>
                <Typography variant="subtitle1">Method Request</Typography>
                <Box sx={{ mt: 1 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Typography>Authorization</Typography>
                    <Typography color="text.secondary">API Key</Typography>
                  </Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 1 }}>
                    <Typography>Request Body Model</Typography>
                    <Typography color="text.secondary">UserRegisterSchema</Typography>
                  </Box>
                </Box>
              </Paper>

              <Paper sx={{ p: 2, bgcolor: 'background.default' }} elevation={0}>
                <Typography variant="subtitle1">Request Validation</Typography>
                <Typography color="text.secondary">Params Body: None</Typography>
              </Paper>

              <Paper sx={{ p: 2, bgcolor: 'background.default' }} elevation={0}>
                <Typography variant="subtitle1">Logs</Typography>
                <Box component="pre" sx={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace', m: 0 }}>
                  {`START Request
Received request: ${path}
Authorization: API Key
END Request`}
                </Box>
              </Paper>
            </Box>
          </Paper>
        </Grid>

        <Grid item xs={12} md={3}>
          <Paper sx={{ p: 2, bgcolor: 'background.paper', color: 'text.primary' }} elevation={1}>
            <Typography variant="subtitle1">Testing</Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, mt: 1 }}>
              <Select size="small" value={method} onChange={(e) => setMethod(e.target.value as string)}>
                <MenuItem value="GET">GET</MenuItem>
                <MenuItem value="POST">POST</MenuItem>
                <MenuItem value="PUT">PUT</MenuItem>
                <MenuItem value="DELETE">DELETE</MenuItem>
              </Select>

              <TextField label="Path" value={path} onChange={(e) => setPath(e.target.value)} size="small" />

              <TextField label="Request Body" multiline minRows={6} value={body} onChange={(e) => setBody(e.target.value)} size="small" />

              <Button variant="contained" onClick={handleTest}>Test</Button>

              <Box>
                <Typography>Latency {latency ? `${latency} ms` : '—'}</Typography>
              </Box>

              <Box>
                <Typography variant="subtitle2">Response</Typography>
                <Box component="pre" sx={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace', maxHeight: 240, overflow: 'auto', m: 0 }}>{response}</Box>
              </Box>
            </Box>
          </Paper>
        </Grid>
      </Grid>
    </Container>
  );
}
