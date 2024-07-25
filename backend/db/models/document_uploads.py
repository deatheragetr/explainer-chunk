from typing import TypedDict

# This is the model for the MongoDB document in the collection 'document_uploads'
# Uses Typed Dict to define the structure of the document since that actually works with mongo/motor
class MongoFileDetails(TypedDict):
    file_name: str
    file_type: str
    file_key: str
    s3_url: str

class MongoDocumentUpload(TypedDict):
    file_details: MongoFileDetails
