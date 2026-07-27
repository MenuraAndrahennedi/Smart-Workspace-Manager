from typing import Dict, Final, List


FILE_TYPE_GROUPS : Final[Dict[str, List[str]]] = {
    "spreadsheet": ["csv", "xls", "xlsx"],
    "document": ["doc", "docx", "txt"],
    "pdf": ["pdf"],
    "image": ["jpg", "jpeg", "png"],
    "video": ["mp4", "mkv", "webm"],
    "audio": ["mp3", "wav", "m4a"],
    "data": ["json", "xml", "yaml", "yml"],
    "archive": ["zip", "tar", "rar"],
    "presentation": ["ppt", "pptx"],
    "code": ["py", "js", "java", "c", "cpp", "html", "css"],
}

SUPPORTED_FILE_TYPES : Final[List[str]] = [extension for group in FILE_TYPE_GROUPS.values() for extension in group]
MAX_FILENAME_LENGTH : Final[int] = 255  # Maximum filename length



STORAGE_DIRECTORIES = (
    "uploads",
    "processed",
    "processed/csv",
    "processed/images",
    "processed/documents",
    "processed/pdf",
    "processed/others",
    "reports",
    "models",
    "sample"
)
