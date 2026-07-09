from fastapi import HTTPException, status
from app.repositories.user import UserRepository
from app.schemas.user import UserCreate, UserResponse
from app.auth.utils import get_password_hash

class UserService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def register_user(self, user_in: UserCreate) -> dict:
        """
        Business logic to register a new user securely.
        """
        # 1. Check if user already exists
        existing_user = await self.user_repo.get_by_email(user_in.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email already exists."
            )

        # 2. Hash the password
        hashed_password = get_password_hash(user_in.password)

        # 3. Prepare data for database insertion
        # We drop the raw password and insert the hashed version
        user_data = user_in.model_dump(exclude={"password"})
        user_data["hashed_password"] = hashed_password

        # 4. Save to database
        created_user = await self.user_repo.create(user_data)
        
        return created_user
