import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiClient, getErrorMessage } from "../api/client";
import { downloadAuthenticatedFile } from "../api/download";
import FileName from "../components/FileName";
import { formatBytes } from "../utils/formatters";

function XlsxConverterPage() {
  const [files, setFiles] = useState([]);
  const [fileId, setFileId] = useState("");
  const [sheets, setSheets] = useState([]);
  const [sheetName, setSheetName] = useState("");
  const [convertedFile, setConvertedFile] = useState(null);
  const [isLoadingFiles, setIsLoadingFiles] = useState(true);
  const [isLoadingSheets, setIsLoadingSheets] = useState(false);
  const [isConverting, setIsConverting] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    apiClient.get("/api/xlsx/files")
      .then((response) => setFiles(response.data))
      .catch((error) => setErrorMessage(getErrorMessage(error, "Could not load XLSX files.")))
      .finally(() => setIsLoadingFiles(false));
  }, []);

  async function selectWorkbook(nextFileId) {
    setFileId(nextFileId);
    setSheets([]);
    setSheetName("");
    setConvertedFile(null);
    setErrorMessage("");

    if (!nextFileId) return;

    setIsLoadingSheets(true);
    try {
      const response = await apiClient.get(`/api/xlsx/files/${nextFileId}/sheets`);
      setSheets(response.data);
      setSheetName(response.data[0] || "");
    } catch (error) {
      setErrorMessage(getErrorMessage(error, "Could not load workbook sheets."));
    } finally {
      setIsLoadingSheets(false);
    }
  }

  async function convertWorkbook(event) {
    event.preventDefault();
    setIsConverting(true);
    setConvertedFile(null);
    setErrorMessage("");

    try {
      const response = await apiClient.post(
        `/api/xlsx/files/${fileId}/convert`,
        { sheet_name: sheetName },
      );
      setConvertedFile(response.data);
    } catch (error) {
      setErrorMessage(getErrorMessage(error, "Could not convert the selected sheet."));
    } finally {
      setIsConverting(false);
    }
  }

  async function downloadConvertedFile() {
    setIsDownloading(true);
    setErrorMessage("");
    try {
      await downloadAuthenticatedFile(
        `/api/files/${convertedFile.id}/download`,
        convertedFile.original_name,
      );
    } catch (error) {
      setErrorMessage(getErrorMessage(error, "Could not download the converted CSV file."));
    } finally {
      setIsDownloading(false);
    }
  }

  const selectedFile = files.find((file) => String(file.id) === String(fileId));

  return (
    <div className="page narrow-page">
      <header className="page-header">
        <div>
          <p className="eyebrow">File tools</p>
          <h1>XLSX to CSV</h1>
          <p className="muted">Choose one workbook sheet and save it as an organized CSV file.</p>
        </div>
      </header>

      {errorMessage && <p className="alert error">{errorMessage}</p>}

      <section className="panel section-stack">
        <h2>Select workbook</h2>

        {isLoadingFiles ? (
          <p className="empty-text">Loading XLSX files...</p>
        ) : files.length === 0 ? (
          <p className="empty-text">No XLSX files are available. Upload one from the Upload page first.</p>
        ) : (
          <form className="form-stack" onSubmit={convertWorkbook}>
            <select
              aria-label="XLSX workbook"
              value={fileId}
              onChange={(event) => selectWorkbook(event.target.value)}
              required
            >
              <option value="">Select an XLSX file</option>
              {files.map((file) => <option key={file.id} value={file.id}>{file.original_name}</option>)}
            </select>

            {selectedFile && (
              <div className="selected-workbook">
                <FileName name={selectedFile.original_name} extension={selectedFile.extension} />
                <span>{formatBytes(selectedFile.size_bytes)}</span>
              </div>
            )}

            <select
              aria-label="Workbook sheet"
              value={sheetName}
              onChange={(event) => setSheetName(event.target.value)}
              disabled={!fileId || isLoadingSheets}
              required
            >
              <option value="">{isLoadingSheets ? "Loading sheets..." : "Select a sheet"}</option>
              {sheets.map((sheet) => <option key={sheet} value={sheet}>{sheet}</option>)}
            </select>

            {fileId && !isLoadingSheets && sheets.length === 0 && (
              <p className="empty-text">This workbook contains no readable sheets.</p>
            )}

            <button className="button primary" disabled={!sheetName || isConverting}>
              {isConverting ? "Converting..." : "Convert to CSV"}
            </button>
          </form>
        )}
      </section>

      {convertedFile && (
        <section className="panel section-stack conversion-result" aria-live="polite">
          <div>
            <p className="eyebrow">Conversion complete</p>
            <h2>CSV file created</h2>
          </div>
          <div className="converted-file-details">
            <FileName name={convertedFile.original_name} extension={convertedFile.extension} size="large" />
            <span>{formatBytes(convertedFile.size_bytes)} · {convertedFile.status}</span>
          </div>
          <div className="result-actions">
            <button type="button" className="button primary" disabled={isDownloading} onClick={downloadConvertedFile}>
              {isDownloading ? "Downloading..." : "Download CSV"}
            </button>
            <Link className="button secondary button-link" to="/library">View in library</Link>
          </div>
        </section>
      )}
    </div>
  );
}

export default XlsxConverterPage;
