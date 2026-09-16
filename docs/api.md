# API and Authentication Reference

## Base URLs

- Local: `http://localhost:8000`
- Azure: `https://smart-workspace-manager-phase1-f5b9emgdcecsddeg.centralindia-01.azurewebsites.net`
- Interactive OpenAPI: `/docs`

The OpenAPI page is the authoritative field-level request and response contract. This document summarizes intended access and behavior.

## Authentication

### Register

`POST /api/auth/register` is public and accepts JSON:

```json
{
  "email": "user@example.com",
  "password": "at-least-8-characters"
}
```

The normalized email must be unique. A successful request returns `201` with a bearer token and signs the React user in. Duplicate email returns `409`; invalid email or password length returns `422`.

### Login

`POST /api/auth/login` is public and accepts `application/x-www-form-urlencoded` OAuth2 password fields:

```text
username=user@example.com
password=the-password
```

`username` contains the email. Successful login returns:

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer"
}
```

Use the token on protected requests:

```http
Authorization: Bearer <jwt>
```

## Endpoint Summary

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| GET | `/health` | Public | Backend health check |
| GET | `/api/settings/public` | Public | Frontend-safe limits and supported types |
| POST | `/api/auth/register` | Public | Create user and return token |
| POST | `/api/auth/login` | Public | Authenticate and return token |
| GET | `/api/dashboard/` | Protected | User-owned totals, groups, and recent files |
| GET | `/api/files/` | Protected | List/search/filter owned files |
| GET | `/api/files/{file_id}` | Protected/owned | Get file metadata |
| POST | `/api/files/upload` | Protected | Upload and organize one file |
| DELETE | `/api/files/{file_id}` | Protected/owned | Delete file/obsolete record and children |
| GET | `/api/files/{file_id}/download` | Protected/owned | Download a managed file |
| GET | `/api/analyzer/analyzable_files` | Protected | List organized owned CSV files |
| POST | `/api/analyzer/analysis/{file_id}` | Protected/owned | Analyze CSV and record job |
| GET | `/api/analyzer/analysis_job/{job_id}` | Protected/owned | Get analysis job |
| GET | `/api/analyzer/files/{file_id}/filter` | Protected/owned | Filter selected CSV columns/rows |
| POST | `/api/analyzer/files/{file_id}/chart` | Protected/owned | Build chart preview |
| POST | `/api/cleaning/{file_id}` | Protected/owned | Preview cleaning operations |
| POST | `/api/cleaning/save_cleaning_results/{file_id}` | Protected/owned | Save CSV and XLSX outputs |
| POST | `/api/reports/{file_id}` | Protected/owned | Generate HTML and PDF report |
| GET | `/api/reports/files/{file_id}` | Protected/owned | List reports for a file |
| GET | `/api/reports/{report_id}` | Protected/owned | Get report metadata |
| GET | `/api/reports/{report_id}/download` | Protected/owned | Download HTML/PDF report |
| GET | `/api/xlsx/files` | Protected | List organized owned XLSX files |
| GET | `/api/xlsx/files/{file_id}/sheets` | Protected/owned | List workbook sheets |
| POST | `/api/xlsx/files/{file_id}/convert` | Protected/owned | Convert one sheet to CSV |

## Error Format

Controlled domain errors generally use:

```json
{
  "error": "Error category",
  "message": "User-safe explanation"
}
```

Authentication errors generated directly by FastAPI may use `detail` instead. Important statuses:

| Status | Meaning |
| --- | --- |
| `400` | Invalid domain operation or malformed supported data |
| `401` | Missing, invalid, or expired token |
| `403` | Authenticated user does not own the resource |
| `404` | Database resource does not exist |
| `409` | Duplicate registration or stored file unavailable |
| `413` | Configured CSV analysis limit exceeded |
| `422` | Request/schema validation failed |
| `500` | Unexpected server failure with internal details hidden |

When metadata exists but the physical file is missing or from an obsolete storage path, file-dependent operations return:

```json
{
  "error": "Stored File Unavailable",
  "message": "The stored file is unavailable; please re-upload it."
}
```

The record can still be removed through `DELETE /api/files/{file_id}`.

## Ownership Rules

- List and dashboard queries filter by authenticated user ID.
- Direct file/job/report lookup checks ownership and returns `403` on mismatch.
- Cleaning and generated outputs are created for the authenticated owner.
- Deleting a file cascades its analysis jobs and report metadata.
- Public settings and system automation logs are intentionally not user-owned resources.
