function CsvFileSelect({ files, value, onChange, disabled = false }) {
  return (
    <select
      value={value}
      onChange={(event) => onChange(event.target.value)}
      disabled={disabled}
      required
    >
      <option value="">Select a CSV file</option>
      {files.map((file) => (
        <option key={file.id} value={file.id}>
          {file.original_name}
        </option>
      ))}
    </select>
  );
}

export default CsvFileSelect;
