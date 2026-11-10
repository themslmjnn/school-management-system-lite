class UsersCacheKeys:
    @staticmethod
    def detailed_response_key_admin(user_id: int) -> str:
        return f"users:response:detailed:{user_id}:admin"

    @staticmethod
    def detailed_response_key_staff(user_id: int) -> str:
        return f"users:response:detailed:{user_id}:staff"

    @staticmethod
    def detailed_response_key_self(user_id: int) -> str:
        return f"users:response:detailed:{user_id}:self"
