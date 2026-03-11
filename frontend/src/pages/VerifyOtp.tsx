import { useState } from 'react';
import { verifyOtp } from '../services/auth';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  TextField,
  Button,
  Alert,
  Paper,
} from '@mui/material';

export default function VerifyOtp() {
  const [code, setCode] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setMessage(null);
    if (code.length !== 6) {
      setError('Please enter the 6-digit code');
      return;
    }
    try {
      setLoading(true);
      const r = await verifyOtp(code);
      if (r && r.error) setError(r.error);
      else {
        setMessage(r.message || 'OTP verified');
        navigate('/login');
      }
    } catch {
      setError('Verification failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: (theme) =>
          theme.palette.mode === 'dark'
            ? `linear-gradient(90deg, ${theme.palette.primary.dark}, ${theme.palette.info.dark})`
            : `linear-gradient(90deg, #1fb6ff, #0066ff)`,
        p: 2,
      }}
    >
      <Box
        sx={{
          maxWidth: 900,
          width: '100%',
          p: { xs: 2, sm: 4 },
          display: 'flex',
          flexDirection: { xs: 'column', md: 'row' },
          gap: 3,
          alignItems: 'center',
          color: '#fff',
        }}
      >
        <Box sx={{ flex: 1 }}>
          <Typography
            variant="h3"
            sx={{ fontWeight: 700, color: 'inherit', mb: 1 }}
          >
            Authentication Code
          </Typography>
          <Typography variant="body1" sx={{ opacity: 0.9, color: 'inherit' }}>
            Enter the one-time code sent to your email or phone.
          </Typography>
        </Box>

        <Paper
          component="form"
          onSubmit={submit}
          noValidate
          elevation={0}
          sx={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            gap: 1.5,
            bgcolor: 'transparent',
          }}
        >
          <TextField
            aria-label="OTP code"
            value={code}
            onChange={(e) => {
              const digits = e.target.value.replace(/\D/g, '').slice(0, 6);
              setCode(digits);
            }}
            placeholder="- - - - - -"
            inputMode="numeric"
            slotProps={{
              htmlInput: {
                maxLength: 6,
                style: {
                  letterSpacing: '18px',
                  textAlign: 'center',
                  fontSize: 24,
                  padding: '14px 20px',
                  color: '#fff',
                },
              },
            }}
            sx={{
              '& .MuiOutlinedInput-root': {
                bgcolor: 'rgba(255,255,255,0.08)',
                '& fieldset': { borderColor: 'rgba(255,255,255,0.2)' },
                '&:hover fieldset': { borderColor: 'rgba(255,255,255,0.4)' },
                '&.Mui-focused fieldset': { borderColor: '#fff' },
              },
            }}
            fullWidth
          />
          <Button
            type="submit"
            variant="contained"
            disabled={loading || code.length !== 6}
            sx={{
              py: 1.5,
              fontWeight: 700,
              bgcolor: 'rgba(8,48,107,0.9)',
              '&:hover': { bgcolor: 'rgba(8,48,107,1)' },
            }}
          >
            {loading ? 'Verifying…' : 'VERIFY'}
          </Button>
          {error && <Alert severity="error">{error}</Alert>}
          {message && <Alert severity="success">{message}</Alert>}
        </Paper>
      </Box>
    </Box>
  );
}
