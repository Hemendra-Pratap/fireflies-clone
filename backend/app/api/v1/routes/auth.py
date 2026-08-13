from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserRead
from app.services.auth_service import auth_service

router = APIRouter()


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create a new user account with email and password.",
)
def register_user(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
) -> UserRead:
    """Register a new user account."""
    try:
        user = auth_service.register(db, email=payload.email, password=payload.password)
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="User login",
    description="Authenticate user with email and password and return a JWT access token.",
)
def login_user(
    payload: LoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Authenticate user credentials and issue a JWT access token."""
    try:
        user = auth_service.authenticate_user(db, email=payload.email, password=payload.password)
        return auth_service.create_user_token(user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.get(
    "/me",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Get current user",
    description="Fetch details of the currently authenticated user resolved from JWT bearer token.",
)
def get_me(
    current_user: User = Depends(get_current_user),
) -> UserRead:
    """Return profile metadata of current authenticated user."""
    return current_user
