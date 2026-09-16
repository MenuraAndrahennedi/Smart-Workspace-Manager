import { Navigate, useLocation } from "react-router-dom";
import useAuth from "../context/useAuth";

function ProtectedRoute({ children }) {
  const location = useLocation();
  const { isAuthenticated, isCheckingAuthentication } = useAuth();

  if (isCheckingAuthentication) {
    return (
      <main className="centered-state">
        <div className="spinner" aria-hidden="true" />
        <p>Checking your session...</p>
      </main>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return children;
}

export default ProtectedRoute;
