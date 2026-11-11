from enum import StrEnum


class EmailType(StrEnum):
    ACCOUNT_ACTIVATION = "account_activation"
    ADMIN_USER_IDENTITY_OVERRIDE = "admin_user_identity_override"
    ADMIN_USER_EMAIL_OVERRIDE = "admin_user_email_override"
    ADMIN_ACCOUNT_DEACTIVATION = "admin_account_deactivation"
    ADMIN_ACCOUNT_ACTIVATION = "admin_account_activation"
    ADMIN_PASSWORD_RESET = "admin_password_reset"
    FORGOT_PASSWORD_REQUEST = "forgot_password_request"
    EMAIL_CHANGE_REQUEST = "email_change_request"
    EMAIL_CHANGE_CONFIRMATION = "email_change_confirmation"
    PASSWORD_CHANGE_CONFIRMATION = "password_change_confirmation"
    SELF_PROFILE_UPDATING = "self_profile_updating"


class EmailStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
