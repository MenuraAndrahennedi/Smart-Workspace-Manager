import FileTypeIcon from "./FileTypeIcon";

function FileName({ name, extension, size = "medium" }) {
  return (
    <span className="file-name-with-icon">
      <FileTypeIcon fileName={name} extension={extension} size={size} />
      <span className="file-name-text">{name}</span>
    </span>
  );
}

export default FileName;
