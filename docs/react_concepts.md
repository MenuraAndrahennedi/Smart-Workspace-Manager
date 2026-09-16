# React and Browser Concepts Used

The React frontend is intentionally small and demonstrates the browser concepts required by the work plan.

## Component Structure

- `AppRoutes.jsx` maps public and protected routes.
- `ProtectedRoute.jsx` redirects users without a valid session.
- `AppLayout.jsx` supplies navigation and the signed-in identity.
- Page components coordinate API calls and page state.
- Reusable components include file names/icons, data tables, CSV selection, and chart previews.

## Controlled Inputs

Login/registration, upload, library filters, analyzer controls, cleaning options, report chart forms, and XLSX selections keep their values in React state. Each input receives a `value` and an `onChange` handler, so the rendered form reflects application state.

## Events

The frontend handles form submission, button clicks, file selection, filter changes, modal confirmation, downloads, sign-out, and report chart editing through React event handlers. Default browser form submission is prevented when the action must call the API without a page reload.

## Conditional Rendering

Pages render different states for:

- initial loading;
- empty collections;
- successful upload/conversion/report creation;
- controlled API errors;
- expired authentication;
- selected files and pending deletion;
- generated report downloads that become stale after chart edits.

## Dynamic Rendering

Files, reports, categories, statistics, missing values, analysis previews, cleaning previews, chart configurations, and Plotly figures are rendered from arrays/objects returned by FastAPI. Stable database IDs are used as React keys where available.

## `useRef` DOM Example

The upload page keeps a reference to the hidden native file input. Clicking the custom drop-zone/button calls the DOM input's `.click()` method. Removing a selected file also clears the native input value through the ref so selecting the same file again fires a change event.

This is the project's deliberate direct-DOM example. All other UI state remains declarative.

## Routing

React Router provides:

- public `/login`;
- protected application routes;
- a shared layout through nested routes;
- redirects from `/` and unknown routes;
- a compatibility redirect from `/xlsx-converter` to `/xlsx-to-csv`.

Azure Static Web Apps must serve the React entry point for direct navigation to nested client routes.

## API and Authentication State

Axios uses `VITE_API_BASE_URL`. A request interceptor attaches the bearer token. A centralized response interceptor handles `401` by removing the token and notifying `AuthProvider`, which sends the user back to the login flow.

`AuthProvider` decodes the JWT's public payload to restore the displayed user and reject an already expired browser session. The backend remains authoritative: decoding in React is not authorization.

## Downloads

Authenticated downloads request binary data through Axios, create a temporary object URL, invoke a browser download through a short-lived anchor element, and revoke the object URL afterward.

## Chart Rendering

The backend returns Plotly-compatible figure JSON. The reusable chart preview component renders supported Cartesian charts in React. Report HTML/PDF generation remains a backend responsibility.

## Current Frontend Limitations

- Authentication uses local storage rather than secure HTTP-only cookies.
- The chart library makes the production JavaScript bundle large.
- The UI targets modern browsers and has not undergone a formal accessibility audit.
- The accepted lint baseline includes non-blocking effect-state warnings in initial session/page loading code.
