import asyncio
from bson import ObjectId
from typing import Any
from postmarker.exceptions import PostmarkerException
from config.mongo import TypedAsyncIOMotorDatabase
from utils.email_utils import create_verification_token, send_verification_email
from config.environment import AppSettings


class RegistrationService:
    def __init__(self, db: TypedAsyncIOMotorDatabase, logger: Any):
        self.db = db
        self.logger = logger
        self.app_settings = AppSettings()

    async def send_verification_email(self, user_id: str) -> None:
        max_retries = 5
        base_delay = 1  # 1 second

        for attempt in range(max_retries):
            try:
                user = await self.db.users.find_one({"_id": ObjectId(user_id)})
                if not user:
                    self.logger.error(f"User not found: {user_id}")
                    return

                verification_token = create_verification_token(user["email"])
                verification_url = f"{self.app_settings.app_base_url}/verify-email?token={verification_token}"

                self.logger.info(f"Sending verification email to user: {user_id}")
                await send_verification_email(user["email"], verification_url)

                self.logger.info(
                    f"Verification email sent successfully to user: {user_id}"
                )
                return

            except PostmarkerException as e:
                delay = base_delay * (2**attempt)
                self.logger.warning(f"Error sending verification email: {e}")
                self.logger.warning(
                    f"Attempt {attempt + 1} failed: {str(e)}. Retrying in {delay} seconds."
                )
                await asyncio.sleep(delay)

        self.logger.error(
            f"Failed to send verification email after {max_retries} attempts for user: {user_id}"
        )

    async def process_new_registration(self, user_id: str) -> None:
        try:
            await self.send_verification_email(user_id)
            # Add any additional registration-related tasks here
        except Exception as e:
            self.logger.error(
                f"Error processing new registration for user {user_id}: {str(e)}"
            )
