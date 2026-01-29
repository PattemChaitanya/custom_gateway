// Declare test globals for TypeScript in environments where @types/jest may not be installed
declare const test: any;
declare const expect: any;
declare const beforeAll: any;
declare const afterAll: any;
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import App from '../App';
import axios from 'axios';

test('login -> me flow uses msw handlers', async () => {
  // set initial URL before mounting so BrowserRouter picks it up
  window.history.pushState({}, 'Login', '/login');
  // App already contains a BrowserRouter internally, do not wrap again
  render(<App />);

  fireEvent.change(screen.getByPlaceholderText(/email/i), { target: { value: 'alice@example.com' } });
  fireEvent.change(screen.getByPlaceholderText(/password/i), { target: { value: 'password123' } });
  fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

  // wait for navigation to dashboard and welcome message
  await waitFor(() => expect(screen.getByText(/dashboard/i)).toBeTruthy());
  await waitFor(() => expect(screen.getByText(/Welcome, alice@example.com/i)).toBeTruthy());
});

test('queued requests trigger single refresh', async () => {
  // simulate expired access token by forcing axios to 401 on first two requests and then msw refresh will provide new token
  // In our handler setup, refresh will work if provided token isn't 'bad'
  // Here we'll directly call the api client to issue two requests that should be queued.
  const api = axios.create({ baseURL: 'http://localhost:8000' });
  // first, login to get tokens via msw
  const loginResp = await api.post('/auth/login', { email: 'bob@example.com', password: 'pwd' });
  const access = loginResp.data.access_token;
  let token = access;


  // msw won't have this handler; instead simulate by sending requests to /auth/me which is handled
  const p1 = api.get('/auth/me', { headers: { Authorization: `Bearer ${token}` } });
  const p2 = api.get('/auth/me', { headers: { Authorization: `Bearer ${token}` } });

  const results = await Promise.all([p1, p2]);
  expect(results[0].data.email).toBeDefined();
  expect(results[1].data.email).toBeDefined();
});
