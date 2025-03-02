#!/usr/bin/env python3
"""
Migration script to add user_id field to existing document uploads.

This script should be run once to update existing documents in the database.
It will assign all existing documents to the specified admin user.
"""

import asyncio
import sys
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from config.environment import MongoSettings

# Replace with the admin user's ObjectId
ADMIN_USER_ID = "REPLACE_WITH_ADMIN_USER_ID"  # Replace this with an actual user ID


async def migrate_documents():
    # Connect to MongoDB
    mongo_settings = MongoSettings()
    client = AsyncIOMotorClient(mongo_settings.mongo_url)
    db = client[mongo_settings.mongo_db]

    # Validate admin user ID
    try:
        admin_id = ObjectId(ADMIN_USER_ID)
    except Exception:
        print("Error: Invalid admin user ID. Please provide a valid MongoDB ObjectId.")
        return

    # Check if admin user exists
    admin_user = await db.users.find_one({"_id": admin_id})
    if not admin_user:
        print(f"Error: Admin user with ID {ADMIN_USER_ID} not found in the database.")
        return

    # Get all documents without user_id
    documents_cursor = db.document_uploads.find({"user_id": {"$exists": False}})
    documents = await documents_cursor.to_list(length=None)

    if not documents:
        print("No documents found without user_id field. Migration not needed.")
        return

    print(f"Found {len(documents)} documents without user_id field.")

    # Update all documents to add user_id
    result = await db.document_uploads.update_many(
        {"user_id": {"$exists": False}}, {"$set": {"user_id": admin_id}}
    )

    print(f"Migration complete. Updated {result.modified_count} documents.")


if __name__ == "__main__":
    if ADMIN_USER_ID == "REPLACE_WITH_ADMIN_USER_ID":
        print("Error: Please replace ADMIN_USER_ID with an actual user ID.")
        sys.exit(1)

    asyncio.run(migrate_documents())
