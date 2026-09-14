import { useEffect, useMemo, useState } from "react";
import { apiClient, getErrorMessage } from "../api/client";
import { downloadAuthenticatedFile } from "../api/download";
import ChartPreview from "../components/ChartPreview";
import CsvFileSelect from "../components/CsvFileSelect";

const MAX_REPORT_CHARTS = 10;
const AGGREGATIONS = ["Mean", "Sum", "Minimum", "Maximum", "Count"];

function isNumericType(type = "") {
  return /int|float|double|decimal/.test(type.toLowerCase());
}

function isDateType(type = "") {
  return /date|time/.test(type.toLowerCase());
}

function ReportsPage() {
  const [files, setFiles] = useState([]);
  const [fileId, setFileId] = useState("");
  const [analysis, setAnalysis] = useState(null);
  const [charts, setCharts] = useState([]);
  const [isEditingChart, setIsEditingChart] = useState(false);
  const [editingIndex, setEditingIndex] = useState(null);
  const [chartType, setChartType] = useState("histogram");
  const [title, setTitle] = useState("Histogram chart");
  const [xColumn, setXColumn] = useState("");
  const [yColumn, setYColumn] = useState("");
  const [aggregation, setAggregation] = useState("");
  const [histogramBins, setHistogramBins] = useState(20);
  const [createdReport, setCreatedReport] = useState(null);
  const [draftNotice, setDraftNotice] = useState("");
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

  const result = analysis?.result;
  const numericColumns = useMemo(
    () => result?.columns.filter((column) => isNumericType(result.data_types[column])) || [],
    [result],
  );
  const dateColumns = useMemo(
    () => result?.columns.filter((column) => isDateType(result.data_types[column])) || [],
    [result],
  );
  const categoricalColumns = useMemo(
    () => result?.columns.filter((column) => !isNumericType(result.data_types[column]) && !isDateType(result.data_types[column])) || [],
    [result],
  );
  const orderedColumns = [...dateColumns, ...numericColumns];
  const availableChartTypes = [
    ...(numericColumns.length ? ["histogram"] : []),
    ...(categoricalColumns.length ? ["bar"] : []),
    ...(numericColumns.length && orderedColumns.length > 1 ? ["line"] : []),
    ...(numericColumns.length > 1 ? ["scatter"] : []),
  ];

  function selectFile(nextFileId) {
    setFileId(nextFileId);
    setAnalysis(null);
    setCharts([]);
    setIsEditingChart(false);
    setEditingIndex(null);
    setCreatedReport(null);
    setDraftNotice("");
    setErrorMessage("");
    setSuccessMessage("");
  }

  async function loadFile() {
    setBusyAction("load");
    setErrorMessage("");
    try {
      const response = await apiClient.post(
        `/api/analyzer/analysis/${fileId}`,
        null,
        { params: { preview_rows: 5 } },
      );
      setAnalysis(response.data);
      setCharts([]);
      setCreatedReport(null);
      setDraftNotice("");
    } catch (error) {
      setErrorMessage(getErrorMessage(error, "Could not load report data."));
    } finally {
      setBusyAction("");
    }
  }

  function getXOptions(type) {
    if (type === "histogram" || type === "scatter") return numericColumns;
    if (type === "line") return orderedColumns;
    return categoricalColumns;
  }

  function setEditorType(nextType) {
    const nextXColumns = getXOptions(nextType);
    const nextXColumn = nextXColumns[0] || "";
    setChartType(nextType);
    setTitle(`${nextType.charAt(0).toUpperCase()}${nextType.slice(1)} chart`);
    setXColumn(nextXColumn);
    setYColumn(numericColumns.find((column) => column !== nextXColumn) || "");
    setAggregation("");
    setHistogramBins(20);
  }

  function startAddingChart() {
    setEditingIndex(null);
    setIsEditingChart(true);
    setEditorType(availableChartTypes[0]);
    setErrorMessage("");
  }

  function startEditingChart(index) {
    const configuration = charts[index].configuration;
    setEditingIndex(index);
    setIsEditingChart(true);
    setChartType(configuration.chart_type);
    setTitle(configuration.title);
    setXColumn(configuration.x_column || "");
    setYColumn(configuration.y_column || "");
    setAggregation(configuration.aggregation || "");
    setHistogramBins(configuration.histogram_bins || 20);
    setErrorMessage("");
  }

  function cancelEditing() {
    setIsEditingChart(false);
    setEditingIndex(null);
    setErrorMessage("");
  }

  function getConfiguration() {
    return {
      chart_type: chartType,
      title: title.trim() || `${chartType.charAt(0).toUpperCase()}${chartType.slice(1)} chart`,
      x_column: xColumn || null,
      y_column: ["bar", "line", "scatter"].includes(chartType) ? yColumn || null : null,
      aggregation: chartType === "bar" && yColumn ? aggregation || null : null,
      histogram_bins: chartType === "histogram" ? Number(histogramBins) : null,
    };
  }

  function invalidateGeneratedReport() {
    if (createdReport) {
      setDraftNotice("The chart collection changed. Generate a new report to refresh the downloads.");
    }
    setCreatedReport(null);
    setSuccessMessage("");
  }

  async function saveChart(event) {
    event.preventDefault();
    setBusyAction("chart");
    setErrorMessage("");

    try {
      const response = await apiClient.post(
        `/api/analyzer/files/${fileId}/chart`,
        getConfiguration(),
      );
      const chartItem = {
        id: editingIndex === null ? `${Date.now()}-${Math.random()}` : charts[editingIndex].id,
        configuration: response.data.configuration,
        figure: response.data.figure,
      };

      if (editingIndex === null) {
        setCharts((current) => [...current, chartItem]);
      } else {
        setCharts((current) => current.map((item, index) => index === editingIndex ? chartItem : item));
      }

      invalidateGeneratedReport();
      setIsEditingChart(false);
      setEditingIndex(null);
    } catch (error) {
      setErrorMessage(getErrorMessage(error, "Could not validate this chart."));
    } finally {
      setBusyAction("");
    }
  }

  function removeChart(index) {
    setCharts((current) => current.filter((_, itemIndex) => itemIndex !== index));
    invalidateGeneratedReport();
    if (editingIndex === index) cancelEditing();
  }

  async function generateReport() {
    setBusyAction("generate");
    setErrorMessage("");
    setSuccessMessage("");
    setDraftNotice("");

    try {
      const response = await apiClient.post(`/api/reports/${fileId}`, {
        chart_configurations: charts.map((chart) => chart.configuration),
      });
      setCreatedReport(response.data);
      setSuccessMessage("HTML and PDF reports were generated successfully.");
    } catch (error) {
      setErrorMessage(getErrorMessage(error, "Could not generate the reports."));
    } finally {
      setBusyAction("");
    }
  }

  async function downloadReport(reportId, filename) {
    setErrorMessage("");
    try {
      await downloadAuthenticatedFile(`/api/reports/${reportId}/download`, filename);
    } catch (error) {
      setErrorMessage(getErrorMessage(error, "Could not download the report."));
    }
  }

  const xOptions = getXOptions(chartType);
  const scatterYColumns = numericColumns.filter((column) => column !== xColumn);

  return (
    <div className="page">
      <header className="page-header"><div><p className="eyebrow">Data tools</p><h1>Reports</h1><p className="muted">Build a report from up to ten charts and export it as HTML and PDF.</p></div></header>
      {errorMessage && <p className="alert error">{errorMessage}</p>}
      {successMessage && <p className="alert success">{successMessage}</p>}
      {draftNotice && <p className="alert">{draftNotice}</p>}

      <section className="panel section-stack">
        <h2>Select data</h2>
        {isLoadingFiles ? <p className="empty-text">Loading CSV files...</p> : files.length === 0 ? <p className="empty-text">No organized CSV files are available.</p> : (
          <div className="inline-form"><CsvFileSelect files={files} value={fileId} onChange={selectFile} /><button type="button" className="button secondary" disabled={!fileId || busyAction === "load"} onClick={loadFile}>{busyAction === "load" ? "Loading..." : "Build report"}</button></div>
        )}
      </section>

      {result && (
        <>
          <section className="panel section-stack">
            <div className="section-heading">
              <div><h2>Report charts</h2><p className="muted">{charts.length} of {MAX_REPORT_CHARTS} charts added</p></div>
              {charts.length < MAX_REPORT_CHARTS && !isEditingChart && availableChartTypes.length > 0 && <button type="button" className="button secondary" onClick={startAddingChart}>Add chart</button>}
            </div>
            {availableChartTypes.length === 0 && <p className="empty-text">This CSV does not contain columns that can be charted.</p>}
            {charts.length === 0 && !isEditingChart && availableChartTypes.length > 0 && <p className="empty-text">Add a chart to begin the report.</p>}

            <div className="report-chart-list">
              {charts.map((chart, index) => (
                <article className="report-chart-card" key={chart.id}>
                  <div className="section-heading">
                    <h2>{index + 1}. {chart.configuration.title}</h2>
                    <div className="result-actions"><button type="button" className="text-button" disabled={isEditingChart} onClick={() => startEditingChart(index)}>Edit</button><button type="button" className="text-button danger" disabled={isEditingChart} onClick={() => removeChart(index)}>Remove</button></div>
                  </div>
                  <ChartPreview figure={chart.figure} title={chart.configuration.title} />
                </article>
              ))}
            </div>
            {charts.length >= MAX_REPORT_CHARTS && <p className="alert">A report can contain up to {MAX_REPORT_CHARTS} charts.</p>}
          </section>

          {isEditingChart && (
            <section className="panel section-stack chart-editor">
              <h2>{editingIndex === null ? "Add chart" : `Edit chart ${editingIndex + 1}`}</h2>
              <form className="form-stack" onSubmit={saveChart}>
                <div className="form-grid">
                  <select aria-label="Chart type" value={chartType} onChange={(event) => setEditorType(event.target.value)}>{availableChartTypes.map((type) => <option key={type} value={type}>{type.charAt(0).toUpperCase() + type.slice(1)}</option>)}</select>
                  <input value={title} placeholder="Chart title" onChange={(event) => setTitle(event.target.value)} required />
                  <select aria-label="X-axis column" value={xColumn} onChange={(event) => { setXColumn(event.target.value); if (chartType === "scatter" && event.target.value === yColumn) setYColumn(""); }} required><option value="">X-axis column</option>{xOptions.map((column) => <option key={column} value={column}>{column}</option>)}</select>
                  {chartType === "bar" && <select aria-label="Bar values" value={yColumn} onChange={(event) => setYColumn(event.target.value)}><option value="">Count rows</option>{numericColumns.map((column) => <option key={column} value={column}>{column}</option>)}</select>}
                  {chartType === "line" && <select aria-label="Y-axis column" value={yColumn} onChange={(event) => setYColumn(event.target.value)} required><option value="">Y-axis column</option>{numericColumns.map((column) => <option key={column} value={column}>{column}</option>)}</select>}
                  {chartType === "scatter" && <select aria-label="Y-axis column" value={yColumn} onChange={(event) => setYColumn(event.target.value)} required><option value="">Y-axis column</option>{scatterYColumns.map((column) => <option key={column} value={column}>{column}</option>)}</select>}
                  {chartType === "bar" && yColumn && <select aria-label="Aggregation" value={aggregation} onChange={(event) => setAggregation(event.target.value)} required><option value="">Aggregation</option>{AGGREGATIONS.map((item) => <option key={item} value={item}>{item}</option>)}</select>}
                  {chartType === "histogram" && <input type="number" min="1" max="100" value={histogramBins} aria-label="Histogram bins" onChange={(event) => setHistogramBins(event.target.value)} required />}
                </div>
                <div className="result-actions"><button className="button primary" disabled={busyAction === "chart"}>{busyAction === "chart" ? "Validating..." : editingIndex === null ? "Preview and add chart" : "Preview and save changes"}</button><button type="button" className="button secondary" disabled={busyAction === "chart"} onClick={cancelEditing}>Cancel</button></div>
              </form>
            </section>
          )}

          {charts.length > 0 && !isEditingChart && (
            <section className="report-generation-actions">
              {!createdReport ? <button type="button" className="button primary" disabled={busyAction === "generate"} onClick={generateReport}>{busyAction === "generate" ? "Generating HTML and PDF..." : "Generate report"}</button> : (
                <div className="result-actions"><button type="button" className="button primary" onClick={() => downloadReport(createdReport.html_report_id, createdReport.html_report_filename)}>Download HTML</button><button type="button" className="button secondary" onClick={() => downloadReport(createdReport.pdf_report_id, createdReport.pdf_report_filename)}>Download PDF</button></div>
              )}
            </section>
          )}
        </>
      )}
    </div>
  );
}

export default ReportsPage;
