from bson import ObjectId
from PIL import Image, ImageDraw, ImageFont
import io
import tempfile
import os
from mypy_boto3_s3.client import S3Client
from config.mongo import TypedAsyncIOMotorDatabase
from config.environment import S3Settings
from db.models.document_uploads import (
    MongoDocumentUpload,
    MongoFileDetails,
    ThumbnailDetails,
)
from pdf2image import convert_from_bytes  # type: ignore[import]
import ebooklib
from ebooklib import epub
from openpyxl import load_workbook
import csv
import json
import markdown
from bs4 import BeautifulSoup
from docx import Document
from utils.file_type_normalizer import supported_file_types
from config.environment import PopplerSettings

poppler_settings = PopplerSettings()


class ThumbnailService:
    def __init__(self, db: TypedAsyncIOMotorDatabase, s3_client: S3Client):
        self.db = db
        self.s3_client = s3_client
        self.s3_settings = S3Settings()
        self.poppler_path = poppler_settings.poppler_path

    async def generate_and_store_thumbnail(self, document_upload_id: str) -> None:
        document = await self.get_document_upload(document_upload_id)
        if not document:
            raise ValueError(f"Document upload with id {document_upload_id} not found")

        file_details = document["file_details"]
        file_content = await self.get_file_content(file_details)

        normalized_file_type = self.get_normalized_file_type(file_details["file_type"])
        thumbnail = await self.generate_thumbnail(file_content, normalized_file_type)
        thumbnail_key = f"document_upload_thumbnails/{document_upload_id}.png"

        await self.store_thumbnail_in_s3(thumbnail, thumbnail_key)

        thumbnail_url = f"https://{self.s3_settings.s3_document_bucket}.{self.s3_settings.s3_host}/{thumbnail_key}"
        thumbnail_details = ThumbnailDetails(
            file_key=thumbnail_key,
            s3_bucket=self.s3_settings.s3_document_bucket,
            s3_url=thumbnail_url,
        )
        await self.update_document_with_thumbnail(document_upload_id, thumbnail_details)

    async def update_document_with_thumbnail(
        self, document_upload_id: str, thumbnail_details: ThumbnailDetails
    ) -> None:
        await self.db.document_uploads.update_one(
            {"_id": ObjectId(document_upload_id)},
            {"$set": {"thumbnail": thumbnail_details}},
        )

    async def get_document_upload(
        self, document_upload_id: str
    ) -> MongoDocumentUpload | None:
        return await self.db.document_uploads.find_one(
            {"_id": ObjectId(document_upload_id)}
        )

    async def get_file_content(self, file_details: MongoFileDetails) -> bytes:
        response = self.s3_client.get_object(
            Bucket=file_details["s3_bucket"], Key=file_details["file_key"]
        )
        return response["Body"].read()

    def get_normalized_file_type(self, file_type: str) -> str:
        """
        Get the normalized file type based on the supported_file_types mapping.
        If the file type is not found in the mapping, return 'unknown'.
        """
        return next(
            (key for key, value in supported_file_types.items() if value == file_type),
            "unknown",
        )

    async def generate_thumbnail(
        self, file_content: bytes, file_type: str
    ) -> Image.Image:
        if file_type == "pdf":
            return await self.generate_pdf_thumbnail(file_content)
        elif file_type == "epub":
            return await self.generate_ebook_thumbnail(file_content)
        elif file_type in ["csv", "excel"]:
            return await self.generate_spreadsheet_thumbnail(file_content, file_type)
        elif file_type in ["json", "markdown", "html", "text"]:
            return await self.generate_text_thumbnail(file_content, file_type)
        elif file_type == "word":
            return await self.generate_word_thumbnail(file_content)
        else:
            return await self.generate_default_thumbnail(file_type)

    async def generate_pdf_thumbnail(self, file_content: bytes) -> Image.Image:
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(file_content)
            temp_file_path = temp_file.name

        try:
            pages = convert_from_bytes(
                file_content, first_page=1, last_page=1, poppler_path=self.poppler_path
            )
            thumbnail = pages[0].resize((200, 200), Image.LANCZOS)
            return thumbnail
        finally:
            os.unlink(temp_file_path)

    async def generate_ebook_thumbnail(self, file_content: bytes) -> Image.Image:
        book = epub.read_epub(io.BytesIO(file_content))
        for item in book.get_items_of_type(ebooklib.ITEM_COVER):
            cover = Image.open(io.BytesIO(item.content))
            return cover.resize((200, 200), Image.LANCZOS)
        return await self.generate_default_thumbnail("epub")

    async def generate_spreadsheet_thumbnail(
        self, file_content: bytes, file_type: str
    ) -> Image.Image:
        text_content = ""
        if file_type == "csv":
            csv_content = io.StringIO(file_content.decode("utf-8"))
            csv_reader = csv.reader(csv_content)
            for _ in range(5):  # Get first 5 rows
                row = next(csv_reader, None)
                if row:
                    text_content += ",".join(row) + "\n"
        elif file_type == "excel":
            with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as temp_file:
                temp_file.write(file_content)
                temp_file_path = temp_file.name
            try:
                wb = load_workbook(filename=temp_file_path)
                sheet = wb.active
                for row in sheet.iter_rows(max_row=5, values_only=True):
                    text_content += ",".join(str(cell) for cell in row) + "\n"
            finally:
                os.unlink(temp_file_path)

        return self.text_to_image(text_content)

    async def generate_text_thumbnail(
        self, file_content: bytes, file_type: str
    ) -> Image.Image:
        text_content = file_content.decode("utf-8")
        if file_type == "json":
            parsed = json.loads(text_content)
            text_content = json.dumps(parsed, indent=2)[:500]  # First 500 chars
        elif file_type == "markdown":
            html = markdown.markdown(text_content)
            text_content = BeautifulSoup(html, "html.parser").get_text()[:500]
        elif file_type == "html":
            text_content = BeautifulSoup(text_content, "html.parser").get_text()[:500]
        elif file_type == "text":
            text_content = text_content[:500]

        return self.text_to_image(text_content)

    async def generate_word_thumbnail(self, file_content: bytes) -> Image.Image:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as temp_file:
            temp_file.write(file_content)
            temp_file_path = temp_file.name

        try:
            doc = Document(temp_file_path)
            text_content = ""
            for paragraph in doc.paragraphs[:10]:  # Get first 10 paragraphs
                text_content += paragraph.text + "\n"

            text_content = text_content.strip()[:500]  # Limit to 500 characters
            return self.text_to_image(text_content, "Word Document")
        except Exception as e:
            print(f"Error processing Word document: {e}")
            return await self.generate_default_thumbnail("word")
        finally:
            os.unlink(temp_file_path)

    def text_to_image(self, text: str, title: str = "") -> Image.Image:
        img = Image.new("RGB", (200, 200), color="white")
        d = ImageDraw.Draw(img)
        font = ImageFont.load_default()

        # Draw title if provided
        if title:
            d.text((10, 10), title, fill="black", font=font)
            start_y = 30
        else:
            start_y = 10

        # Wrap text
        words = text.split()
        lines = []
        current_line = []
        for word in words:
            if d.textsize(" ".join(current_line + [word]), font=font)[0] <= 180:
                current_line.append(word)
            else:
                lines.append(" ".join(current_line))
                current_line = [word]
        lines.append(" ".join(current_line))

        # Draw wrapped text
        y = start_y
        for line in lines:
            d.text((10, y), line, fill="black", font=font)
            y += font.getsize(line)[1] + 2
            if y > 190:  # Stop if we've reached the bottom of the image
                break

        return img

    async def generate_default_thumbnail(self, file_type: str) -> Image.Image:
        img = Image.new("RGB", (200, 200), color="lightgray")
        d = ImageDraw.Draw(img)
        font = ImageFont.load_default()
        d.text((10, 10), f"{file_type.upper()} File", fill="black", font=font)
        return img

    async def store_thumbnail_in_s3(
        self, thumbnail: Image.Image, thumbnail_key: str
    ) -> None:
        buffer = io.BytesIO()
        thumbnail.save(buffer, format="PNG")
        buffer.seek(0)

        self.s3_client.put_object(
            Bucket=self.s3_settings.s3_document_bucket,
            Key=thumbnail_key,
            Body=buffer,
            ContentType="image/png",
        )
