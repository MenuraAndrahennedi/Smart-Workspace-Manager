# CI/CD Workflows

Production deployments run from the `main` branch. Backend and frontend have separate GitHub Actions workflows.

## Backend Workflow

File: `.github/workflows/deploy-azure.yml`

Trigger:

- Every push to `main`
- Manual `workflow_dispatch`

Test job:

1. Check out the repository.
2. Set up Python 3.12 with pip caching.
3. Install `requirements-streamlit.txt` so the full backend and preserved legacy boundary tests are available.
4. Run `pip check`.
5. Run unit, API, and integration tests against an isolated SQLite database and local CI data root.

Deploy job (only after tests pass):

1. Verify `requirements.txt`, `backend/main.py`, and `gunicorn.conf.py` exist.
2. Authenticate to Azure using OIDC.
3. Deploy the repository to the `smart-workspace-manager-phase1` App Service.

GitHub repository secrets used:

- `AZURE_CLIENT_ID`
- `AZURE_TENANT_ID`
- `AZURE_SUBSCRIPTION_ID`

Azure uses the federated GitHub credential `github-swm-main`. No client secret or publish-profile password is committed.

## Frontend Workflow

File: `.github/workflows/deploy-frontend.yml`

Trigger:

- Pushes to `main` that change `frontend/react_app/**` or the workflow
- Manual `workflow_dispatch`

Steps:

1. Check out the repository.
2. Set up Node.js 24 with npm caching.
3. Run `npm ci`.
4. Run `npm run lint`.
5. Require the production `VITE_API_BASE_URL` repository variable.
6. Run `npm run build`.
7. Upload `frontend/react_app/dist` to Azure Static Web Apps.

GitHub configuration used:

- Repository variable: `VITE_API_BASE_URL`
- Repository secret: `AZURE_STATIC_WEB_APPS_API_TOKEN`

The workflow uses `skip_app_build: true` because GitHub already built and validated the exact artifact being deployed.

## Configuration Ownership

| Setting type | Location | Examples |
| --- | --- | --- |
| Test-only values | Workflow job environment | SQLite URL, CI secret, test limits |
| Backend deployment secrets/config | Azure App Service settings | `DATABASE_URL`, `SECRET_KEY`, `FRONTEND_ORIGINS` |
| Frontend build-time API URL | GitHub repository variable | `VITE_API_BASE_URL` |
| Azure OIDC identifiers | GitHub repository secrets | client, tenant, subscription IDs |
| Static Web Apps deployment token | GitHub repository secret | `AZURE_STATIC_WEB_APPS_API_TOKEN` |

Never store database credentials, JWT secret values, or deployment tokens in workflow YAML, `.env.example`, documentation, screenshots, issues, or logs.

## Release Verification

After a fresh push:

1. Confirm the backend test job succeeds.
2. Confirm Azure OIDC login and backend deployment succeed.
3. Confirm frontend install, lint, build, and deployment succeed when frontend files changed.
4. Open the deployed commit's frontend and verify the visible change.
5. Open `/health` on the deployed backend.
6. Run the cloud login/upload/analysis/report/delete smoke test.

If only documentation changes, the backend workflow still runs because it is triggered by every `main` push; the frontend workflow does not run unless its configured paths changed or it is started manually.

## Troubleshooting

- **Backend tests fail before deployment:** open the failed pytest step and reproduce its command locally.
- **OIDC login fails:** verify the three Azure identifier secrets and the federated credential's repository, `main` branch, and subject.
- **App deploy succeeds but API is unavailable:** inspect App Service Log Stream, startup command, dependencies, database firewall, and app settings.
- **Frontend configuration check fails:** define the repository variable `VITE_API_BASE_URL` with the deployed backend origin and no trailing API path.
- **Static Web Apps deployment fails:** refresh the deployment token in Azure and update the GitHub secret.
- **Frontend shows Network Error:** verify the compiled API URL, backend health, exact Static Web Apps origin in `FRONTEND_ORIGINS`, and App Service/Azure SQL connectivity.
