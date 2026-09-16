import { Navigate, Route, Routes } from "react-router-dom";
import ProtectedRoute from "../components/ProtectedRoute";
import AppLayout from "../layouts/AppLayout";
import DashboardPage from "../pages/DashboardPage";
import LibraryPage from "../pages/LibraryPage";
import LoginPage from "../pages/LoginPage";
import UploadPage from "../pages/UploadPage";
import AnalyzerPage from "../pages/AnalyzerPage";
import CleaningPage from "../pages/CleaningPage";
import ReportsPage from "../pages/ReportsPage";
import XlsxConverterPage from "../pages/XlsxConverterPage";

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/library" element={<LibraryPage />} />
        <Route path="/xlsx-to-csv" element={<XlsxConverterPage />} />
        <Route path="/analyzer" element={<AnalyzerPage />} />
        <Route path="/cleaning" element={<CleaningPage />} />
        <Route path="/reports" element={<ReportsPage />} />
        <Route path="/xlsx-converter" element={<Navigate to="/xlsx-to-csv" replace />} />
      </Route>

      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

export default AppRoutes;
