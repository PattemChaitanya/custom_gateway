import { render, screen, fireEvent } from '@testing-library/react';
import Login from '../pages/Login';
import Register from '../pages/Register';
import { BrowserRouter } from 'react-router-dom';

describe('Client-side validation', () => {
  test('Login shows email and password length errors', async () => {
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

  test('Register shows email, password length and terms errors', async () => {
    render(
      <BrowserRouter>
        <Register />
      </BrowserRouter>
    );

    // invalid email
    fireEvent.change(screen.getByPlaceholderText(/email/i), { target: { value: 'bad-email' } });

    // use the first password input for the main password field
    const pw = screen.getAllByPlaceholderText(/password/i);
    fireEvent.change(pw[0], { target: { value: '123' } });
    fireEvent.change(pw[1], { target: { value: '123' } });

    // do not check terms
    fireEvent.click(screen.getByRole('button', { name: /register now/i }));

    expect(await screen.findByText(/Enter a valid email/i)).toBeTruthy();
    expect(await screen.findByText(/Password must be at least 6 characters/i)).toBeTruthy();
    expect(await screen.findByText(/Please accept Terms of Use/i)).toBeTruthy();
  });

  test('Register shows password mismatch error', async () => {
    render(
      <BrowserRouter>
        <Register />
      </BrowserRouter>
    );

    const pw = screen.getAllByPlaceholderText(/password/i);
    fireEvent.change(pw[0], { target: { value: 'password1' } });
    fireEvent.change(pw[1], { target: { value: 'password2' } });
    fireEvent.click(screen.getByRole('button', { name: /register now/i }));

    expect(await screen.findByText(/Passwords do not match/i)).toBeTruthy();
  });
});
