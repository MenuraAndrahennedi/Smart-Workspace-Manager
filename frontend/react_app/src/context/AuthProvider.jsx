import { useEffect, useMemo, useState } from "react";
import { apiClient } from "../api/client";
import { AuthContext } from "./AuthContext";

function readUserFromToken(token) {
  try {
    const payloadPart = token.split(".")[1];
    const base64 = payloadPart.replace(/-/g, "+").replace(/_/g, "/");
    const paddedBase64 = base64.padEnd(Math.ceil(base64.length / 4) * 4, "=");
    const payload = JSON.parse(atob(paddedBase64));

    if (!payload.sub || !payload.email || payload.exp * 1000 <= Date.now()) {
      return null;
    }

    return { id: Number(payload.sub), email: payload.email };
  } catch {
    return null;
  }
}

function AuthProvider({ children }) {
  const [currentUser, setCurrentUser] = useState(null);
  const [isCheckingAuthentication, setIsCheckingAuthentication] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    const restoredUser = token ? readUserFromToken(token) : null;

    if (token && !restoredUser) {
      localStorage.removeItem("access_token");
    }

    setCurrentUser(restoredUser);
    setIsCheckingAuthentication(false);
  }, []);

  useEffect(() => {
    function handleUnauthorized() {
      setCurrentUser(null);
    }

    window.addEventListener("auth:unauthorized", handleUnauthorized);
    return () => window.removeEventListener("auth:unauthorized", handleUnauthorized);
  }, []);

  async function login(email, password) {
    const formData = new URLSearchParams();
    formData.append("username", email);
    formData.append("password", password);

    const response = await apiClient.post("/api/auth/login", formData, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });

    const token = response.data.access_token;
    const user = readUserFromToken(token);

    if (!user) {
      throw new Error("The server returned an invalid access token.");
    }

    localStorage.setItem("access_token", token);
    setCurrentUser(user);
  }

  async function register(email, password) {
    const response = await apiClient.post("/api/auth/register", {
      email,
      password,
    });
    const token = response.data.access_token;
    const user = readUserFromToken(token);

    if (!user) {
      throw new Error("The server returned an invalid access token.");
    }

    localStorage.setItem("access_token", token);
    setCurrentUser(user);
  }

  function logout() {
    localStorage.removeItem("access_token");
    setCurrentUser(null);
  }

  const authValue = useMemo(
    () => ({
      currentUser,
      isAuthenticated: currentUser !== null,
      isCheckingAuthentication,
      login,
      register,
      logout,
    }),
    [currentUser, isCheckingAuthentication],
  );

  return (
    <AuthContext.Provider value={authValue}>{children}</AuthContext.Provider>
  );
}

export default AuthProvider;
