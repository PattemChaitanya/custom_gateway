import { useState } from 'react';
import { verifyOtp } from '../services/auth';
import { useNavigate } from 'react-router-dom';

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
    // client-side guard: require exactly 6 digits
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
        // navigate to dashboard or login
        navigate('/login');
      }
    } catch (e) {
      setError('Verification failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'linear-gradient(90deg,#1fb6ff,#0066ff)' }}>
      <div style={{ maxWidth: 900, width: '100%', padding: 32, display: 'flex', gap: 24, alignItems: 'center', color: '#fff' }}>
        <div style={{ flex: 1 }}>
          <h1 style={{ fontSize: 40, margin: 0 }}>Authentication Code</h1>
          <p style={{ opacity: 0.9 }}>Enter the one-time code sent to your email or phone.</p>
        </div>

        <form onSubmit={submit} noValidate style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 12 }}>
          <input
            aria-label="OTP code"
            value={code}
            onChange={(e) => {
              // accept digits only, limit to 6 characters
              const digits = e.target.value.replace(/\D/g, '').slice(0, 6);
              setCode(digits);
            }}
            placeholder="- - - - - -"
            inputMode="numeric"
            maxLength={6}
            style={{
              padding: '18px 24px',
              fontSize: 24,
              borderRadius: 6,
              border: 'none',
              width: '100%',
              letterSpacing: '18px',
              textAlign: 'center',
              background: 'rgba(255,255,255,0.06)',
              color: '#fff',
              outline: 'none',
            }}
          />
          <button
            type="submit"
            style={{
              padding: '12px 20px',
              background: '#08306b',
              color: '#fff',
              fontWeight: 700,
              border: 'none',
              borderRadius: 6,
              opacity: loading || code.length !== 6 ? 0.6 : 1,
              cursor: loading || code.length !== 6 ? 'not-allowed' : 'pointer',
            }}
            disabled={loading || code.length !== 6}
          >
            {loading ? 'Verifying…' : 'VERIFY'}
          </button>
          {error && <div style={{ color: '#ffcccc' }}>{error}</div>}
          {message && <div style={{ color: '#ccffcc' }}>{message}</div>}
        </form>
      </div>
    </div>
  );
}
