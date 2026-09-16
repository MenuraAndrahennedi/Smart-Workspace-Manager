import { useCallback, useEffect, useState } from "react";
import { apiClient, getErrorMessage } from "../api/client";
import { downloadAuthenticatedFile } from "../api/download";
import FileName from "../components/FileName";
import FileTypeIcon from "../components/FileTypeIcon";
import { formatBytes, formatDate } from "../utils/formatters";

function DashboardPage() {
  const [dashboard, setDashboard] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");
  const [busyFileId, setBusyFileId] = useState(null);
  const [filePendingDelete, setFilePendingDelete] = useState(null);

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

  async function downloadFile(file) {
    setBusyFileId(file.id);
    setErrorMessage("");
    try {
      await downloadAuthenticatedFile(
        `/api/files/${file.id}/download`,
        file.original_name,
      );
    } catch (error) {
      setErrorMessage(getErrorMessage(error, "Could not download the file."));
    } finally {
      setBusyFileId(null);
    }
  }

  async function removeFile(file) {
    setBusyFileId(file.id);
    setErrorMessage("");
    try {
      await apiClient.delete(`/api/files/${file.id}`);
      setFilePendingDelete(null);
      await loadDashboard();
    } catch (error) {
      setErrorMessage(getErrorMessage(error, "Could not delete the file."));
    } finally {
      setBusyFileId(null);
    }
  }

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
                <div className="simple-list-row category-row" key={item.category}>
                  <FileTypeIcon category={item.category} size="small" />
                  <div className="category-details">
                    <strong>{item.category}</strong>
                    <span>{item.file_count} files</span>
                  </div>
                  <span className="category-size">{formatBytes(item.total_size_bytes)}</span>
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
                <thead><tr><th>Name</th><th>Category</th><th>Size</th><th>Added</th><th>Actions</th></tr></thead>
                <tbody>
                  {dashboard.recent_files.map((file) => (
                    <tr key={file.id}>
                      <td className="file-name">
                        <FileName name={file.original_name} extension={file.extension} />
                      </td>
                      <td><span className="badge">{file.category}</span></td>
                      <td>{formatBytes(file.size_bytes)}</td>
                      <td>{formatDate(file.created_at)}</td>
                      <td>
                        <div className="table-actions">
                          <button className="text-button" disabled={busyFileId === file.id} onClick={() => downloadFile(file)}>Download</button>
                          <button className="text-button danger" disabled={busyFileId === file.id} onClick={() => setFilePendingDelete(file)}>Delete</button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>

      {filePendingDelete && (
        <div className="modal-backdrop" role="presentation">
          <section className="modal" role="dialog" aria-modal="true" aria-labelledby="dashboard-delete-title">
            <div className="modal-mark" aria-hidden="true">!</div>
            <h2 id="dashboard-delete-title">Delete this file?</h2>
            <div className="modal-file">
              <FileName name={filePendingDelete.original_name} extension={filePendingDelete.extension} />
            </div>
            <p className="muted">The file and its database record will be removed permanently.</p>
            <div className="modal-actions">
              <button className="button secondary" type="button" onClick={() => setFilePendingDelete(null)} disabled={busyFileId === filePendingDelete.id}>Cancel</button>
              <button className="button danger-button" type="button" onClick={() => removeFile(filePendingDelete)} disabled={busyFileId === filePendingDelete.id}>
                {busyFileId === filePendingDelete.id ? "Deleting..." : "Delete file"}
              </button>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}

export default DashboardPage;
