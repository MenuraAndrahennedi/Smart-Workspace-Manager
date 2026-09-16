import { useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { getErrorMessage } from "../api/client";
import useAuth from "../context/useAuth";

function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { isAuthenticated, isCheckingAuthentication, login, register } = useAuth();
  const [isRegistering, setIsRegistering] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setErrorMessage("");
    setIsSubmitting(true);

    try {
      if (isRegistering) {
        await register(email, password);
      } else {
        await login(email, password);
      }
      const destination = location.state?.from?.pathname || "/dashboard";
      navigate(destination, { replace: true });
    } catch (error) {
      setErrorMessage(getErrorMessage(error, error.message || "Login failed."));
    } finally {
      setIsSubmitting(false);
    }
  }

  if (isCheckingAuthentication) {
    return <main className="centered-state">Checking your session...</main>;
  }

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <main className="login-page">
      <section className="login-card">
        <div className="wordmark">SW</div>
        <p className="eyebrow">Smart Workspace Manager</p>
        <h1>{isRegistering ? "Create account" : "Sign in"}</h1>
        <p className="muted">
          {isRegistering
            ? "Register with your email and a secure password."
            : "Access your files and workspace overview."}
        </p>

        <form className="form-stack" onSubmit={handleSubmit}>
          <label htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
            value={email}
            autoComplete="email"
            required
            onChange={(event) => setEmail(event.target.value)}
          />

          <label htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            value={password}
            autoComplete={isRegistering ? "new-password" : "current-password"}
            minLength={isRegistering ? 8 : undefined}
            required
            onChange={(event) => setPassword(event.target.value)}
          />

          {isRegistering && (
            <small className="form-help">Use at least 8 characters.</small>
          )}

          {errorMessage && <p className="alert error">{errorMessage}</p>}

          <button className="button primary" type="submit" disabled={isSubmitting}>
            {isSubmitting
              ? (isRegistering ? "Creating account..." : "Signing in...")
              : (isRegistering ? "Create account" : "Sign in")}
          </button>

          <button
            className="auth-switch"
            type="button"
            disabled={isSubmitting}
            onClick={() => {
              setIsRegistering((current) => !current);
              setErrorMessage("");
            }}
          >
            {isRegistering
              ? "Already have an account? Sign in"
              : "New here? Create an account"}
          </button>
        </form>
      </section>
    </main>
  );
}

export default LoginPage;
