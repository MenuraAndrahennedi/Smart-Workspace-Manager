import { useCallback, useEffect, useState } from "react";
import { apiClient, getErrorMessage } from "../api/client";
import FileName from "../components/FileName";
import { formatBytes, formatDate } from "../utils/formatters";

function DashboardPage() {
  const [dashboard, setDashboard] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");

  const loadDashboard = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage("");

    try {
      const response = await apiClient.get("/api/dashboard/");
      setDashboard(response.data);
    } catch (error) {
      setErrorMessage(getErrorMessage(error, "Could not load the dashboard."));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  if (isLoading) return <div className="page-state">Loading dashboard...</div>;

  if (errorMessage) {
    return (
      <div className="page-state">
        <p className="alert error">{errorMessage}</p>
        <button className="button secondary" onClick={loadDashboard}>Try again</button>
      </div>
    );
  }

  const metrics = [
    ["Total files", dashboard.total_files],
    ["Storage used", formatBytes(dashboard.total_size_bytes)],
    ["Organized", dashboard.organized_files],
    ["Failed", dashboard.failed_files],
  ];

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Overview</p>
          <h1>Dashboard</h1>
          <p className="muted">A quick view of your workspace.</p>
        </div>
        <button className="button secondary" onClick={loadDashboard}>Refresh</button>
      </header>

      <section className="metric-grid">
        {metrics.map(([label, value]) => (
          <article className="metric-card" key={label}>
            <p>{label}</p>
            <strong>{value}</strong>
          </article>
        ))}
      </section>

      <div className="content-grid">
        <section className="panel">
          <div className="panel-heading">
            <h2>Categories</h2>
          </div>
          {dashboard.category_summary.length === 0 ? (
            <p className="empty-text">No categorized files yet.</p>
          ) : (
            <div className="simple-list">
              {dashboard.category_summary.map((item) => (
                <div className="simple-list-row" key={item.category}>
                  <div>
                    <strong>{item.category}</strong>
                    <span>{item.file_count} files</span>
                  </div>
                  <span>{formatBytes(item.total_size_bytes)}</span>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="panel wide-panel">
          <div className="panel-heading">
            <h2>Recent files</h2>
          </div>
          {dashboard.recent_files.length === 0 ? (
            <p className="empty-text">Upload a file to begin.</p>
          ) : (
            <div className="table-wrap">
              <table>
                <thead><tr><th>Name</th><th>Category</th><th>Size</th><th>Added</th></tr></thead>
                <tbody>
                  {dashboard.recent_files.map((file) => (
                    <tr key={file.id}>
                      <td className="file-name">
                        <FileName name={file.original_name} extension={file.extension} />
                      </td>
                      <td><span className="badge">{file.category}</span></td>
                      <td>{formatBytes(file.size_bytes)}</td>
                      <td>{formatDate(file.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

export default DashboardPage;
