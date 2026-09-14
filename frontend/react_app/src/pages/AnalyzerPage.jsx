import { useEffect, useMemo, useState } from "react";
import { apiClient, getErrorMessage } from "../api/client";
import ChartPreview from "../components/ChartPreview";
import CsvFileSelect from "../components/CsvFileSelect";
import DataTable from "../components/DataTable";

function isNumericType(type = "") {
  return /int|float|double|decimal/.test(type.toLowerCase());
}

function AnalyzerPage() {
  const [files, setFiles] = useState([]);
  const [fileId, setFileId] = useState("");
  const [previewRows, setPreviewRows] = useState(10);
  const [analysis, setAnalysis] = useState(null);
  const [filteredRows, setFilteredRows] = useState([]);
  const [hasFiltered, setHasFiltered] = useState(false);
  const [selectedColumns, setSelectedColumns] = useState([]);
  const [filterColumn, setFilterColumn] = useState("");
  const [operator, setOperator] = useState("");
  const [filterValue, setFilterValue] = useState("");
  const [chartType, setChartType] = useState("histogram");
  const [chartTitle, setChartTitle] = useState("Chart preview");
  const [xColumn, setXColumn] = useState("");
  const [yColumn, setYColumn] = useState("");
  const [aggregation, setAggregation] = useState("");
  const [histogramBins, setHistogramBins] = useState(20);
  const [chart, setChart] = useState(null);
  const [isLoadingFiles, setIsLoadingFiles] = useState(true);
  const [busyAction, setBusyAction] = useState("");
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    apiClient.get("/api/analyzer/analyzable_files")
      .then((response) => setFiles(response.data))
      .catch((error) => setErrorMessage(getErrorMessage(error, "Could not load CSV files.")))
      .finally(() => setIsLoadingFiles(false));
  }, []);

  const result = analysis?.result;
  const numericColumns = useMemo(
    () => result?.columns.filter((column) => isNumericType(result.data_types[column])) || [],
    [result],
  );
  const orderedColumns = useMemo(
    () => result?.columns.filter((column) => isNumericType(result.data_types[column]) || /date|time/.test(result.data_types[column].toLowerCase())) || [],
    [result],
  );
  const chartXColumns = chartType === "histogram" || chartType === "scatter"
    ? numericColumns
    : chartType === "line" ? orderedColumns : result?.columns || [];
  const canCreateLineChart = numericColumns.length > 0 && orderedColumns.length > 1;
  const filterOperators = filterColumn && isNumericType(result?.data_types[filterColumn])
    ? ["Equals", "Greater than", "Less than"]
    : ["Contains", "Equals", "Starts with"];

  function resetResults(nextFileId) {
    setFileId(nextFileId);
    setAnalysis(null);
    setFilteredRows([]);
    setHasFiltered(false);
    setChart(null);
    setErrorMessage("");
  }

  async function runAnalysis(event) {
    event.preventDefault();
    setBusyAction("analysis");
    setErrorMessage("");

    try {
      const response = await apiClient.post(
        `/api/analyzer/analysis/${fileId}`,
        null,
        { params: { preview_rows: previewRows } },
      );
      setAnalysis(response.data);
      setSelectedColumns(response.data.result.columns);
      const initialNumericColumns = response.data.result.columns.filter((column) =>
        isNumericType(response.data.result.data_types[column]),
      );
      const initialChartType = initialNumericColumns.length ? "histogram" : "bar";
      setChartType(initialChartType);
      setXColumn(initialNumericColumns[0] || response.data.result.columns[0] || "");
      setYColumn(initialNumericColumns[1] || "");
      setFilteredRows([]);
      setHasFiltered(false);
      setChart(null);
    } catch (error) {
      setErrorMessage(getErrorMessage(error, "Could not analyze the CSV file."));
    } finally {
      setBusyAction("");
    }
  }

  function toggleColumn(column) {
    setSelectedColumns((current) =>
      current.includes(column)
        ? current.filter((item) => item !== column)
        : [...current, column],
    );
  }

  async function applyDataFilter(event) {
    event.preventDefault();
    setBusyAction("filter");
    setErrorMessage("");

    try {
      const params = new URLSearchParams();
      selectedColumns.forEach((column) => params.append("selected_columns", column));
      if (filterColumn) {
        params.append("filter_column", filterColumn);
        params.append("operator", operator);
        params.append("filter_value", filterValue);
      }
      params.append("maximum_result_rows", "100");
      const response = await apiClient.get(
        `/api/analyzer/files/${fileId}/filter`,
        { params },
      );
      setFilteredRows(response.data);
      setHasFiltered(true);
    } catch (error) {
      setErrorMessage(getErrorMessage(error, "Could not filter the CSV data."));
    } finally {
      setBusyAction("");
    }
  }

  async function createChart(event) {
    event.preventDefault();
    setBusyAction("chart");
    setErrorMessage("");

    const configuration = {
      chart_type: chartType,
      title: chartTitle,
      x_column: xColumn || null,
      y_column: ["bar", "line", "scatter"].includes(chartType) ? yColumn || null : null,
      aggregation: chartType === "bar" && yColumn ? aggregation || null : null,
      histogram_bins: chartType === "histogram" ? Number(histogramBins) : null,
    };

    try {
      const response = await apiClient.post(
        `/api/analyzer/files/${fileId}/chart`,
        configuration,
      );
      setChart(response.data);
    } catch (error) {
      setErrorMessage(getErrorMessage(error, "Could not create the chart."));
    } finally {
      setBusyAction("");
    }
  }

  function changeChartType(nextChartType) {
    const nextXColumns = nextChartType === "histogram" || nextChartType === "scatter"
      ? numericColumns
      : nextChartType === "line" ? orderedColumns : result?.columns || [];
    setChartType(nextChartType);
    setXColumn(nextXColumns[0] || "");
    setYColumn(numericColumns.find((column) => column !== nextXColumns[0]) || "");
    setAggregation("");
    setChart(null);
  }

  const missingRows = result
    ? result.columns.map((column) => ({ column, missing_values: result.missing_values[column] }))
    : [];
  const typeRows = result
    ? result.columns.map((column) => ({ column, data_type: result.data_types[column] }))
    : [];

  return (
    <div className="page">
      <header className="page-header"><div><p className="eyebrow">Data tools</p><h1>CSV Analyzer</h1><p className="muted">Inspect, filter, and visualize an organized CSV file.</p></div></header>

      {errorMessage && <p className="alert error">{errorMessage}</p>}

      <section className="panel section-stack">
        <h2>Select data</h2>
        {isLoadingFiles ? <p className="empty-text">Loading CSV files...</p> : files.length === 0 ? <p className="empty-text">No organized CSV files are available.</p> : (
          <form className="inline-form" onSubmit={runAnalysis}>
            <CsvFileSelect files={files} value={fileId} onChange={resetResults} />
            <input type="number" min="1" max="100" value={previewRows} aria-label="Preview rows" onChange={(event) => setPreviewRows(event.target.value)} />
            <button className="button primary" disabled={!fileId || busyAction === "analysis"}>{busyAction === "analysis" ? "Analyzing..." : "Analyze"}</button>
          </form>
        )}
      </section>

      {result && (
        <>
          <section className="metric-grid data-metrics">
            <article className="metric-card"><p>Rows</p><strong>{result.row_count}</strong></article>
            <article className="metric-card"><p>Columns</p><strong>{result.column_count}</strong></article>
            <article className="metric-card"><p>Missing values</p><strong>{Object.values(result.missing_values).reduce((sum, value) => sum + value, 0)}</strong></article>
            <article className="metric-card"><p>Duplicates</p><strong>{result.duplicate_count}</strong></article>
          </section>

          <section className="panel section-stack"><h2>Preview</h2><DataTable rows={result.preview} /></section>

          <div className="content-grid analysis-details">
            <section className="panel section-stack"><h2>Column types</h2><DataTable rows={typeRows} /></section>
            <section className="panel section-stack"><h2>Missing values</h2><DataTable rows={missingRows} /></section>
          </div>

          <section className="panel section-stack"><h2>Descriptive statistics</h2><DataTable rows={result.descriptive_statistics} /></section>

          <section className="panel section-stack">
            <h2>Filter data</h2>
            <form className="form-stack" onSubmit={applyDataFilter}>
              <fieldset className="checkbox-grid"><legend>Displayed columns</legend>{result.columns.map((column) => <label key={column}><input type="checkbox" checked={selectedColumns.includes(column)} onChange={() => toggleColumn(column)} />{column}</label>)}</fieldset>
              <div className="form-grid">
                <select value={filterColumn} onChange={(event) => { setFilterColumn(event.target.value); setOperator(""); }}><option value="">No row filter</option>{result.columns.map((column) => <option key={column}>{column}</option>)}</select>
                <select value={operator} disabled={!filterColumn} onChange={(event) => setOperator(event.target.value)}><option value="">Select operator</option>{filterOperators.map((item) => <option key={item}>{item}</option>)}</select>
                <input value={filterValue} disabled={!filterColumn} placeholder="Filter value" onChange={(event) => setFilterValue(event.target.value)} />
              </div>
              <button className="button secondary" disabled={!selectedColumns.length || busyAction === "filter" || (filterColumn && (!operator || filterValue === ""))}>{busyAction === "filter" ? "Filtering..." : "Apply filter"}</button>
            </form>
            {hasFiltered && <DataTable rows={filteredRows} columns={selectedColumns} emptyMessage="No rows match this filter." />}
          </section>

          <section className="panel section-stack">
            <h2>Create chart</h2>
            <form className="form-stack" onSubmit={createChart}>
              <div className="form-grid">
                <select value={chartType} onChange={(event) => changeChartType(event.target.value)}>{numericColumns.length > 0 && <option value="histogram">Histogram</option>}<option value="bar">Bar</option>{canCreateLineChart && <option value="line">Line</option>}{numericColumns.length > 1 && <option value="scatter">Scatter</option>}</select>
                <input value={chartTitle} placeholder="Chart title" onChange={(event) => setChartTitle(event.target.value)} required />
                <select value={xColumn} onChange={(event) => setXColumn(event.target.value)} required><option value="">X column</option>{chartXColumns.map((column) => <option key={column}>{column}</option>)}</select>
                {chartType !== "histogram" && <select value={yColumn} required={["line", "scatter"].includes(chartType)} onChange={(event) => setYColumn(event.target.value)}><option value="">{chartType === "bar" ? "Count rows" : "Y column"}</option>{numericColumns.map((column) => <option key={column}>{column}</option>)}</select>}
                {chartType === "bar" && yColumn && <select value={aggregation} onChange={(event) => setAggregation(event.target.value)} required><option value="">Aggregation</option>{["Mean", "Sum", "Minimum", "Maximum", "Count"].map((item) => <option key={item}>{item}</option>)}</select>}
                {chartType === "histogram" && <input type="number" min="1" value={histogramBins} aria-label="Histogram bins" onChange={(event) => setHistogramBins(event.target.value)} />}
              </div>
              <button className="button primary" disabled={busyAction === "chart"}>{busyAction === "chart" ? "Creating..." : "Create chart"}</button>
            </form>
            {chart && <><p className="muted">Plotted rows: {chart.plotted_row_count}</p><ChartPreview figure={chart.figure} title={chart.configuration.title} /></>}
          </section>
        </>
      )}
    </div>
  );
}

export default AnalyzerPage;
