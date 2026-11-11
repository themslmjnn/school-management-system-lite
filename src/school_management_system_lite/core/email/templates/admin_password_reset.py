from httpx import AsyncClient

from school_management_system_lite.core.config import get_settings
from school_management_system_lite.core.email.service import send_email

settings = get_settings()


def build_admin_password_reset_email(raw_password_reset_token: str) -> tuple[str, str]:
    reset_password_link = (
        f"{settings.APP_URL}/reset-password?token={raw_password_reset_token}"
    )

    subject = "Your SMS Lite password reset link"

    html_body = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>

        <body
            style="
                margin: 0;
                padding: 0;
                font-family: Arial, sans-serif;
                background-color: #f5f6f8;
                color: #374151;
            "
        >
            <div style="padding: 40px 20px;">
                <div
                    style="
                        max-width: 560px;
                        margin: 0 auto;
                        background-color: #ffffff;
                        border-radius: 10px;
                        padding: 40px;
                        box-sizing: border-box;
                    "
                >
                    <h1
                        style="
                            margin: 0 0 30px;
                            font-size: 22px;
                            color: #1f2937;
                        "
                    >
                        SMS Lite
                    </h1>

                    <h2
                        style="
                            margin: 0 0 20px;
                            font-size: 20px;
                            color: #1f2937;
                        "
                    >
                        Reset your password
                    </h2>

                    <p style="line-height: 1.6; margin: 0 0 16px;">
                        An administrator has requested a password reset for your
                        account.
                    </p>

                    <p style="line-height: 1.6; margin: 0 0 16px;">
                        Click the button below to create a new password.
                    </p>

                    <div style="text-align: center; margin: 32px 0;">
                        <a
                            href="{reset_password_link}"
                            style="
                                display: inline-block;
                                background-color: #2563eb;
                                color: #ffffff;
                                padding: 13px 26px;
                                border-radius: 6px;
                                text-decoration: none;
                                font-weight: bold;
                            "
                        >
                            Reset Password
                        </a>
                    </div>

                    <div
                        style="
                            margin: 24px 0;
                            padding: 16px;
                            background-color: #f9fafb;
                            border-radius: 6px;
                        "
                    >
                        <p
                            style="
                                margin: 0;
                                font-size: 14px;
                                line-height: 1.6;
                                color: #6b7280;
                            "
                        >
                            This password reset link will expire in
                            <strong>
                                {settings.PASSWORD_RESET_TOKEN_EXPIRES_MINUTES} minutes
                            </strong>.
                        </p>
                    </div>

                    <p
                        style="
                            font-size: 14px;
                            line-height: 1.6;
                            color: #6b7280;
                            margin: 24px 0 0;
                        "
                    >
                        If you were not expecting this request, please contact
                        your administrator as soon as possible.
                    </p>
                </div>

                <p
                    style="
                        text-align: center;
                        font-size: 12px;
                        color: #9ca3af;
                        margin-top: 20px;
                    "
                >
                    © SMS Lite
                </p>
            </div>
        </body>
        </html>
    """

    return subject, html_body


async def send_admin_password_reset_token(
    resend_client: AsyncClient, to_email: str, raw_reset_password_token: str
) -> None:
    subject, html_body = build_admin_password_reset_email(raw_reset_password_token)

    await send_email(
        resend_client,
        subject,
        to_email,
        html_body,
    )
