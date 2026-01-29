import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import Register from "../pages/Register";
import * as authService from "../services/auth";

jest.mock("../services/auth", () => ({
  register: jest.fn(),
  login: jest.fn(),
  me: jest.fn(),
}));

test("Register calls API and navigates", async () => {
  (authService.register as jest.Mock).mockResolvedValue({});
  (authService.login as jest.Mock).mockResolvedValue({ access_token: "token" });
  (authService.me as jest.Mock).mockResolvedValue({ email: "new@x.com" });

  render(
    <BrowserRouter>
      <Register />
    </BrowserRouter>
  );

  fireEvent.change(screen.getByPlaceholderText(/email/i), {
    target: { value: "new@x.com" },
  });
  fireEvent.change(screen.getByPlaceholderText(/^password$/i), {
    target: { value: "password1" },
  });
  fireEvent.change(screen.getByPlaceholderText(/confirm password/i), {
    target: { value: "password1" },
  });

  fireEvent.click(screen.getByLabelText(/i accept terms of use/i));
  fireEvent.click(screen.getByRole("button", { name: /register now/i }));

  await waitFor(() => {
    expect(authService.register).toHaveBeenCalled();
    expect(authService.login).toHaveBeenCalled();
    expect(authService.me).toHaveBeenCalled();
  });
});
