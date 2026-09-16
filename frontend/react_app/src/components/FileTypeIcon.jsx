const FILE_TYPE_STYLES = {
  doc: ["word", "W"], docx: ["word", "W"],
  xls: ["excel", "X"], xlsx: ["excel", "X"], csv: ["excel", "CSV"],
  pdf: ["pdf", "PDF"],
  ppt: ["powerpoint", "P"], pptx: ["powerpoint", "P"],
  jpg: ["image", "IMG"], jpeg: ["image", "IMG"], png: ["image", "IMG"],
  mp4: ["video", "VID"], mkv: ["video", "VID"], webm: ["video", "VID"],
  mp3: ["audio", "AUD"], wav: ["audio", "AUD"], m4a: ["audio", "AUD"],
  zip: ["archive", "ZIP"], tar: ["archive", "ZIP"], rar: ["archive", "ZIP"],
  py: ["code", "</>"], js: ["code", "JS"], java: ["code", "</>"],
  c: ["code", "C"], cpp: ["code", "C++"], html: ["code", "</>"],
  css: ["code", "CSS"], json: ["code", "{}"], xml: ["code", "<>"],
  yaml: ["code", "YML"], yml: ["code", "YML"], txt: ["text", "TXT"],
};

function getExtension(fileName, extension) {
  if (extension) return extension.toLowerCase().replace(".", "");
  return fileName?.split(".").pop()?.toLowerCase() || "file";
}

function FileTypeIcon({ fileName, extension, size = "medium" }) {
  const resolvedExtension = getExtension(fileName, extension);
  const [type, label] = FILE_TYPE_STYLES[resolvedExtension] || [
    "generic",
    resolvedExtension.slice(0, 4).toUpperCase(),
  ];

  return (
    <span
      className={`file-type-icon ${type} ${size}`}
      title={`${resolvedExtension.toUpperCase()} file`}
      aria-label={`${resolvedExtension.toUpperCase()} file`}
    >
      {label}
    </span>
  );
}

export default FileTypeIcon;
