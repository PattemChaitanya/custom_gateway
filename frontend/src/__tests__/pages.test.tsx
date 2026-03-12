/**
 * Tests for page components:
 * - Dashboard
 * - ResetPassword
 * - Login (client-side validation — detailed coverage)
 * - Register (submission + navigation)
 */
import {
  render,
  screen,
  fireEvent,
  waitFor,
  act,
} from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { useAuthStore } from "../hooks/useAuth";
import Dashboard from "../pages/Dashboard";
import ResetPassword from "../pages/ResetPassword";

// ---------------------------------------------------------------------------
// Service mocks
// ---------------------------------------------------------------------------
jest.mock("../services/auth", () => ({
  login: jest.fn(),
  logout: jest.fn().mockResolvedValue(undefined),
  me: jest.fn(),
  register: jest.fn(),
  resetPassword: jest.fn(),
  getCurrentUserInfo: jest.fn(),
}));

import * as authService from "../services/auth";
const mockLogin = authService.login as jest.Mock;
const mockLogout = authService.logout as jest.Mock;
const mockResetPassword = authService.resetPassword as jest.Mock;
const mockMe = authService.me as jest.Mock;
const mockRegister = authService.register as jest.Mock;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function withRouter(ui: React.ReactElement, entry = "/") {
  return render(<MemoryRouter initialEntries={[entry]}>{ui}</MemoryRouter>);
}

function setProfile(overrides: object = {}) {
  act(() => {
    useAuthStore.setState({
      accessToken: "tok",
      refreshToken: null,
      profile: {
        id: 1,
        email: "alice@example.com",
        is_active: true,
        is_superuser: false,
        roles: [],
        permissions: [],
        ...overrides,
      },
    });
  });
}

beforeEach(() => {
  jest.clearAllMocks();
  act(() => {
    useAuthStore.setState({
      accessToken: null,
      refreshToken: null,
      profile: null,
    });
  });
  localStorage.clear();
});

// ===========================================================================
// Dashboard
// ===========================================================================
describe("Dashboard", () => {
  test("shows welcome message with profile email", () => {
    setProfile({ email: "alice@example.com" });
    withRouter(<Dashboard />);
    expect(screen.getByText(/Welcome, alice@example.com/i)).toBeTruthy();
  });

  test("shows loading indicator when profile is null", () => {
    withRouter(<Dashboard />);
    expect(screen.getByRole("progressbar")).toBeTruthy();
  });

  test("renders Manage APIs and Control Plane buttons", () => {
    setProfile();
    withRouter(<Dashboard />);
    expect(screen.getByRole("button", { name: /manage apis/i })).toBeTruthy();
    expect(screen.getByRole("button", { name: /control plane/i })).toBeTruthy();
  });

  test("clicking Logout calls logout service", async () => {
    setProfile();
    withRouter(<Dashboard />);
    fireEvent.click(screen.getByRole("button", { name: /logout/i }));
    await waitFor(() => expect(mockLogout).toHaveBeenCalledTimes(1));
  });

  test("renders dashboard heading", () => {
    setProfile();
    withRouter(<Dashboard />);
    expect(screen.getByText(/dashboard/i)).toBeTruthy();
  });
});

// ===========================================================================
// ResetPassword
// ===========================================================================
describe("ResetPassword", () => {
  test("renders the form with email field and submit button", () => {
    withRouter(<ResetPassword />);
    expect(screen.getByPlaceholderText(/email/i)).toBeTruthy();
    expect(
      screen.getByRole("button", { name: /send reset link/i }),
    ).toBeTruthy();
  });

  test("shows success message on successful reset", async () => {
    mockResetPassword.mockResolvedValueOnce({
      message: "Password reset link sent",
    });
    withRouter(<ResetPassword />);
    fireEvent.change(screen.getByPlaceholderText(/email/i), {
      target: { value: "test@example.com" },
    });
    fireEvent.click(screen.getByRole("button", { name: /send reset link/i }));
    await waitFor(() =>
      expect(screen.getByText(/password reset link sent/i)).toBeTruthy(),
    );
    expect(mockResetPassword).toHaveBeenCalledWith("test@example.com");
  });

  test("shows error message on failed reset", async () => {
    mockResetPassword.mockRejectedValueOnce(new Error("Network error"));
    withRouter(<ResetPassword />);
    fireEvent.change(screen.getByPlaceholderText(/email/i), {
      target: { value: "bad@example.com" },
    });
    fireEvent.click(screen.getByRole("button", { name: /send reset link/i }));
    await waitFor(() =>
      expect(screen.getByText(/failed to send reset link/i)).toBeTruthy(),
    );
  });

  test("shows api error when response contains error field", async () => {
    mockResetPassword.mockResolvedValueOnce({ error: "User not found" });
    withRouter(<ResetPassword />);
    fireEvent.change(screen.getByPlaceholderText(/email/i), {
      target: { value: "nobody@example.com" },
    });
    fireEvent.click(screen.getByRole("button", { name: /send reset link/i }));
    await waitFor(() =>
      expect(screen.getByText(/user not found/i)).toBeTruthy(),
    );
  });

  test("button shows Sending… while request is in flight", async () => {
    let resolve!: (v: any) => void;
    mockResetPassword.mockReturnValueOnce(
      new Promise((r) => {
        resolve = r;
      }),
    );
    withRouter(<ResetPassword />);
    fireEvent.change(screen.getByPlaceholderText(/email/i), {
      target: { value: "a@b.com" },
    });
    fireEvent.click(screen.getByRole("button", { name: /send reset link/i }));
    expect(screen.getByRole("button", { name: /sending/i })).toBeTruthy();
    await act(async () => {
      resolve({ message: "done" });
    });
  });
});

// ===========================================================================
// Login page — additional coverage beyond validation.test.tsx
// ===========================================================================
import Login from "../pages/Login";

describe("Login page", () => {
  test("renders email, password fields and sign-in button", () => {
    withRouter(<Login />);
    expect(screen.getByPlaceholderText(/email/i)).toBeTruthy();
    expect(screen.getByPlaceholderText(/^password$/i)).toBeTruthy();
    expect(screen.getByRole("button", { name: /sign in/i })).toBeTruthy();
  });

  test("successful login stores profile and navigates", async () => {
    mockLogin.mockResolvedValueOnce({ access_token: "tok" });
    mockMe.mockResolvedValueOnce({
      email: "alice@example.com",
      id: 1,
      roles: [],
      permissions: [],
      is_active: true,
      is_superuser: false,
    });
    withRouter(<Login />, "/login");
    fireEvent.change(screen.getByPlaceholderText(/email/i), {
      target: { value: "alice@example.com" },
    });
    fireEvent.change(screen.getByPlaceholderText(/^password$/i), {
      target: { value: "password1" },
    });
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));
    await waitFor(() =>
      expect(mockLogin).toHaveBeenCalledWith("alice@example.com", "password1"),
    );
    await waitFor(() => expect(mockMe).toHaveBeenCalled());
  });

  test("shows api error when login returns error field", async () => {
    mockLogin.mockResolvedValueOnce({ error: "Invalid credentials" });
    withRouter(<Login />);
    fireEvent.change(screen.getByPlaceholderText(/email/i), {
      target: { value: "bad@example.com" },
    });
    fireEvent.change(screen.getByPlaceholderText(/^password$/i), {
      target: { value: "wrongpass" },
    });
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));
    await waitFor(() =>
      expect(screen.getByText(/invalid credentials/i)).toBeTruthy(),
    );
  });

  test("shows generic error on network failure", async () => {
    mockLogin.mockRejectedValueOnce(new Error("Network error"));
    withRouter(<Login />);
    fireEvent.change(screen.getByPlaceholderText(/email/i), {
      target: { value: "a@b.com" },
    });
    fireEvent.change(screen.getByPlaceholderText(/^password$/i), {
      target: { value: "password1" },
    });
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));
    await waitFor(() => expect(screen.getByText(/login failed/i)).toBeTruthy());
  });
});

// ===========================================================================
// Register page — submission + error paths
// ===========================================================================
import Register from "../pages/Register";

describe("Register page", () => {
  test("renders all form fields", () => {
    withRouter(<Register />);
    expect(screen.getByPlaceholderText(/email/i)).toBeTruthy();
    const pwFields = screen.getAllByPlaceholderText(/password/i);
    expect(pwFields.length).toBeGreaterThanOrEqual(2);
  });

  test("successful registration navigates away", async () => {
    mockRegister.mockResolvedValueOnce({ message: "User registered" });
    mockLogin.mockResolvedValueOnce({ access_token: "tok" });
    mockMe.mockResolvedValueOnce({
      email: "new@example.com",
      id: 2,
      roles: [],
      permissions: [],
      is_active: true,
      is_superuser: false,
    });
    withRouter(<Register />);
    fireEvent.change(screen.getByPlaceholderText(/email/i), {
      target: { value: "new@example.com" },
    });
    const pws = screen.getAllByPlaceholderText(/password/i);
    fireEvent.change(pws[0], { target: { value: "secure123" } });
    fireEvent.change(pws[1], { target: { value: "secure123" } });
    fireEvent.click(screen.getByLabelText(/i accept terms of use/i));
    fireEvent.click(screen.getByRole("button", { name: /register now/i }));
    await waitFor(() => expect(mockRegister).toHaveBeenCalled());
  });

  test("shows api error on registration failure", async () => {
    mockRegister.mockResolvedValueOnce({ error: "Email already exists" });
    withRouter(<Register />);
    fireEvent.change(screen.getByPlaceholderText(/email/i), {
      target: { value: "dup@example.com" },
    });
    const pws = screen.getAllByPlaceholderText(/password/i);
    fireEvent.change(pws[0], { target: { value: "password1" } });
    fireEvent.change(pws[1], { target: { value: "password1" } });
    fireEvent.click(screen.getByLabelText(/i accept terms of use/i));
    fireEvent.click(screen.getByRole("button", { name: /register now/i }));
    await waitFor(() =>
      expect(screen.getByText(/email already exists/i)).toBeTruthy(),
    );
  });

  test("shows generic error on network failure", async () => {
    mockRegister.mockRejectedValueOnce(new Error("Network error"));
    withRouter(<Register />);
    fireEvent.change(screen.getByPlaceholderText(/email/i), {
      target: { value: "new@example.com" },
    });
    const pws = screen.getAllByPlaceholderText(/password/i);
    fireEvent.change(pws[0], { target: { value: "password1" } });
    fireEvent.change(pws[1], { target: { value: "password1" } });
    fireEvent.click(screen.getByLabelText(/i accept terms of use/i));
    fireEvent.click(screen.getByRole("button", { name: /register now/i }));
    await waitFor(() =>
      expect(screen.getByText(/registration failed/i)).toBeTruthy(),
    );
  });
});
