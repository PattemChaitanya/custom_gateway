# React + TypeScript + Vite

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Babel](https://babeljs.io/) (or [oxc](https://oxc.rs) when used in [rolldown-vite](https://vite.dev/guide/rolldown)) for Fast Refresh
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/) for Fast Refresh

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the ESLint configuration

If you are developing a production application, we recommend updating the configuration to enable type-aware lint rules:

```js
export default defineConfig([
  globalIgnores(['dist']),
  {
    # React + TypeScript + Vite

    This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

    Currently, two official plugins are available:

    - [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Babel](https://babeljs.io/) (or [oxc](https://oxc.rs) when used in [rolldown-vite](https://vite.dev/guide/rolldown)) for Fast Refresh
    - [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/) for Fast Refresh

    ## React Compiler

    The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

    ## Expanding the ESLint configuration

    If you are developing a production application, we recommend updating the configuration to enable type-aware lint rules.

    ## Authentication flow (project-specific)

    This frontend integrates with the backend auth endpoints provided in `backend/app/api/auth`.

    - Login: `POST /auth/login` — backend returns `access_token` in response body and sets a HttpOnly `refresh_token` cookie.
    - Refresh: `POST /auth/refresh-tokens` — frontend calls this when a 401 occurs; the backend reads the cookie and returns a new `access_token` (and may rotate the refresh cookie).
    - Logout: `POST /auth/logout` — backend revokes the refresh token and clears cookie.

    Key frontend files:
    - `src/services/api.ts` — axios client with Authorization header injection and cookie-first refresh logic (retries up to 3 times, queues concurrent requests during refresh).
    - `src/hooks/useAuth.ts` — Zustand store for `accessToken` and `profile`.
    - `src/services/auth.ts` — login/logout/me helpers.
    - `src/pages/Login.tsx`, `src/pages/Register.tsx`, `src/pages/Dashboard.tsx` — pages demonstrating the flow.

    Storage and security:
    - Access token is stored in memory (Zustand) to reduce XSS risk.
    - Refresh token is stored as an HttpOnly cookie managed by the backend.

    ## Running locally

    1. Start backend (default assumed at `http://localhost:8000`):

    ```bash
    cd backend
    uvicorn app.main:app --reload --port 8000
    ```

    2. Start frontend:

    ```bash
    cd frontend
    npm install
    npm run dev
    ```

    If backend runs on a different port or host, set `VITE_API_URL` before starting the frontend, e.g.:

    ```bash
    export VITE_API_URL=http://localhost:8000
    npm run dev
    ```

    ## Running tests locally

    The frontend includes basic Jest + React Testing Library tests.

    Install dev dependencies and run:

    ```bash
    cd frontend
    npm install
    npm test
    ```

    Notes:
    - Tests use `ts-jest` and `jest-environment-jsdom`.
    - For integration tests that need cookies and network behavior, consider using `msw` (Mock Service Worker).

    ## Next improvements

    - Add e2e tests simulating cookie rotation (msw or Cypress).
    - Improve form validation and error UI.

    ## Deployment notes (cookies & CORS)

    When deploying to production, ensure the backend and frontend cookie/CORS settings are configured correctly:

    - Set `SECURE_COOKIES=true` in the backend environment to ensure refresh cookies are set with the Secure flag.
    - Choose an appropriate `COOKIE_SAMESITE` value (`lax` or `strict` is safe; use `none` only if cross-site usage is required and ensure `SECURE_COOKIES=true`).
    - Set `COOKIE_DOMAIN` if you need the cookie to be scoped to a specific domain (useful when frontend and backend share a parent domain).
    - On the frontend, ensure requests include credentials when necessary (`axios` client uses `withCredentials` for refresh calls).
    - Configure CORS on the backend to allow credentials and the frontend origin. For FastAPI, example:

    ```py
    from fastapi.middleware.cors import CORSMiddleware

    app.add_middleware(
      CORSMiddleware,
      allow_origins=["https://app.example.com"],
      allow_credentials=True,
      allow_methods=["*"],
      allow_headers=["*"],
    )
    ```

    Notes:
    - If `SameSite=None` is used for cookies, modern browsers require `Secure` to be true.
    - Avoid storing refresh tokens in localStorage in production; HttpOnly cookies are less exposed to XSS.
