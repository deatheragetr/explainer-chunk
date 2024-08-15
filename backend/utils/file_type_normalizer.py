from typing import Dict

supported_file_types: Dict[str, str] = {
    "pdf": "application/pdf",
    "epub": "application/epub+zip",
    "json": "application/json",
    "markdown": "text/markdown",
    "text": "text/plain",
    "csv": "text/csv",
    "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "html": "text/html",
}


def normalize_file_type(content_type: str, file_extension: str) -> str:
    content_type = content_type.split(";")[0].lower()
    type_mapping = {
        "application/pdf": supported_file_types["pdf"],
        ".pdf": supported_file_types["pdf"],
        "application/epub+zip": supported_file_types["epub"],
        ".epub": supported_file_types["epub"],
        "application/json": supported_file_types["json"],
        ".json": supported_file_types["json"],
        "text/markdown": supported_file_types["markdown"],
        ".md": supported_file_types["markdown"],
        ".markdown": supported_file_types["markdown"],
        "text/plain": supported_file_types["text"],
        ".txt": supported_file_types["text"],
        "text/csv": supported_file_types["csv"],
        ".csv": supported_file_types["csv"],
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": supported_file_types[
            "excel"
        ],
        ".xlsx": supported_file_types["excel"],
        "text/html": supported_file_types["html"],
        ".html": supported_file_types["html"],
        ".htm": supported_file_types["html"],
    }
    return (
        type_mapping.get(content_type)
        or type_mapping.get(file_extension.lower())
        or "unknown"
    )
