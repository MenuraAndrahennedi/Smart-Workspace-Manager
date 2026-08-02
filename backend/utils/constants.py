from typing import Dict, Final, List

MAX_FILENAME_LENGTH : Final[int] = 255  # Maximum filename length


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


ORGANIZER_CATEGORY_RULES: Final[Dict[str, List[str]]] = {
    "spreadsheets": FILE_TYPE_GROUPS["spreadsheet"],
    "images": FILE_TYPE_GROUPS["image"],
    "pdf": FILE_TYPE_GROUPS["pdf"],
    "documents": [
        *FILE_TYPE_GROUPS["document"],
        *FILE_TYPE_GROUPS["presentation"],
    ],
}
DEFAULT_ORGANIZER_CATEGORY: Final[str] = "others"



STORAGE_DIRECTORIES: Final[tuple[str, ...]] = (
    "uploads",
    "processed",
    "processed/spreadsheets",
    "processed/images",
    "processed/documents",
    "processed/pdf",
    "processed/others",
    "reports",
    "sample"
)

VALID_AGGREGATIONS: Final[dict[str, str]] = {
    "Mean": "mean",
    "Sum": "sum",
    "Minimum": "min",
    "Maximum": "max",
    "Count": "count",
}
