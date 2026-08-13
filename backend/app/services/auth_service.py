from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.auth import TokenResponse


class AuthService:
    """Service handling user authentication and registration business logic."""

    def get_user_by_email(self, db: Session, email: str) -> User | None:
        """Fetch a single User by normalized email."""
        normalized_email = email.strip().lower() if email else ""
        return db.query(User).filter(User.email == normalized_email).first()

    def register(self, db: Session, email: str, password: str) -> User:
        """Register a new user with normalized email and Argon2id password hash."""
        normalized_email = email.strip().lower()
        existing_user = self.get_user_by_email(db, normalized_email)
        if existing_user:
            raise ValueError("User with this email already exists")

        password_hash = hash_password(password)
        user = User(
            email=normalized_email,
            password_hash=password_hash,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        from app.services.workspace_service import workspace_service
        workspace_service.get_or_create_default_workspace(db, user)

        return user

    register_user = register

    def authenticate_user(self, db: Session, email: str, password: str) -> User:
        """Authenticate user by email and password.
        
        Returns User ORM object if credentials match.
        Raises ValueError('Invalid email or password') if email is nonexistent or password is incorrect.
        """
        normalized_email = email.strip().lower() if email else ""
        user = self.get_user_by_email(db, normalized_email)

        if not user or not verify_password(password, user.password_hash):
            raise ValueError("Invalid email or password")

        return user

    def create_user_token(self, user: User) -> TokenResponse:
        """Generate JWT access token response for an authenticated user."""
        token, expires_in = create_access_token(subject=user.id)
        return TokenResponse(
            access_token=token,
            token_type="bearer",
            expires_in=expires_in,
        )

    def update_profile(self, db: Session, user: User, full_name: str | None) -> User:
        """Update authenticated user profile metadata."""
        user.full_name = full_name.strip() if full_name and full_name.strip() else None
        db.commit()
        db.refresh(user)
        return user

    def change_password(self, db: Session, user: User, current_password: str, new_password: str) -> User:
        """Securely verify current password and update user password hash."""
        if not verify_password(current_password, user.password_hash):
            raise ValueError("Incorrect current password")

        if len(new_password) < 8:
            raise ValueError("New password must be at least 8 characters long")

        user.password_hash = hash_password(new_password)
        db.commit()
        db.refresh(user)
        return user


auth_service = AuthService()
