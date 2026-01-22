import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import Login from "../pages/Login";
import Register from "../pages/Register";
import { BrowserRouter } from "react-router-dom";
import * as authService from "../services/auth";

jest.mock("../services/auth");

describe("Auth pages", () => {
  test("Login calls login and navigates on success", async () => {
    (authService as any).login = jest.fn().mockResolvedValue({ access_token: "a" });

    render(
      <BrowserRouter>
        <Login />
      </BrowserRouter>
    );

    fireEvent.change(screen.getByPlaceholderText(/email/i), { target: { value: "a@b.com" } });
    fireEvent.change(screen.getByPlaceholderText(/password/i), { target: { value: "pwd" } });
    fireEvent.click(screen.getByText(/sign in/i));

    await waitFor(() => expect(authService.login).toHaveBeenCalled());
  });

  test("Register calls API and navigates to login", async () => {
  global.fetch = jest.fn().mockResolvedValue({ json: () => ({ message: "User registered" }) });

    render(
      <BrowserRouter>
        <Register />
      </BrowserRouter>
    );

    fireEvent.change(screen.getByPlaceholderText(/email/i), { target: { value: "new@x.com" } });
    fireEvent.change(screen.getByPlaceholderText(/password/i), { target: { value: "pwd" } });
    fireEvent.click(screen.getByText(/create account/i));

    await waitFor(() => expect(global.fetch).toHaveBeenCalled());
  });
});
