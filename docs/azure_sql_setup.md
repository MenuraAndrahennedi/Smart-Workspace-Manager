# Azure SQL Setup and SQLite Fallback

This runbook records the Day 17 database configuration for Smart Workspace
Manager. The application supports Azure SQL Database for its deployed metadata
database and SQLite for local development or temporary fallback use.

## Azure SQL resources

| Resource | Configuration |
| --- | --- |
| Subscription | Azure for Students |
| Resource group | `rg-smart-workspace-manager` |
| Region | Central India |
| Logical SQL server | `smart-workspace-manager-server` |
| Database | `smart-workspace-manager-db` |
| Tier | Free, General Purpose, serverless |
| Overage behavior | Disabled; pause when the monthly free limit is exhausted |
| Monthly free allowance | 100,000 vCore seconds, 32 GB data, 32 GB backup storage |

The server firewall must allow the IP addresses of approved clients and deployed
applications. Do not enable broad firewall access unless the deployment requires
it.

The deployed App Service outbound IP addresses are registered as narrowly scoped
SQL firewall rules. Recheck them if the App Service networking blade reports a
different outbound-IP set after a resource or plan change.

## Required local components

- Python 3.12 and the project virtual environment
- Microsoft ODBC Driver 18 for SQL Server
- `pyodbc`, SQLAlchemy, and Alembic from `requirements.txt`

Confirm that Windows can see the driver:

```powershell
Get-OdbcDriver -Name "ODBC Driver 18 for SQL Server"
```

## Environment configuration

Configuration is read from the project-root `.env` file locally and should be
provided through secure application settings in Azure. Never commit `.env`, a
real database password, or `SECRET_KEY`.

Use this SQLAlchemy URL format for Azure SQL:

```dotenv
DATABASE_URL=mssql+pyodbc://USERNAME:URL_ENCODED_PASSWORD@SERVER.database.windows.net:1433/DATABASE?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no
```

For this project, replace `SERVER` and `DATABASE` with:

```text
SERVER=smart-workspace-manager-server
DATABASE=smart-workspace-manager-db
```

The password must be URL-encoded. For example, `@` becomes `%40`. Generate an
encoded value without printing or committing the original password:

```powershell
.venv\Scripts\python.exe -c "from urllib.parse import quote_plus; import getpass; print(quote_plus(getpass.getpass('Password: ')))"
```

Copy only the encoded output into the private `.env` file. Keep encryption
enabled and `TrustServerCertificate=no`.

## Alembic migrations

Alembic reads `DATABASE_URL` through `backend.config.settings`. Its online mode
uses a non-persistent migration connection, and SQLite migrations use batch mode.

The current migration history is:

1. `9883f709a4d2` — baseline schema
2. `fd3f2d7e4c91` — users and file ownership

After selecting the intended database in `.env`, apply migrations from the
project root:

```powershell
.venv\Scripts\python.exe -m alembic -c backend\database\migrations\alembic.ini upgrade head
```

Check the installed revision when diagnosing a deployment:

```powershell
.venv\Scripts\python.exe -m alembic -c backend\database\migrations\alembic.ini current
```

Do not run a migration against Azure until the active `DATABASE_URL` has been
checked. Do not place a production connection string in `alembic.ini`.

## Verified Azure schema

Day 17 verification confirmed that Azure SQL reached revision
`fd3f2d7e4c91` and contains:

- `users`
- `files`
- `analysis_jobs`
- `reports`
- `automation_logs`
- `settings`
- `alembic_version`

`files.user_id` is required, indexed by `ix_files_user_id`, and references
`users.id` with cascade deletion. Analysis jobs and reports reference their
source files. The migration-created `legacy@local.invalid` row provides an owner
for pre-ownership data; it is not a normal application login.

The original Day 17 verification found no ownership or child-record orphans.
The active Phase 2 application now permits users to register and stores their
owned metadata in this database.

Azure SQL stores file metadata, not file bytes. A local backend and the deployed
backend can therefore see the same database row while using different physical
storage roots. If an older row points to a local Windows path or a missing Azure
file, file-dependent endpoints return `409` with:

```text
The stored file is unavailable; please re-upload it.
```

The React Library or Dashboard can delete that obsolete metadata safely. The
deletion service never follows or deletes a path outside the active `DATA_ROOT`.

## Cost safeguards

The database uses the Azure SQL free serverless offer with paid overage disabled.
The configured safeguards are:

- database pauses when its monthly free allowance is exhausted;
- a `Free amount remaining` metric alert triggers at 10,000 vCore seconds;
- email notification is configured through an Azure Monitor action group;
- the resource group has a small monthly Cost Management budget and email
  thresholds.

Cost Management budgets and alerts notify users but do not stop charges. The
disabled-overage database setting is the primary SQL cost control. Disconnect
Query Editor, SSMS, VS Code SQL sessions, and local backend processes after use
so idle connections do not delay serverless auto-pause.

## SQLite fallback

Use SQLite when developing locally or when Azure SQL is temporarily unavailable.
Set the private `.env` file to:

```dotenv
DATABASE_URL=sqlite:///./data/smart_workspace.db
```

Then migrate the SQLite database:

```powershell
.venv\Scripts\python.exe -m alembic -c backend\database\migrations\alembic.ini upgrade head
```

Start the application normally after migration. To return to Azure SQL, restore
the Azure SQL `DATABASE_URL`, confirm firewall access, and restart the process so
SQLAlchemy creates its engine with the new URL.

SQLite and Azure SQL are independent databases. Switching the URL does not copy
or synchronize users, file metadata, analysis jobs, reports, logs, or settings.
Local managed files under `DATA_ROOT` are also independent of database switching.
Use the fallback for development or temporary availability, not as automatic
failover.

## Troubleshooting

- **ODBC driver not found:** install Microsoft ODBC Driver 18 and confirm its
  registered name with `Get-OdbcDriver`.
- **Login timeout or firewall error:** confirm the client IP is allowed on the
  Azure SQL logical server and that TCP port 1433 is available.
- **Authentication failure:** verify the username and URL-encoded password in
  the private environment configuration.
- **Alembic URL interpolation error:** keep the URL in `.env`; the migration
  environment reads it directly and does not require inserting it into
  `alembic.ini`.
- **Database unavailable after exhausting free usage:** with paid overage
  disabled, wait for the monthly free allowance to reset.

## Microsoft References

- [Azure SQL Database free offer and current monthly allowances](https://learn.microsoft.com/azure/azure-sql/database/free-offer)
- [Configure Azure SQL server firewall rules](https://learn.microsoft.com/azure/azure-sql/database/firewall-configure)
