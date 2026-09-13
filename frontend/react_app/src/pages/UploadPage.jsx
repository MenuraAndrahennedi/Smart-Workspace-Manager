import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { apiClient, getErrorMessage } from "../api/client";
import FileName from "../components/FileName";
import FileTypeIcon from "../components/FileTypeIcon";
import { formatBytes } from "../utils/formatters";

function UploadPage() {
  const fileInputRef = useRef(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [settings, setSettings] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [uploadedFile, setUploadedFile] = useState(null);

  useEffect(() => {
    apiClient.get("/api/settings/public")
      .then((response) => setSettings(response.data))
      .catch(() => setSettings(null));
  }, []);

  function selectFile(event) {
    setSelectedFile(event.target.files?.[0] || null);
    setUploadedFile(null);
    setErrorMessage("");
  }

  function removeSelectedFile() {
    setSelectedFile(null);
    setErrorMessage("");

    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }

  async function uploadSelectedFile(event) {
    event.preventDefault();
    if (!selectedFile) return;

    if (settings && selectedFile.size > settings.max_upload_size_bytes) {
      setErrorMessage(`The file exceeds the ${settings.max_upload_size_mb} MB limit.`);
      return;
    }

    setIsUploading(true);
    setErrorMessage("");

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      const response = await apiClient.post("/api/files/upload", formData);
      setUploadedFile(response.data);
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    } catch (error) {
      setErrorMessage(getErrorMessage(error, "Could not upload the file."));
    } finally {
      setIsUploading(false);
    }
  }

  const acceptedTypes = settings
    ? settings.supported_file_types.map((extension) => `.${extension}`).join(",")
    : undefined;

  return (
    <div className="page narrow-page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Add content</p>
          <h1>Upload file</h1>
          <p className="muted">Choose one supported file to add to your workspace.</p>
        </div>
      </header>

      <section className="panel upload-panel">
        <form onSubmit={uploadSelectedFile}>
          <input
            ref={fileInputRef}
            className="visually-hidden"
            id="file-upload"
            type="file"
            accept={acceptedTypes}
            onChange={selectFile}
          />

          {!selectedFile ? (
            <button
              className="file-picker"
              type="button"
              onClick={() => fileInputRef.current?.click()}
            >
              <span className="file-picker-icon">+</span>
              <strong>Choose a file</strong>
              <span>
                {settings
                  ? `Maximum ${settings.max_upload_size_mb} MB`
                  : "Select from your computer"}
              </span>
            </button>
          ) : (
            <div className="selected-file">
              <FileTypeIcon fileName={selectedFile.name} size="large" />

              <div className="selected-file-details">
                <span>Selected file</span>
                <strong>{selectedFile.name}</strong>
                <small>
                  {formatBytes(selectedFile.size)}
                  {selectedFile.type ? ` - ${selectedFile.type}` : ""}
                </small>
              </div>

              <button
                className="button secondary"
                type="button"
                onClick={removeSelectedFile}
                disabled={isUploading}
              >
                Remove selected file
              </button>
            </div>
          )}

          {errorMessage && <p className="alert error">{errorMessage}</p>}
          {uploadedFile && (
            <div className="alert success">
              <FileName
                name={uploadedFile.original_name}
                extension={uploadedFile.extension}
              />
              <span>
                Uploaded and organized. <Link to="/library">Open library</Link>
              </span>
            </div>
          )}

          {selectedFile && (
            <button
              className="button primary"
              type="submit"
              disabled={isUploading}
            >
              {isUploading ? "Uploading..." : "Upload file"}
            </button>
          )}
        </form>
      </section>
    </div>
  );
}

export default UploadPage;
