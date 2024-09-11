import os
from postmarker.core import PostmarkClient
from pydantic import EmailStr
from jose import jwt
from datetime import datetime, timedelta
import datetime as dt
from config.environment import CryptoSettings

from config.environment import EmailSettings

email_settings = EmailSettings()
crypto_settings = CryptoSettings()
postmark_client = PostmarkClient(server_token=email_settings.postmark_api_key)


def create_verification_token(email: str) -> str:
    expiration = datetime.now(dt.UTC) + timedelta(days=7)
    payload = {"sub": email, "exp": expiration}
    return jwt.encode(
        payload, crypto_settings.secret_key, algorithm=crypto_settings.algorithm
    )


async def send_verification_email(email: EmailStr, verification_url: str):
    template_alias = "welcome-email-and-verification"  # Replace with the actual template alias from Postmark
    template_model = {"verification_url": verification_url, "email": email}

    response = postmark_client.emails.send_with_template(
        TemplateAlias=template_alias,
        TemplateModel=template_model,
        From=email_settings.default_sender_email,
        To=email,
    )

    return response


async def send_email_change_verification(email: EmailStr, verification_url: str):
    template_alias = "email-change-verification"
    template_model = {"verification_url": verification_url, "email": email}

    response = postmark_client.emails.send_with_template(
        TemplateAlias=template_alias,
        TemplateModel=template_model,
        From=email_settings.default_sender_email,
        To=email,
    )

    return response
