# Documentation Index

The Markdown files below describe the final Phase 2 implementation and deployment.

| Document | Purpose |
| --- | --- |
| [Architecture and security](architecture.md) | Runtime layers, authentication, ownership, storage, and Azure topology |
| [API and authentication](api.md) | Public/protected endpoints, token use, ownership rules, and errors |
| [Azure deployment](azure_deployment.md) | Deployed resources, environment, startup, networking, smoke test, and limits |
| [Azure SQL setup](azure_sql_setup.md) | Connection setup, Alembic, firewall, cost controls, and SQLite fallback |
| [CI/CD workflows](ci_cd.md) | Backend/frontend GitHub Actions, secret names, verification, troubleshooting |
| [React/browser concepts](react_concepts.md) | Controlled inputs, events, conditional/dynamic rendering, routing, and `useRef` |
| [SQL and SQLAlchemy](sql/sql_crud.md) | Raw SQL concepts and repository equivalents |

The PDF/DOCX artifacts in this directory are planning and project-reference documents. The root `README.md` and the Markdown guides above are the current operational documentation for the completed codebase.

Never add real passwords, JWT secrets, database URLs containing credentials, Azure tokens, or private `.env` contents to documentation.
