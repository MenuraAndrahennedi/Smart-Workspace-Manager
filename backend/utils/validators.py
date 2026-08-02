from backend.utils.constants import (
    DEFAULT_ORGANIZER_CATEGORY,
    MAX_FILENAME_LENGTH,
    ORGANIZER_CATEGORY_RULES,
    SUPPORTED_FILE_TYPES,
)



def validate_filename(filename) -> str:

    if not isinstance(filename, str):
        raise TypeError(f"Filename must be a string, got {type(filename).__name__}.")

    else:
        filename = filename.strip()
        if 0 < len(filename) <= MAX_FILENAME_LENGTH:
            return filename
        elif len(filename) == 0:
            raise ValueError("Filename cannot be empty.")  
        elif len(filename) > MAX_FILENAME_LENGTH:
            raise ValueError(f"Filename exceeds maximum length of {MAX_FILENAME_LENGTH} characters.")


def get_file_extension(filename: str) -> str:
    filename = validate_filename(filename)
    if filename.count('.') == 0:
        raise ValueError("Filename must contain an extension.")
    return filename.rsplit('.', 1)[-1].lower()


def validate_file_extension(filename: str) -> str:
    extension = get_file_extension(filename)
    if extension in SUPPORTED_FILE_TYPES:
        return extension
    else:
        raise ValueError(f"Files with the '.{extension}' extension are not supported.")
     

def validate_file_size(filesize: int, max_size_bytes: int) -> int :
    if not isinstance(filesize, int):
        raise TypeError(f"Filesize must be an integer, got {type(filesize).__name__}.")
    if not isinstance(max_size_bytes, int):
        raise TypeError(f"Max filesize must be an integer, got {type(max_size_bytes).__name__}.")
    if not filesize > 0 :
        raise ValueError("The selected file is empty.")
    if not filesize <= max_size_bytes:
        raise ValueError("The selected file exceeds the maximum allowed size.")
    return filesize

def get_file_category(filename:str) -> str:
    extension = validate_file_extension(filename)

    for category, extensions in ORGANIZER_CATEGORY_RULES.items():
        if extension in extensions:
            return category

    return DEFAULT_ORGANIZER_CATEGORY


def find_unsupported_files(filenames: list) -> list:
    unsupported_files: list[str]=[]
    for filename in filenames:
        try:
            validate_file_extension(filename)
        except (ValueError, TypeError):
            unsupported_files.append(filename)
    
    return unsupported_files





