function formatCellValue(value) {
  if (value === null || value === undefined) return "-";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function DataTable({ rows = [], columns, emptyMessage = "No data available." }) {
  if (rows.length === 0) {
    return <p className="empty-text">{emptyMessage}</p>;
  }

  const visibleColumns = columns?.length ? columns : Object.keys(rows[0]);

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {visibleColumns.map((column) => (
              <th key={column}>{column.replaceAll("_", " ")}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={rowIndex}>
              {visibleColumns.map((column) => (
                <td key={column}>{formatCellValue(row[column])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default DataTable;
