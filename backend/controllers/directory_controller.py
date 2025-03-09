from datetime import datetime, UTC
from typing import Optional, Dict, Any, cast, List
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from config.mongo import get_db, TypedAsyncIOMotorDatabase
from motor.motor_asyncio import AsyncIOMotorCollection
from api.utils.auth_helper import get_current_user
from db.models.directory import MongoDirectory, create_directory_path
from db.models.document_uploads import MongoDocumentUpload, get_display_title
from db.models.user import MongoUser
from api.responses.directory import (
    DirectoryResponse,
    DirectoryContentsResponse,
    DirectoryListResponse,
)
from api.responses.document_upload import (
    DocumentRetrieveResponseForPage,
    DocumentUploadResponse,
    ThumbnailInfo,
)

router = APIRouter()


async def get_directory_collection(
    db: TypedAsyncIOMotorDatabase,
) -> AsyncIOMotorCollection[MongoDirectory]:
    return cast(AsyncIOMotorCollection[MongoDirectory], db["directories"])


async def get_document_uploads_collection(
    db: TypedAsyncIOMotorDatabase,
) -> AsyncIOMotorCollection[MongoDocumentUpload]:
    return cast(AsyncIOMotorCollection[MongoDocumentUpload], db["document_uploads"])


@router.post("/directories", response_model=DirectoryResponse)
async def create_directory(
    name: str,
    parent_id: Optional[str] = None,
    db: TypedAsyncIOMotorDatabase = Depends(get_db),
    current_user: MongoUser = Depends(get_current_user),
):
    """
    Create a new directory.

    Args:
        name: The name of the directory
        parent_id: The ID of the parent directory (None for root directories)
        db: The database connection
        current_user: The authenticated user

    Returns:
        The created directory
    """
    user_id = str(current_user["_id"])
    directory_collection = await get_directory_collection(db)

    # Validate directory name
    if not name or len(name.strip()) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Directory name cannot be empty",
        )

    # Check if parent directory exists if parent_id is provided
    parent_path = "/"
    if parent_id:
        parent_directory = await directory_collection.find_one(
            {"_id": ObjectId(parent_id), "user_id": ObjectId(user_id)}
        )
        if not parent_directory:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent directory not found",
            )
        parent_path = parent_directory["path"]

    # Check if directory with same name already exists in the same parent
    existing_directory = await directory_collection.find_one(
        {
            "user_id": ObjectId(user_id),
            "name": name,
            "parent_id": ObjectId(parent_id) if parent_id else None,
        }
    )
    if existing_directory:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Directory with this name already exists in the parent directory",
        )

    # Create directory path
    path = create_directory_path(parent_path, name)

    # Create directory
    now = datetime.now(UTC).isoformat()
    directory: MongoDirectory = {
        "_id": ObjectId(),
        "user_id": ObjectId(user_id),
        "name": name,
        "parent_id": ObjectId(parent_id) if parent_id else None,
        "path": path,
        "created_at": now,
        "updated_at": now,
    }

    result = await directory_collection.insert_one(directory)
    directory["_id"] = result.inserted_id

    # Create a new dictionary for response instead of modifying the TypedDict
    directory_dict = {
        "id": str(directory["_id"]),
        "user_id": str(directory["user_id"]),
        "name": str(directory["name"]),
        "parent_id": (
            str(directory["parent_id"]) if directory.get("parent_id") else None
        ),
        "path": str(directory["path"]),
        "created_at": str(directory["created_at"]),
        "updated_at": str(directory["updated_at"]),
    }

    # return DirectoryResponse(directory_dict)
    return DirectoryResponse.model_validate(directory_dict)


@router.get("/directories", response_model=DirectoryListResponse)
async def list_directories(
    parent_id: Optional[str] = None,
    db: TypedAsyncIOMotorDatabase = Depends(get_db),
    current_user: MongoUser = Depends(get_current_user),
):
    """
    List directories for the authenticated user.

    Args:
        parent_id: The ID of the parent directory (None for root directories)
        db: The database connection
        current_user: The authenticated user

    Returns:
        A list of directories
    """
    user_id = str(current_user["_id"])
    directory_collection = await get_directory_collection(db)

    # Build query
    if parent_id:
        query = {"user_id": ObjectId(user_id), "parent_id": ObjectId(parent_id)}
    else:
        # Use $exists: false to find documents where parent_id is null or doesn't exist
        query = {
            "user_id": ObjectId(user_id),
            "$or": [{"parent_id": None}, {"parent_id": {"$exists": False}}],
        }

    # Get directories
    directories = cast(
        List[MongoDirectory],
        await directory_collection.find(query).to_list(length=None),
    )

    # Convert directories to response format
    directory_responses: List[DirectoryResponse] = []
    for directory in directories:
        directory_responses.append(
            DirectoryResponse(
                id=str(directory["_id"]),
                user_id=str(directory["user_id"]),
                name=str(directory["name"]),
                parent_id=(
                    str(directory["parent_id"]) if directory.get("parent_id") else None
                ),
                path=str(directory["path"]),
                created_at=str(directory["created_at"]),
                updated_at=str(directory["updated_at"]),
            )
        )

    return DirectoryListResponse(directories=directory_responses)


@router.get("/directories/{directory_id}", response_model=DirectoryResponse)
async def get_directory(
    directory_id: str,
    db: TypedAsyncIOMotorDatabase = Depends(get_db),
    current_user: MongoUser = Depends(get_current_user),
):
    """
    Get a directory by ID.

    Args:
        directory_id: The ID of the directory
        db: The database connection
        current_user: The authenticated user

    Returns:
        The directory
    """
    user_id = str(current_user["_id"])
    directory_collection = await get_directory_collection(db)

    # Get directory
    directory = await directory_collection.find_one(
        {"_id": ObjectId(directory_id), "user_id": ObjectId(user_id)}
    )
    if not directory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Directory not found",
        )

    # Create a new dictionary for response instead of modifying the TypedDict
    directory_dict = {
        "id": str(directory["_id"]),
        "user_id": str(directory["user_id"]),
        "name": str(directory["name"]),
        "parent_id": (
            str(directory["parent_id"]) if directory.get("parent_id") else None
        ),
        "path": str(directory["path"]),
        "created_at": str(directory["created_at"]),
        "updated_at": str(directory["updated_at"]),
    }

    # Use model_validate to handle optional fields properly
    return DirectoryResponse.model_validate(directory_dict)


@router.put("/directories/{directory_id}", response_model=DirectoryResponse)
async def update_directory(
    directory_id: str,
    name: str,
    db: TypedAsyncIOMotorDatabase = Depends(get_db),
    current_user: MongoUser = Depends(get_current_user),
):
    """
    Update a directory.

    Args:
        directory_id: The ID of the directory to update
        name: The new name of the directory
        db: The database connection
        current_user: The authenticated user

    Returns:
        The updated directory
    """
    user_id = str(current_user["_id"])
    directory_collection = await get_directory_collection(db)
    document_collection = await get_document_uploads_collection(db)

    # Validate directory name
    if not name or len(name.strip()) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Directory name cannot be empty",
        )

    # Get directory
    directory = await directory_collection.find_one(
        {"_id": ObjectId(directory_id), "user_id": ObjectId(user_id)}
    )
    if not directory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Directory not found",
        )

    # Check if directory with same name already exists in the same parent
    existing_directory = await directory_collection.find_one(
        {
            "user_id": ObjectId(user_id),
            "name": name,
            "parent_id": directory["parent_id"],
            "_id": {"$ne": ObjectId(directory_id)},
        }
    )
    if existing_directory:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Directory with this name already exists in the parent directory",
        )

    # Get parent path
    parent_path = "/"
    if directory["parent_id"]:
        parent_directory = await directory_collection.find_one(
            {"_id": directory["parent_id"], "user_id": ObjectId(user_id)}
        )
        if parent_directory:
            parent_path = parent_directory["path"]

    # Create new path
    old_path = directory["path"]
    new_path = create_directory_path(parent_path, name)

    # Update directory
    now = datetime.now(UTC).isoformat()
    await directory_collection.update_one(
        {"_id": ObjectId(directory_id)},
        {
            "$set": {
                "name": name,
                "path": new_path,
                "updated_at": now,
            }
        },
    )

    # Update all child directories' paths
    child_directories = cast(
        List[MongoDirectory],
        await directory_collection.find(
            {"path": {"$regex": f"^{old_path}/"}, "user_id": ObjectId(user_id)}
        ).to_list(
            length=None
        ),  # type: ignore
    )

    for child in child_directories:
        child_new_path = child["path"].replace(old_path, new_path, 1)
        await directory_collection.update_one(
            {"_id": child["_id"]},
            {"$set": {"path": child_new_path, "updated_at": now}},
        )

    # Update all documents in this directory and child directories
    await document_collection.update_many(
        {"directory_id": ObjectId(directory_id), "user_id": ObjectId(user_id)},
        {"$set": {"directory_path": new_path}},
    )

    # Update all documents in child directories
    for child in child_directories:
        child_new_path = child["path"].replace(old_path, new_path, 1)
        await document_collection.update_many(
            {"directory_id": child["_id"], "user_id": ObjectId(user_id)},
            {"$set": {"directory_path": child_new_path}},
        )

    # Get updated directory
    updated_directory = await directory_collection.find_one(
        {"_id": ObjectId(directory_id)}
    )

    # Create a new dictionary for response instead of modifying the TypedDict
    if updated_directory is None:
        raise HTTPException(status_code=404, detail="Directory not found")

    directory_dict = {
        "id": str(updated_directory["_id"]),
        "user_id": str(updated_directory["user_id"]),
        "name": str(updated_directory["name"]),
        "parent_id": (
            str(updated_directory["parent_id"])
            if updated_directory.get("parent_id")
            else None
        ),
        "path": str(updated_directory["path"]),
        "created_at": str(updated_directory["created_at"]),
        "updated_at": str(updated_directory["updated_at"]),
    }

    # Use model_validate to handle optional fields properly
    return DirectoryResponse.model_validate(directory_dict)


@router.delete("/directories/{directory_id}")
async def delete_directory(
    directory_id: str,
    recursive: bool = False,
    db: TypedAsyncIOMotorDatabase = Depends(get_db),
    current_user: MongoUser = Depends(get_current_user),
):
    """
    Delete a directory.

    Args:
        directory_id: The ID of the directory
        recursive: Whether to delete all child directories and documents
        db: The database connection
        current_user: The authenticated user

    Returns:
        Success message
    """
    user_id = str(current_user["_id"])
    directory_collection = await get_directory_collection(db)
    document_collection = await get_document_uploads_collection(db)

    # Get directory
    directory = await directory_collection.find_one(
        {"_id": ObjectId(directory_id), "user_id": ObjectId(user_id)}
    )
    if not directory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Directory not found",
        )

    # Check if directory has child directories
    child_directories = cast(
        List[MongoDirectory],
        await directory_collection.find(
            {"parent_id": ObjectId(directory_id), "user_id": ObjectId(user_id)}
        ).to_list(length=None),
    )

    # Check if directory has documents
    documents = cast(
        List[MongoDocumentUpload],
        await document_collection.find(
            {"directory_id": ObjectId(directory_id), "user_id": ObjectId(user_id)}
        ).to_list(length=None),
    )

    if (child_directories or documents) and not recursive:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Directory is not empty. Use recursive=true to delete all contents.",
        )

    if recursive:
        # Delete all child directories recursively
        await directory_collection.delete_many(
            {"path": {"$regex": f"^{directory['path']}/"}, "user_id": ObjectId(user_id)}
        )

        # Move all documents in this directory and child directories to root
        await document_collection.update_many(
            {
                "$or": [
                    {"directory_id": ObjectId(directory_id)},
                    {"directory_path": {"$regex": f"^{directory['path']}/"}},
                ],
                "user_id": ObjectId(user_id),
            },
            {"$set": {"directory_id": None, "directory_path": None}},
        )

    # Delete directory
    await directory_collection.delete_one({"_id": ObjectId(directory_id)})

    return {"message": "Directory deleted successfully"}


@router.post("/directories/{directory_id}/move", response_model=DirectoryResponse)
async def move_directory(
    directory_id: str,
    new_parent_id: Optional[str] = None,
    db: TypedAsyncIOMotorDatabase = Depends(get_db),
    current_user: MongoUser = Depends(get_current_user),
):
    """
    Move a directory to a new parent.

    Args:
        directory_id: The ID of the directory to move
        new_parent_id: The ID of the new parent directory (None for root)
        db: The database connection
        current_user: The authenticated user

    Returns:
        The updated directory
    """
    user_id = str(current_user["_id"])
    directory_collection = await get_directory_collection(db)
    document_collection = await get_document_uploads_collection(db)

    # Get directory
    directory = await directory_collection.find_one(
        {"_id": ObjectId(directory_id), "user_id": ObjectId(user_id)}
    )
    if not directory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Directory not found",
        )

    # Check if new parent exists if provided
    new_parent_path = "/"
    if new_parent_id:
        # Prevent moving to own child
        if directory["path"] == "/" + new_parent_id or directory["path"].startswith(
            "/" + new_parent_id + "/"
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot move directory to its own child",
            )

        new_parent = await directory_collection.find_one(
            {"_id": ObjectId(new_parent_id), "user_id": ObjectId(user_id)}
        )
        if not new_parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="New parent directory not found",
            )
        new_parent_path = new_parent["path"]

    # Check if directory with same name already exists in the new parent
    existing_directory = await directory_collection.find_one(
        {
            "user_id": ObjectId(user_id),
            "name": directory["name"],
            "parent_id": ObjectId(new_parent_id) if new_parent_id else None,
            "_id": {"$ne": ObjectId(directory_id)},
        }
    )
    if existing_directory:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Directory with this name already exists in the new parent directory",
        )

    # Create new path
    old_path = directory["path"]
    new_path = create_directory_path(new_parent_path, directory["name"])

    # Update directory
    now = datetime.now(UTC).isoformat()
    await directory_collection.update_one(
        {"_id": ObjectId(directory_id)},
        {
            "$set": {
                "parent_id": ObjectId(new_parent_id) if new_parent_id else None,
                "path": new_path,
                "updated_at": now,
            }
        },
    )

    # Update all child directories' paths
    child_directories = cast(
        List[MongoDirectory],
        await directory_collection.find(
            {"path": {"$regex": f"^{old_path}/"}, "user_id": ObjectId(user_id)}
        ).to_list(length=None),
    )

    for child in child_directories:
        child_new_path = child["path"].replace(old_path, new_path, 1)
        await directory_collection.update_one(
            {"_id": child["_id"]},
            {"$set": {"path": child_new_path, "updated_at": now}},
        )

    # Update all documents in this directory
    await document_collection.update_many(
        {"directory_id": ObjectId(directory_id), "user_id": ObjectId(user_id)},
        {"$set": {"directory_path": new_path}},
    )

    # Update all documents in child directories
    for child in child_directories:
        child_new_path = child["path"].replace(old_path, new_path, 1)
        await document_collection.update_many(
            {"directory_id": child["_id"], "user_id": ObjectId(user_id)},
            {"$set": {"directory_path": child_new_path}},
        )

    # Get updated directory
    updated_directory = await directory_collection.find_one(
        {"_id": ObjectId(directory_id)}
    )

    # Create a new dictionary for response instead of modifying the TypedDict
    if updated_directory is None:
        raise HTTPException(status_code=404, detail="Directory not found")

    directory_dict = {
        "id": str(updated_directory["_id"]),
        "user_id": str(updated_directory["user_id"]),
        "name": str(updated_directory["name"]),
        "parent_id": (
            str(updated_directory["parent_id"])
            if updated_directory.get("parent_id")
            else None
        ),
        "path": str(updated_directory["path"]),
        "created_at": str(updated_directory["created_at"]),
        "updated_at": str(updated_directory["updated_at"]),
    }

    # Use model_validate to handle optional fields properly
    return DirectoryResponse.model_validate(directory_dict)


@router.get("/directories/path/{path:path}", response_model=DirectoryResponse)
async def get_directory_by_path(
    path: str,
    db: TypedAsyncIOMotorDatabase = Depends(get_db),
    current_user: MongoUser = Depends(get_current_user),
):
    """
    Get a directory by path.

    Args:
        path: The path of the directory
        db: The database connection
        current_user: The authenticated user

    Returns:
        The directory
    """
    user_id = str(current_user["_id"])
    directory_collection = await get_directory_collection(db)

    # Ensure path starts with /
    if not path.startswith("/"):
        path = f"/{path}"

    # Get directory
    directory = await directory_collection.find_one(
        {"path": path, "user_id": ObjectId(user_id)}
    )
    if not directory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Directory not found",
        )

    # Create a new dictionary for response instead of modifying the TypedDict
    directory_dict = {
        "id": str(directory["_id"]),
        "user_id": str(directory["user_id"]),
        "name": str(directory["name"]),
        "parent_id": (
            str(directory["parent_id"]) if directory.get("parent_id") else None
        ),
        "path": str(directory["path"]),
        "created_at": str(directory["created_at"]),
        "updated_at": str(directory["updated_at"]),
    }

    # Use model_validate to handle optional fields properly
    return DirectoryResponse.model_validate(directory_dict)


@router.get("/directories/root/contents", response_model=DirectoryContentsResponse)
async def get_root_directory_contents(
    db: TypedAsyncIOMotorDatabase = Depends(get_db),
    current_user: MongoUser = Depends(get_current_user),
):
    """
    Get the contents of the root directory (subdirectories and documents).

    Args:
        db: The database connection
        current_user: The authenticated user

    Returns:
        The directory contents
    """
    return await get_directory_contents(None, db, current_user)


@router.get(
    "/directories/{directory_id}/contents", response_model=DirectoryContentsResponse
)
async def get_directory_contents(
    directory_id: Optional[str] = None,
    db: TypedAsyncIOMotorDatabase = Depends(get_db),
    current_user: MongoUser = Depends(get_current_user),
):
    """
    Get the contents of a directory (subdirectories and documents).

    Args:
        directory_id: The ID of the directory (None for root)
        db: The database connection
        current_user: The authenticated user

    Returns:
        The directory contents
    """
    user_id = str(current_user["_id"])
    directory_collection = await get_directory_collection(db)
    document_collection = await get_document_uploads_collection(db)

    # Build query for directories
    if directory_id:
        dir_query = {"user_id": ObjectId(user_id), "parent_id": ObjectId(directory_id)}
    else:
        # Match documents where parent_id is null OR doesn't exist
        dir_query = {
            "user_id": ObjectId(user_id),
            "$or": [{"parent_id": None}, {"parent_id": {"$exists": False}}],
        }

    # Get directories
    directories = cast(
        List[MongoDirectory],
        await directory_collection.find(dir_query).to_list(length=None),
    )

    # Convert directories to response format
    directory_responses: List[DirectoryResponse] = []
    for directory in directories:
        directory_responses.append(
            DirectoryResponse(
                id=str(directory["_id"]),
                user_id=str(directory["user_id"]),
                name=str(directory["name"]),
                parent_id=(
                    str(directory["parent_id"]) if directory.get("parent_id") else None
                ),
                path=str(directory["path"]),
                created_at=str(directory["created_at"]),
                updated_at=str(directory["updated_at"]),
            )
        )

    # Build query for documents
    if directory_id:
        doc_query = {
            "user_id": ObjectId(user_id),
            "directory_id": ObjectId(directory_id),
        }
    else:
        # For root level, find documents with no directory_id
        # Using $or to handle both cases: field doesn't exist or is explicitly null
        doc_query = {
            "user_id": ObjectId(user_id),
            "$or": [{"directory_id": None}, {"directory_id": {"$exists": False}}],
        }

    # Get documents
    documents = cast(
        List[MongoDocumentUpload],
        await document_collection.find(doc_query).to_list(length=None),
    )

    # Convert documents to response format
    document_responses: List[DocumentRetrieveResponseForPage] = []
    for document in documents:
        # Create base response with required fields
        doc_response = DocumentRetrieveResponseForPage(
            id=str(document["_id"]),
            file_name=document["file_details"]["file_name"],
            file_type=document["file_details"]["file_type"],
            url_friendly_file_name=document["file_details"]["url_friendly_file_name"],
            custom_title=document.get("custom_title"),
            title=get_display_title(document),
            note=None,
            thumbnail=None,
            extracted_metadata=None,
            directory_path=(
                document["directory_path"] if document.get("directory_path") else None
            ),
            directory_id=(
                str(document["directory_id"]) if document.get("directory_id") else None
            ),
        )

        # Add thumbnail if available
        thumbnail = document.get("thumbnail")
        if thumbnail and "s3_url" in thumbnail:
            doc_response.thumbnail = ThumbnailInfo(presigned_url=thumbnail["s3_url"])

        document_responses.append(doc_response)

    return DirectoryContentsResponse(
        directories=directory_responses, documents=document_responses
    )


@router.post("/documents/{document_id}/move", response_model=Dict[str, Any])
async def move_document(
    document_id: str,
    directory_id: Optional[str] = None,
    db: TypedAsyncIOMotorDatabase = Depends(get_db),
    current_user: MongoUser = Depends(get_current_user),
):
    """
    Move a document to a new directory.

    Args:
        document_id: The ID of the document to move
        directory_id: The ID of the new directory (None for root)
        db: The database connection
        current_user: The authenticated user

    Returns:
        The updated document
    """
    user_id = str(current_user["_id"])
    directory_collection = await get_directory_collection(db)
    document_collection = await get_document_uploads_collection(db)

    # Get document
    document = await document_collection.find_one(
        {"_id": ObjectId(document_id), "user_id": ObjectId(user_id)}
    )
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Check if new directory exists if provided
    directory_path = None
    if directory_id:
        directory = await directory_collection.find_one(
            {"_id": ObjectId(directory_id), "user_id": ObjectId(user_id)}
        )
        if not directory:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Directory not found",
            )
        directory_path = directory["path"]

    # Update document
    await document_collection.update_one(
        {"_id": ObjectId(document_id)},
        {
            "$set": {
                "directory_id": ObjectId(directory_id) if directory_id else None,
                "directory_path": directory_path,
            }
        },
    )

    # Get updated document
    updated_document = await document_collection.find_one(
        {"_id": ObjectId(document_id)}
    )

    if updated_document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    # Create a new response dictionary instead of modifying the original
    response = {
        "id": str(updated_document["_id"]),
        "user_id": str(updated_document["user_id"]),
    }

    if updated_document.get("directory_id"):
        response["directory_id"] = str(updated_document["directory_id"])

    return response
