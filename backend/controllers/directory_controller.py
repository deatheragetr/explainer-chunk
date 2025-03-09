from datetime import datetime
from typing import List, Optional, Dict, Any
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.database import Database

from config.mongo import get_db, TypedAsyncIOMotorDatabase
from api.utils.auth_helper import get_current_user
from db.models.directory import MongoDirectory, create_directory_path
from db.models.document_uploads import MongoDocumentUpload
from db.models.user import MongoUser

router = APIRouter()


async def get_directory_collection(db: TypedAsyncIOMotorDatabase):
    return db["directories"]


async def get_document_uploads_collection(db: TypedAsyncIOMotorDatabase):
    return db["document_uploads"]


@router.post("/directories", response_model=Dict[str, Any])
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
    now = datetime.utcnow().isoformat()
    directory = {
        "user_id": ObjectId(user_id),
        "name": name,
        "parent_id": ObjectId(parent_id) if parent_id else None,
        "path": path,
        "created_at": now,
        "updated_at": now,
    }

    result = await directory_collection.insert_one(directory)
    directory["_id"] = result.inserted_id

    # Convert ObjectId to string for response
    directory["_id"] = str(directory["_id"])
    directory["user_id"] = str(directory["user_id"])
    if directory["parent_id"]:
        directory["parent_id"] = str(directory["parent_id"])

    return directory


@router.get("/directories", response_model=List[Dict[str, Any]])
async def list_directories(
    parent_id: Optional[str] = None,
    db: TypedAsyncIOMotorDatabase = Depends(get_db),
    current_user: MongoUser = Depends(get_current_user),
):
    """
    List directories.

    Args:
        parent_id: The ID of the parent directory (None for root directories)
        db: The database connection
        current_user: The authenticated user

    Returns:
        List of directories
    """
    user_id = str(current_user["_id"])
    directory_collection = await get_directory_collection(db)

    # Build query
    query = {"user_id": ObjectId(user_id)}
    if parent_id:
        query["parent_id"] = ObjectId(parent_id)
    else:
        # Use $exists: false to find documents where parent_id is null or doesn't exist
        query["parent_id"] = {"$exists": False}

    # Get directories
    directories = await directory_collection.find(query).to_list(length=None)

    # Convert ObjectId to string for response
    for directory in directories:
        directory["_id"] = str(directory["_id"])
        directory["user_id"] = str(directory["user_id"])
        if directory.get("parent_id"):
            directory["parent_id"] = str(directory["parent_id"])

    return directories


@router.get("/directories/{directory_id}", response_model=Dict[str, Any])
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

    # Convert ObjectId to string for response
    directory["_id"] = str(directory["_id"])
    directory["user_id"] = str(directory["user_id"])
    if directory["parent_id"]:
        directory["parent_id"] = str(directory["parent_id"])

    return directory


@router.put("/directories/{directory_id}", response_model=Dict[str, Any])
async def update_directory(
    directory_id: str,
    name: str,
    db: TypedAsyncIOMotorDatabase = Depends(get_db),
    current_user: MongoUser = Depends(get_current_user),
):
    """
    Update a directory.

    Args:
        directory_id: The ID of the directory
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
    now = datetime.utcnow().isoformat()
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
    child_directories = await directory_collection.find(
        {"path": {"$regex": f"^{old_path}/"}, "user_id": ObjectId(user_id)}
    ).to_list(length=None)

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

    # Convert ObjectId to string for response
    updated_directory["_id"] = str(updated_directory["_id"])
    updated_directory["user_id"] = str(updated_directory["user_id"])
    if updated_directory["parent_id"]:
        updated_directory["parent_id"] = str(updated_directory["parent_id"])

    return updated_directory


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
    child_directories = await directory_collection.find(
        {"parent_id": ObjectId(directory_id), "user_id": ObjectId(user_id)}
    ).to_list(length=None)

    # Check if directory has documents
    documents = await document_collection.find(
        {"directory_id": ObjectId(directory_id), "user_id": ObjectId(user_id)}
    ).to_list(length=None)

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


@router.post("/directories/{directory_id}/move", response_model=Dict[str, Any])
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
        The moved directory
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
    now = datetime.utcnow().isoformat()
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
    child_directories = await directory_collection.find(
        {"path": {"$regex": f"^{old_path}/"}, "user_id": ObjectId(user_id)}
    ).to_list(length=None)

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

    # Convert ObjectId to string for response
    updated_directory["_id"] = str(updated_directory["_id"])
    updated_directory["user_id"] = str(updated_directory["user_id"])
    if updated_directory["parent_id"]:
        updated_directory["parent_id"] = str(updated_directory["parent_id"])

    return updated_directory


@router.get("/directories/path/{path:path}", response_model=Dict[str, Any])
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

    # Convert ObjectId to string for response
    directory["_id"] = str(directory["_id"])
    directory["user_id"] = str(directory["user_id"])
    if directory["parent_id"]:
        directory["parent_id"] = str(directory["parent_id"])

    return directory


@router.get("/directories/root/contents", response_model=Dict[str, Any])
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


@router.get("/directories/{directory_id}/contents", response_model=Dict[str, Any])
async def get_directory_contents(
    directory_id: Optional[str] = None,
    db: TypedAsyncIOMotorDatabase = Depends(get_db),
    current_user: MongoUser = Depends(get_current_user),
):
    """
    Get the contents of a directory (subdirectories and documents).

    Args:
        directory_id: The ID of the directory
        db: The database connection
        current_user: The authenticated user

    Returns:
        The directory contents
    """
    user_id = str(current_user["_id"])
    directory_collection = await get_directory_collection(db)
    document_collection = await get_document_uploads_collection(db)

    # Build query for directories
    dir_query = {"user_id": ObjectId(user_id)}
    if directory_id:
        dir_query["parent_id"] = ObjectId(directory_id)
    else:
        # Use $exists: false to find documents where parent_id is null or doesn't exist
        dir_query["parent_id"] = {"$exists": False}

    # Get directories
    directories = await directory_collection.find(dir_query).to_list(length=None)

    # Convert ObjectId to string for response
    for directory in directories:
        directory["_id"] = str(directory["_id"])
        directory["user_id"] = str(directory["user_id"])
        if directory.get("parent_id"):
            directory["parent_id"] = str(directory["parent_id"])

    # Build query for documents
    doc_query = {"user_id": ObjectId(user_id)}
    if directory_id:
        doc_query["directory_id"] = ObjectId(directory_id)
    else:
        # Use $exists: false to find documents where directory_id is null or doesn't exist
        doc_query["directory_id"] = {"$exists": False}

    # Get documents
    documents = await document_collection.find(doc_query).to_list(length=None)

    # Convert ObjectId to string for response
    for document in documents:
        document["_id"] = str(document["_id"])
        document["user_id"] = str(document["user_id"])
        if document.get("directory_id"):
            document["directory_id"] = str(document["directory_id"])

    return {"directories": directories, "documents": documents}


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
        The moved document
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

    # Convert ObjectId to string for response
    updated_document["_id"] = str(updated_document["_id"])
    updated_document["user_id"] = str(updated_document["user_id"])
    if updated_document.get("directory_id"):
        updated_document["directory_id"] = str(updated_document["directory_id"])

    return updated_document
