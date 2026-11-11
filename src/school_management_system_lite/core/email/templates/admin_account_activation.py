from school_management_system_lite.core.config import get_settings
from school_management_system_lite.core.email.service import send_email


def build_admin_account_activation_email() -> tuple[str, str]:
    login_link = f"{get_settings().APP_URL}/auth/login"

    subject = "Your SMS Lite account has been activated"

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
                        Your account has been activated
                    </h2>

                    <p style="line-height: 1.6; margin: 0 0 16px;">
                        An administrator has activated your account.
                        You can now log in and access the system.
                    </p>

                    <div style="text-align: center; margin: 32px 0;">
                        <a
                            href="{login_link}"
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
                            Log In
                        </a>
                    </div>

                    <p
                        style="
                            font-size: 14px;
                            line-height: 1.6;
                            color: #6b7280;
                            margin: 24px 0 0;
                        "
                    >
                        If you were not expecting this, please contact your
                        administrator as soon as possible.
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


async def send_admin_account_activation_email(*, to_email: str) -> None:
    subject, html_body = build_admin_account_activation_email()

    await send_email(
        subject=subject,
        to_email=to_email,
        html_body=html_body,
    )
