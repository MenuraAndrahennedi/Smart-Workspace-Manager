import { useCallback, useEffect, useState } from "react";
import { apiClient, getErrorMessage } from "../api/client";
import FileName from "../components/FileName";
import { formatBytes, formatDate } from "../utils/formatters";

function LibraryPage() {
  const [files, setFiles] = useState([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [category, setCategory] = useState("");
  const [status, setStatus] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");
  const [busyFileId, setBusyFileId] = useState(null);
  const [filePendingDelete, setFilePendingDelete] = useState(null);

  const loadFiles = useCallback(async (filters = {}) => {
    setIsLoading(true);
    setErrorMessage("");

    try {
      const response = await apiClient.get("/api/files/", { params: filters });
      setFiles(response.data);
    } catch (error) {
      setErrorMessage(getErrorMessage(error, "Could not load your files."));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadFiles();
  }, [loadFiles]);

  function applyFilters(event) {
    event.preventDefault();
    loadFiles({
      search_term: searchTerm || undefined,
      category: category || undefined,
      status: status || undefined,
    });
  }

  function clearFilters() {
    setSearchTerm("");
    setCategory("");
    setStatus("");
    loadFiles();
  }

  async function downloadFile(file) {
    setBusyFileId(file.id);
    setErrorMessage("");

    try {
      const response = await apiClient.get(`/api/files/${file.id}/download`, {
        responseType: "blob",
      });
      const url = URL.createObjectURL(response.data);
      const link = document.createElement("a");
      link.href = url;
      link.download = file.original_name;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
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
      setFiles((currentFiles) => currentFiles.filter((item) => item.id !== file.id));
      setFilePendingDelete(null);
    } catch (error) {
      setErrorMessage(getErrorMessage(error, "Could not delete the file."));
    } finally {
      setBusyFileId(null);
    }
  }

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Your workspace</p>
          <h1>File library</h1>
          <p className="muted">Search, filter, download, and remove your files.</p>
        </div>
      </header>

      <form className="filter-bar" onSubmit={applyFilters}>
        <input
          aria-label="Search files"
          type="search"
          placeholder="Search by filename"
          value={searchTerm}
          onChange={(event) => setSearchTerm(event.target.value)}
        />
        <select value={category} onChange={(event) => setCategory(event.target.value)}>
          <option value="">All categories</option>
          <option value="spreadsheets">Spreadsheets</option>
          <option value="documents">Documents</option>
          <option value="images">Images</option>
          <option value="pdf">PDF</option>
          <option value="others">Others</option>
        </select>
        <select value={status} onChange={(event) => setStatus(event.target.value)}>
          <option value="">All statuses</option>
          <option value="organized">Organized</option>
          <option value="uploaded">Uploaded</option>
          <option value="failed">Failed</option>
        </select>
        <button className="button primary" type="submit">Apply</button>
        <button className="button secondary" type="button" onClick={clearFilters}>Clear</button>
      </form>

      {errorMessage && <p className="alert error">{errorMessage}</p>}

      <section className="panel">
        {isLoading ? (
          <p className="empty-text">Loading files...</p>
        ) : files.length === 0 ? (
          <p className="empty-text">No files match your current filters.</p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Name</th><th>Category</th><th>Status</th><th>Size</th><th>Added</th><th>Actions</th></tr></thead>
              <tbody>
                {files.map((file) => (
                  <tr key={file.id}>
                    <td className="file-name">
                      <FileName name={file.original_name} extension={file.extension} />
                    </td>
                    <td>{file.category}</td>
                    <td><span className="badge">{file.status}</span></td>
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

      {filePendingDelete && (
        <div className="modal-backdrop" role="presentation">
          <section
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="delete-dialog-title"
          >
            <div className="modal-mark" aria-hidden="true">!</div>
            <h2 id="delete-dialog-title">Delete this file?</h2>
            <div className="modal-file">
              <FileName
                name={filePendingDelete.original_name}
                extension={filePendingDelete.extension}
              />
            </div>
            <p className="muted">
              This file will be removed permanently. This action cannot be undone.
            </p>

            <div className="modal-actions">
              <button
                className="button secondary"
                type="button"
                onClick={() => setFilePendingDelete(null)}
                disabled={busyFileId === filePendingDelete.id}
              >
                Cancel
              </button>
              <button
                className="button danger-button"
                type="button"
                onClick={() => removeFile(filePendingDelete)}
                disabled={busyFileId === filePendingDelete.id}
              >
                {busyFileId === filePendingDelete.id ? "Deleting..." : "Delete file"}
              </button>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}

export default LibraryPage;
