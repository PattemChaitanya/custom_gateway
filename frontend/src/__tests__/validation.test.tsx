import { render, screen, fireEvent } from '@testing-library/react';
import Login from '../pages/Login';
import Register from '../pages/Register';
import { BrowserRouter } from 'react-router-dom';

test('Login client-side validation shows errors', async () => {
  render(
    <BrowserRouter>
      <Login />
    </BrowserRouter>
  );

  fireEvent.change(screen.getByPlaceholderText(/email/i), { target: { value: 'bad-email' } });
  fireEvent.change(screen.getByPlaceholderText(/password/i), { target: { value: '123' } });
  fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

  expect(await screen.findByText(/Enter a valid email/i)).toBeTruthy();
  expect(await screen.findByText(/Password must be at least 6 characters/i)).toBeTruthy();
});

test('Register client-side validation shows errors', async () => {
  render(
    <BrowserRouter>
      <Register />
    </BrowserRouter>
  );

  fireEvent.change(screen.getByPlaceholderText(/email/i), { target: { value: 'bad-email' } });
  fireEvent.change(screen.getByPlaceholderText(/password/i), { target: { value: '123' } });
  fireEvent.click(screen.getByRole('button', { name: /create account/i }));

  expect(await screen.findByText(/Enter a valid email/i)).toBeTruthy();
  expect(await screen.findByText(/Password must be at least 6 characters/i)).toBeTruthy();
});
