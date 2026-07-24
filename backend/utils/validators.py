from backend.utils.constants import MAX_FILENAME_LENGTH, SUPPORTED_FILE_TYPES, MAX_FILE_SIZE_BYTES, FILE_TYPE_GROUPS



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
        raise ValueError(f"{filename}'s file extension does not support")
     

def validate_file_size(filesize: int) -> int :
    if not isinstance(filesize, int):
        raise TypeError(f"Filesize must be an integer, got {type(filesize).__name__}.")
    if not filesize > 0 :
        raise ValueError(f"{filesize} is invalid")
    if not filesize <= MAX_FILE_SIZE_BYTES:
        raise ValueError(f"{filesize} exceeds the maximum file size")
    return filesize

def get_file_category(filename:str) -> str:
    extension = validate_file_extension(filename)

    for filetype in FILE_TYPE_GROUPS.keys():
        if extension in FILE_TYPE_GROUPS.get(filetype):
            return filetype
        
    raise ValueError(f"No file category is found for {filename}")


def find_unsupported_files(filenames: list) -> list:
    unsupported_files: list[str]=[]
    for filename in filenames:
        try:
            validate_file_extension(filename)
        except (ValueError, TypeError):
            unsupported_files.append(filename)
    
    return unsupported_files





