from school_management_system_lite.core.config import get_settings
from school_management_system_lite.core.email.service import send_email


def build_account_activation_email(
    email: str, raw_activation_token: str
) -> tuple[str, str]:
    settings = get_settings()

    activation_link = f"{settings.APP_URL}/activation?token={raw_activation_token}"

    subject = "Activate your SMS Lite account"

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
                        Activate your account
                    </h2>

                    <p style="line-height: 1.6; margin: 0 0 16px;">
                        Hello,
                    </p>

                    <p style="line-height: 1.6; margin: 0 0 16px;">
                        An account has been created for you in
                        <strong>SMS Lite</strong>.
                    </p>

                    <p style="line-height: 1.6; margin: 0 0 16px;">
                        Your email is:
                    </p>

                    <div
                        style="
                            display: inline-block;
                            background-color: #f3f4f6;
                            padding: 10px 14px;
                            border-radius: 6px;
                            font-family: monospace;
                            font-size: 15px;
                            margin-bottom: 24px;
                        "
                    >
                        {email}
                    </div>

                    <p style="line-height: 1.6; margin: 0 0 16px;">
                        Click the button below to activate your account and create
                        your password.
                    </p>

                    <div style="text-align: center; margin: 32px 0;">
                        <a
                            href="{activation_link}"
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
                            Activate Account
                        </a>
                    </div>

                    <p
                        style="
                            font-size: 14px;
                            line-height: 1.6;
                            color: #6b7280;
                            margin: 0 0 12px;
                        "
                    >
                        This activation link will expire in
                        <strong>
                            {settings.ACTIVATION_TOKEN_EXPIRES_HOURS} hours
                        </strong>.
                    </p>

                    <p
                        style="
                            font-size: 13px;
                            line-height: 1.6;
                            color: #9ca3af;
                            margin: 24px 0 0;
                        "
                    >
                        If you were not expecting this email, you can safely ignore it.
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


async def send_account_activation_email(
    *,
    to_email: str,
    email: str,
    raw_activation_token: str,
) -> None:
    subject, html_body = build_account_activation_email(
        email=email,
        raw_activation_token=raw_activation_token,
    )

    await send_email(
        subject=subject,
        to_email=to_email,
        html_body=html_body,
    )
