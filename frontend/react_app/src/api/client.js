import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

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

  if (serverMessage) return serverMessage;
  if (error.response?.status === 401) return "Your session has expired. Please sign in again.";
  if (error.response?.status === 403) return "You do not have permission to access this resource.";
  return fallbackMessage;
}
