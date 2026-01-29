import { rest } from 'msw';

let currentRefresh = 'initial-refresh';

export const handlers = [
  rest.post('http://localhost:8000/auth/login', async (req, res, ctx) => {
    const { email } = await req.json();
    // simulate setting refresh as cookie by returning refresh_token in body in tests
    currentRefresh = 'refresh-' + Math.random().toString(36).slice(2, 8);
    return res(ctx.status(200), ctx.json({ access_token: 'access-' + email, refresh_token: currentRefresh }));
  }),

  rest.post('http://localhost:8000/auth/refresh-tokens', async (req, res, ctx) => {
    // check body or pretend cookie
    let body = {} as any;
    try {
      body = await req.json();
    } catch(_) {}
    const provided = body.refresh_token || currentRefresh;
    if (!provided || provided.startsWith('bad')) {
      return res(ctx.status(200), ctx.json({ error: 'invalid_token' }));
    }
    // rotate refresh
    currentRefresh = 'refresh-' + Math.random().toString(36).slice(2, 8);
    return res(ctx.status(200), ctx.json({ message: 'Tokens refreshed', access_token: 'access-refreshed', refresh_token: currentRefresh }));
  }),

  rest.post('http://localhost:8000/auth/register', async (_req, res, ctx) => {
    // accept any register payload and respond with success
    return res(ctx.status(201), ctx.json({ message: 'User registered' }));
  }),

  rest.post('http://localhost:8000/auth/reset-password', async (req, res, ctx) => {
    // accept any email and pretend to send reset link
    const { email } = await req.json();
    return res(ctx.status(200), ctx.json({ message: 'Password reset link sent', email }));
  }),

  rest.post('http://localhost:8000/auth/verify-otp', async (req, res, ctx) => {
    const { otp } = await req.json();
    if (otp === '9999') return res(ctx.status(200), ctx.json({ message: 'OTP verified', otp }));
    return res(ctx.status(200), ctx.json({ error: 'invalid_otp' }));
  }),

  rest.get('http://localhost:8000/auth/me', (req, res, ctx) => {
    // return email from Authorization bearer token
    const auth = req.headers.get('authorization') || '';
    const m = /access-(.+)/.exec(auth);
    const email = m ? m[1] : 'unknown@example.com';
    return res(ctx.status(200), ctx.json({ message: 'Current user', email }));
  }),
];
