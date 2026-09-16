import axios from "axios";

const configuredApiUrl = import.meta.env.VITE_API_BASE_URL;

if (!configuredApiUrl) {
  throw new Error("VITE_API_BASE_URL is not configured.");
}

const API_BASE_URL = configuredApiUrl.replace(/\/+$/, "");

export const apiClient = axios.create({ baseURL: API_BASE_URL });

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("access_token");
      window.dispatchEvent(new Event("auth:unauthorized"));
    }

    return Promise.reject(error);
  },
);

export function getErrorMessage(error, fallbackMessage) {
  const serverMessage = error.response?.data?.message || error.response?.data?.detail;

  if (typeof serverMessage === "string") return serverMessage;
  if (Array.isArray(serverMessage)) {
    return serverMessage
      .map((item) => item?.msg || String(item))
      .join("; ");
  }
  if (error.response?.status === 401) return "Your session has expired. Please sign in again.";
  if (error.response?.status === 403) return "You do not have permission to access this resource.";
  return fallbackMessage;
}
