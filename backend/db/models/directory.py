from typing import TypedDict, Annotated, Optional
from bson import ObjectId


class MongoDirectory(TypedDict):
    _id: Annotated[ObjectId, "MongoDB ObjectId"]
    user_id: Annotated[ObjectId, "ID of the user who owns this directory"]
    name: Annotated[str, "Name of the directory"]
    parent_id: Optional[
        Annotated[ObjectId, "ID of the parent directory (None if root)"]
    ]
    path: Annotated[str, "Full path of the directory (e.g., /parent/child)"]
    created_at: Annotated[str, "ISO format timestamp of when the directory was created"]
    updated_at: Annotated[
        str, "ISO format timestamp of when the directory was last updated"
    ]


def create_directory_path(parent_path: Optional[str], directory_name: str) -> str:
    """
    Create a directory path by combining the parent path and directory name.

    Args:
        parent_path: The path of the parent directory (None for root directories)
        directory_name: The name of the directory

    Returns:
        The full path of the directory
    """
    if parent_path is None or parent_path == "/":
        return f"/{directory_name}"
    else:
        # Ensure parent_path starts with / and doesn't end with /
        if not parent_path.startswith("/"):
            parent_path = f"/{parent_path}"
        if parent_path.endswith("/"):
            parent_path = parent_path[:-1]
        return f"{parent_path}/{directory_name}"
