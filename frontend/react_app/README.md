# Smart Workspace Manager React Frontend

This is the active React 19/Vite frontend for Smart Workspace Manager. It calls the separately deployed FastAPI backend and provides registration/login, dashboard, upload, library, CSV analysis/cleaning, charts/reports, and XLSX conversion.

## Local development

```powershell
Copy-Item .env.example .env
npm install
npm run dev
```

`frontend/react_app/.env` must define:

```dotenv
VITE_API_BASE_URL=http://localhost:8000
```

The Python backend must also allow `http://localhost:5173` through its root `FRONTEND_ORIGINS` setting.

## Commands

```powershell
npm run dev
npm run lint
npm run build
npm run preview
```

## Production

GitHub Actions reads `VITE_API_BASE_URL` from a repository variable during the build and deploys `dist/` to Azure Static Web Apps. The API URL is compiled into the bundle; changing it requires another build.

See the root [README](../../README.md), [React concepts](../../docs/react_concepts.md), and [CI/CD guide](../../docs/ci_cd.md) for the full project context.
