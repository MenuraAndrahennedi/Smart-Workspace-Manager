# Azure Phase 2 Deployment

## Deployed Resources

| Resource | Value |
| --- | --- |
| Resource group | `rg-smart-workspace-manager` |
| Region | Central India (App Service and Azure SQL) |
| Backend App Service | `smart-workspace-manager-phase1` |
| App Service plan | `asp-smart-workspace-manager-f1` (Linux F1) |
| Frontend Static Web App | `smart-workspace-manager-frontend` (Free) |
| Frontend URL | `https://mango-tree-09402d200.1.azurestaticapps.net` |
| Backend URL | `https://smart-workspace-manager-phase1-f5b9emgdcecsddeg.centralindia-01.azurewebsites.net` |
| SQL logical server | `smart-workspace-manager-server` |
| SQL database | `smart-workspace-manager-db` |

The App Service name is retained from Phase 1, but the resource now runs FastAPI—not Streamlit.

## Backend Configuration

Runtime stack: Python 3.12 on Linux.

Startup command:

```bash
gunicorn -c gunicorn.conf.py backend.main:app
```

`gunicorn.conf.py` binds port 8000, uses one ASGI worker for F1 memory constraints, permits long data-processing requests, and sends access/error logs to Azure Log Stream.

Required App Service settings:

- `DATABASE_URL`
- `STORAGE_PROVIDER=local`
- `DATA_ROOT=/home/data`
- `SECRET_KEY`
- `ALGORITHM=HS256`
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `FRONTEND_ORIGINS=http://localhost:5173,https://mango-tree-09402d200.1.azurestaticapps.net`
- `LOG_LEVEL`
- All `MAX_*` limits present in `.env.example`
- `SCM_DO_BUILD_DURING_DEPLOYMENT=true`
- `PYTHONUNBUFFERED=1`

The singular `FRONTEND_ORIGIN` is a compatibility fallback only. Azure should use `FRONTEND_ORIGINS`.

## Frontend Configuration

The Static Web Apps artifact is built from `frontend/react_app` and uploaded from `frontend/react_app/dist`.

GitHub repository variable:

```text
VITE_API_BASE_URL=https://smart-workspace-manager-phase1-f5b9emgdcecsddeg.centralindia-01.azurewebsites.net
```

Vite substitutes this value during the production build. Changing the variable requires a new frontend workflow run; it is not read dynamically at browser runtime.

## Azure SQL and Networking

Azure SQL connections use ODBC Driver 18 with encryption and certificate verification. The SQL logical-server firewall allows the deployed App Service outbound IP addresses. Local IP rules should be temporary and narrowly scoped.

After changing database configuration, verify migrations:

```powershell
.venv\Scripts\python.exe -m alembic -c backend\database\migrations\alembic.ini current
.venv\Scripts\python.exe -m alembic -c backend\database\migrations\alembic.ini upgrade head
```

Expected head: `fd3f2d7e4c91`.

See `docs/azure_sql_setup.md` for connection-string encoding, schema, cost safeguards, and SQLite fallback.

## Managed Files

The deployed backend stores physical files under `/home/data`. Azure SQL stores only metadata and storage paths.

- Do not set Azure `DATA_ROOT=./data`; that would place runtime data in the deployed application directory.
- Do not expect a file uploaded by a local backend to exist in App Service merely because both use Azure SQL.
- If historical metadata refers to unavailable storage, re-upload the file or delete the obsolete record in the React Library/Dashboard.

This filesystem design is suitable for a single-instance demonstration. Blob Storage is the recommended future upgrade for durable, scalable production file storage.

## Cloud Smoke Test

1. Open `/health` and `/docs` on the backend.
2. Register a new user and sign in through React.
3. Confirm a protected endpoint rejects a request without a bearer token.
4. Upload and download a small CSV.
5. Analyze/filter it, clean it, and download outputs.
6. Generate charts and download HTML/PDF reports.
7. Upload an XLSX workbook, select a sheet, convert it, and download CSV.
8. Delete files and obsolete records.
9. Verify another user receives `403` for direct access to the first user's resources.
10. Refresh deployed React routes and confirm client-side routing remains available.

## Cost and Service Limitations

- App Service F1 has no production SLA or Always On and can cold-start or stop under quota pressure.
- Static Web Apps uses the Free plan.
- Azure SQL uses the free serverless offer with paid overage disabled when available.
- A `Free amount remaining` alert and resource-group budget notifications are configured.
- Budgets notify; they do not stop spending. Disabled SQL overage is the primary SQL cost safeguard.
- Close Query Editor, SSMS, VS Code SQL sessions, and local Azure-connected processes when finished so idle connections do not delay serverless auto-pause.

## Operational Checks

- App Service Log Stream shows Gunicorn startup and request logs.
- CORS contains only the local and deployed frontend origins.
- `/home/data` is configured before creating cloud files.
- The SQL firewall includes current App Service outbound addresses.
- GitHub Actions production runs are green.
- Azure cost/budget/free-allowance alerts remain enabled.

## Microsoft References

- [Azure App Service plans](https://learn.microsoft.com/azure/app-service/overview-hosting-plans)
- [Azure Static Web Apps hosting plans](https://learn.microsoft.com/azure/static-web-apps/plans)
- [Azure Static Web Apps quotas](https://learn.microsoft.com/azure/static-web-apps/quotas)
- [Azure SQL Database free offer](https://learn.microsoft.com/azure/azure-sql/database/free-offer)
