from enum import StrEnum


class EmailType(StrEnum):
    ACCOUNT_ACTIVATION = "account_activation"
    ADMIN_USER_IDENTITY_OVERRIDE = "admin_user_identity_override"
    ADMIN_USER_EMAIL_OVERRIDE = "admin_user_email_override"
    ADMIN_ACCOUNT_DEACTIVATION = "admin_account_deactivation"
    ADMIN_ACCOUNT_REACTIVATION = "admin_account_reactivation"
    ADMIN_PASSWORD_RESET = "admin_password_reset"
    FORGOT_PASSWORD_REQUEST = "forgot_password_request"
    EMAIL_CHANGE_REQUEST = "email_change_request"
    EMAIL_CHANGE_CONFIRMATION = "email_change_confirmation"
    PASSWORD_CHANGED_NOTIFICATION = "password_changed_notification"
    SELF_PROFILE_UPDATING = "self_profile_updating"


class EmailStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
