import { useEffect, useMemo, useState } from "react";
import { apiClient, getErrorMessage } from "../api/client";
import { downloadAuthenticatedFile } from "../api/download";
import CsvFileSelect from "../components/CsvFileSelect";
import DataTable from "../components/DataTable";

function isNumericType(type = "") {
  return /int|float|double|decimal/.test(type.toLowerCase());
}

function CleaningPage() {
  const [files, setFiles] = useState([]);
  const [fileId, setFileId] = useState("");
  const [analysis, setAnalysis] = useState(null);
  const [result, setResult] = useState(null);
  const [savedResult, setSavedResult] = useState(null);
  const [removeDuplicates, setRemoveDuplicates] = useState(false);
  const [numericColumn, setNumericColumn] = useState("");
  const [numericStrategy, setNumericStrategy] = useState("mean");
  const [numericValue, setNumericValue] = useState(0);
  const [textColumn, setTextColumn] = useState("");
  const [textValue, setTextValue] = useState("");
  const [dropMissingRows, setDropMissingRows] = useState(false);
  const [busyAction, setBusyAction] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [isLoadingFiles, setIsLoadingFiles] = useState(true);

  useEffect(() => {
    apiClient.get("/api/analyzer/analyzable_files")
      .then((response) => setFiles(response.data))
      .catch((error) => setErrorMessage(getErrorMessage(error, "Could not load CSV files.")))
      .finally(() => setIsLoadingFiles(false));
  }, []);

  const columns = useMemo(() => analysis?.result?.columns || [], [analysis]);
  const numericColumns = useMemo(
    () => columns.filter((column) => isNumericType(analysis?.result?.data_types[column])),
    [analysis, columns],
  );
  const textColumns = useMemo(
    () => columns.filter((column) => !isNumericType(analysis?.result?.data_types[column])),
    [analysis, columns],
  );

  function selectFile(nextFileId) {
    setFileId(nextFileId);
    setAnalysis(null);
    setResult(null);
    setSavedResult(null);
    setErrorMessage("");
    setSuccessMessage("");
  }

  async function loadFile() {
    setBusyAction("load");
    setErrorMessage("");
    try {
      const response = await apiClient.post(`/api/analyzer/analysis/${fileId}`, null, { params: { preview_rows: 10 } });
      setAnalysis(response.data);
    } catch (error) {
      setErrorMessage(getErrorMessage(error, "Could not inspect this CSV file."));
    } finally {
      setBusyAction("");
    }
  }

  async function previewCleaning(event) {
    event.preventDefault();
    setBusyAction("preview");
    setErrorMessage("");
    setSuccessMessage("");
    setSavedResult(null);

    const options = {
      remove_duplicates: removeDuplicates,
      duplicate_columns: null,
      numeric_fill_column: numericColumn || null,
      numeric_fill_strategy: numericColumn ? numericStrategy : null,
      numeric_fill_value: numericColumn && numericStrategy === "constant" ? Number(numericValue) : null,
      text_fill_column: textColumn || null,
      text_fill_value: textColumn ? textValue : null,
      drop_missing_rows: dropMissingRows,
      drop_missing_columns: null,
    };

    try {
      const response = await apiClient.post(`/api/cleaning/${fileId}`, options);
      setResult(response.data);
    } catch (error) {
      setErrorMessage(getErrorMessage(error, "Could not preview the cleaning result."));
    } finally {
      setBusyAction("");
    }
  }

  async function saveResult() {
    setBusyAction("save");
    setErrorMessage("");
    setSuccessMessage("");
    try {
      const response = await apiClient.post(
        `/api/cleaning/save_cleaning_results/${fileId}`,
        result.cleaned_dataframe,
      );
      setSavedResult(response.data);
      setSuccessMessage("Cleaned CSV and Excel files were saved to your library.");
    } catch (error) {
      setErrorMessage(getErrorMessage(error, "Could not save the cleaned files."));
    } finally {
      setBusyAction("");
    }
  }

  async function downloadFile(id, filename) {
    setErrorMessage("");
    try {
      await downloadAuthenticatedFile(`/api/files/${id}/download`, filename);
    } catch (error) {
      setErrorMessage(getErrorMessage(error, "Could not download the cleaned file."));
    }
  }

  return (
    <div className="page">
      <header className="page-header"><div><p className="eyebrow">Data tools</p><h1>CSV Cleaning</h1><p className="muted">Preview safe cleaning changes before saving new CSV and Excel files.</p></div></header>
      {errorMessage && <p className="alert error">{errorMessage}</p>}
      {successMessage && <p className="alert success">{successMessage}</p>}

      <section className="panel section-stack">
        <h2>Select data</h2>
        {isLoadingFiles ? <p className="empty-text">Loading CSV files...</p> : files.length === 0 ? <p className="empty-text">No organized CSV files are available.</p> : (
          <div className="inline-form">
            <CsvFileSelect files={files} value={fileId} onChange={selectFile} />
            <button type="button" className="button secondary" disabled={!fileId || busyAction === "load"} onClick={loadFile}>{busyAction === "load" ? "Loading..." : "Load columns"}</button>
          </div>
        )}
      </section>

      {analysis && (
        <section className="panel section-stack">
          <h2>Cleaning options</h2>
          <form className="form-stack" onSubmit={previewCleaning}>
            <label className="check-option"><input type="checkbox" checked={removeDuplicates} onChange={(event) => setRemoveDuplicates(event.target.checked)} />Remove duplicate rows</label>
            <div className="form-grid">
              <select value={numericColumn} onChange={(event) => setNumericColumn(event.target.value)}><option value="">Do not fill a numeric column</option>{numericColumns.map((column) => <option key={column}>{column}</option>)}</select>
              <select value={numericStrategy} disabled={!numericColumn} onChange={(event) => setNumericStrategy(event.target.value)}><option value="mean">Fill with mean</option><option value="median">Fill with median</option><option value="constant">Fill with a value</option></select>
              {numericStrategy === "constant" && <input type="number" value={numericValue} disabled={!numericColumn} aria-label="Numeric fill value" onChange={(event) => setNumericValue(event.target.value)} />}
            </div>
            <div className="form-grid">
              <select value={textColumn} onChange={(event) => setTextColumn(event.target.value)}><option value="">Do not fill a text column</option>{textColumns.map((column) => <option key={column}>{column}</option>)}</select>
              <input value={textValue} disabled={!textColumn} placeholder="Text replacement" onChange={(event) => setTextValue(event.target.value)} />
            </div>
            <label className="check-option"><input type="checkbox" checked={dropMissingRows} onChange={(event) => setDropMissingRows(event.target.checked)} />Drop rows that still contain missing values</label>
            <button className="button primary" disabled={busyAction === "preview"}>{busyAction === "preview" ? "Cleaning..." : "Preview cleaning"}</button>
          </form>
        </section>
      )}

      {result && (
        <>
          <section className="metric-grid data-metrics">
            <article className="metric-card"><p>Original rows</p><strong>{result.original_row_count}</strong></article>
            <article className="metric-card"><p>Cleaned rows</p><strong>{result.cleaned_row_count}</strong></article>
            <article className="metric-card"><p>Duplicates removed</p><strong>{result.duplicates_removed}</strong></article>
            <article className="metric-card"><p>Missing remaining</p><strong>{result.remaining_missing_values}</strong></article>
          </section>
          <section className="panel section-stack">
            <div className="section-heading"><div><h2>Cleaned preview</h2><p className="muted">{result.missing_values_filled} values filled · {result.rows_dropped} rows dropped</p></div><button type="button" className="button primary" disabled={busyAction === "save"} onClick={saveResult}>{busyAction === "save" ? "Saving..." : "Save cleaned files"}</button></div>
            <DataTable rows={result.cleaned_dataframe} />
            {savedResult && <div className="result-actions"><button type="button" className="button secondary" onClick={() => downloadFile(savedResult.csv_file_id, savedResult.csv_filename)}>Download CSV</button><button type="button" className="button secondary" onClick={() => downloadFile(savedResult.excel_file_id, savedResult.excel_filename)}>Download Excel</button></div>}
          </section>
        </>
      )}
    </div>
  );
}

export default CleaningPage;
