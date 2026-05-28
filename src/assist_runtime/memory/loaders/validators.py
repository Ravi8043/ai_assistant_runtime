import logging
import os
from assist_runtime.memory.exceptions import MemoryLoadError

logger = logging.getLogger(__name__)



def validate_file_path(file_path: str) -> None:

    """
    Validates file path and raises appropriate errors if invalid
    """
    
    if not file_path or not file_path.strip():
        error_msg = "File path was not provided or is empty"
        logger.error(error_msg)
        raise MemoryLoadError(error_msg)
    
    if not os.path.exists(file_path):
        error_msg = f"File does not exist: {file_path}"
        logger.error(error_msg)
        raise MemoryLoadError(error_msg)
    
    if not os.path.isfile(file_path):
        error_msg = f"Path provided is not a file: {file_path}"
        logger.error(error_msg)
        raise MemoryLoadError(error_msg)

def validate_directory_path(dir_path: str) -> None:
    """
    Validates directory path and raises appropriate errors if invalid
    """
    if not dir_path or not dir_path.strip():
        error_msg = "Directory path was not provided or is empty"
        logger.error(error_msg)
        raise MemoryLoadError(error_msg)
    
    if not os.path.exists(dir_path):
        error_msg = f"Directory does not exist: {dir_path}"
        logger.error(error_msg)
        raise MemoryLoadError(error_msg)
    
    if not os.path.isdir(dir_path):
        error_msg = f"Path provided is not a directory: {dir_path}"
        logger.error(error_msg)
        raise MemoryLoadError(error_msg)