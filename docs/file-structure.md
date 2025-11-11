# 📂 Monorepo File Structure (Python + Frontend)

This document explains the **monolithic architecture file structure** for our project. Both **backend (Python)** and **frontend (React/Next.js)** are included in a single repository, following a well-organized layout.

---

## 📁 Root Structure

```bash
monorepo/
│── backend/              # Python backend (monolithic core)
│── frontend/             # React/Next.js frontend
│── docs/                 # Documentation (architecture, ADRs, API contracts)
│── scripts/              # Automation scripts (setup, CI/CD helpers)
│── tests/                # Centralized integration/e2e tests
│── configs/              # Configurations shared across backend & frontend
│── .github/              # GitHub workflows & actions (CI/CD)
│── .gitignore
│── requirements.txt      # Backend Python dependencies
│── package.json          # Frontend dependencies (if standalone React/Next.js)
│── README.md             # Project overview
│── FILE_STRUCTURE.md     # This document
```

---

## 🐍 Backend Structure (Python Monolith)

```bash
backend/
│── app/                  # Core application code
│   ├── __init__.py
│   ├── main.py           # Entry point
│   ├── api/              # REST endpoints / Controllers
│   ├── services/         # Business logic layer
│   ├── models/           # Database models / ORM
│   ├── schemas/          # Pydantic/Marshmallow schemas (validation)
│   ├── repositories/     # Data access layer (DB queries)
│   ├── utils/            # Helper functions
│   └── middlewares/      # Request/response middlewares
│
│── config/               # Environment configs (dev, prod, test)
│   ├── settings.py
│   └── logging.py
│
│── migrations/           # DB migration scripts
│── tests/                # Unit tests (backend-specific)
│── requirements/         # Split dependency files (base, dev, prod)
│── Dockerfile            # Backend Docker config
```

### ✅ Notes:

* **`api/`** → Handles routing, maps HTTP requests to services.
* **`services/`** → Business logic, independent of DB.
* **`repositories/`** → DB operations, keeps persistence separate.
* **`schemas/`** → Ensures request/response validation.
* **`middlewares/`** → For auth, logging, request validation.

---

## ⚛️ Frontend Structure (React/Next.js)

```bash
frontend/
│── public/               # Static assets (images, fonts, icons)
│── src/
│   ├── components/       # Reusable UI components
│   ├── pages/            # Page-level components (Next.js: routing)
│   ├── layouts/          # Page layouts
│   ├── hooks/            # Custom React hooks
│   ├── contexts/         # Global state/context API
│   ├── services/         # API calls (fetch/Axios)
│   ├── utils/            # Utility functions
│   ├── styles/           # CSS/SCSS/Tailwind files
│   └── tests/            # Unit tests (Jest/RTL)
│
│── next.config.js        # Next.js config (if using Next.js)
│── vite.config.js        # Vite config (if using Vite)
│── package.json
│── tsconfig.json         # TypeScript config (if applicable)
```

### ✅ Notes:

* **`components/`** → Shared building blocks (buttons, inputs, modals).
* **`pages/`** → Each file becomes a route (Next.js) or router mapping (CRA/Vite).
* **`services/`** → Keeps API logic separated from UI.
* **`contexts/`** → For global state management.
* **`layouts/`** → Defines global layouts (header/footer/sidebar).

---

## 🧪 Centralized Tests

```bash
tests/
│── e2e/                  # End-to-end tests (Cypress/Playwright)
│── integration/          # Tests that span backend & frontend
│── performance/          # Load/performance testing scripts
```

---

## ⚙️ Configurations

```bash
configs/
│── nginx/                # Reverse proxy configs
│── docker/               # Docker Compose, multi-stage builds
│── env/                  # .env.example files for environments
│── monitoring/           # Grafana/Prometheus configs
```

---

## 🚀 Deployment

* **Backend** → Deployed as a containerized Python app (Docker + Gunicorn + Nginx).
* **Frontend** → Built & deployed as static files (served via Nginx/CDN).
* **CI/CD** → GitHub Actions pipeline inside `.github/workflows`.

---

## 🔑 Key Takeaways

* Single repo (**monorepo**) → Easier coordination between frontend & backend.
* **Clear separation** inside backend (api, services, repos, models).
* **Frontend isolated** but still part of repo.
* **Shared configs & docs** at root for collaboration.
* **Centralized testing** ensures backend + frontend integration stability.
