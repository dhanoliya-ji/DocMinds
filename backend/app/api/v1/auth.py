from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api import deps
from app.core import security
from app.core.config import settings
from app.models.organization import Organization
from app.models.user import User
from app.schemas.user import UserCreate, UserOut
from app.schemas.token import Token, TokenRefreshRequest, TokenPayload

router = APIRouter()

@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def signup(
    user_in: UserCreate,
    db: AsyncSession = Depends(deps.get_db)
):
    """
    Register a new user.
    If org_name is provided, a new tenant organization is created and the user is set as the 'Admin'.
    If org_id is provided, the user joins that organization with their specified role.
    """
    # Check if user already exists
    stmt = select(User).where(User.email == user_in.email)
    result = await db.execute(stmt)
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists in the system."
        )

    # Handle tenant onboarding logic
    if user_in.org_name:
        # User is initializing a brand new organization
        org = Organization(name=user_in.org_name)
        db.add(org)
        await db.flush()  # Populate org.id
        role = "Admin"     # Instantiator is the Admin
    elif user_in.org_id:
        # User is registering under an existing organization
        stmt = select(Organization).where(Organization.id == user_in.org_id)
        result = await db.execute(stmt)
        org = result.scalar_one_or_none()
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="The specified organization was not found."
            )
        role = user_in.role
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either org_name (create organization) or org_id (join organization) must be provided."
        )

    db_user = User(
        email=user_in.email,
        hashed_password=security.get_password_hash(user_in.password),
        role=role,
        org_id=org.id,
        is_active=True,
        is_verified=False
    )
    
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

@router.post("/login", response_model=Token)
async def login(
    db: AsyncSession = Depends(deps.get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    Authenticate email and password using standard OAuth2 form inputs, returning access & refresh tokens.
    """
    stmt = select(User).where(User.email == form_data.username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )
    elif not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This account has been deactivated."
        )

    # Embed tenant mappings in claims for rapid RBAC validation on stateless API calls
    access_token = security.create_access_token(
        subject=user.id,
        additional_claims={
            "org_id": str(user.org_id),
            "role": user.role
        }
    )
    refresh_token = security.create_refresh_token(subject=user.id)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.post("/refresh", response_model=Token)
async def refresh_token(
    payload: TokenRefreshRequest,
    db: AsyncSession = Depends(deps.get_db)
):
    """
    Exchange a valid refresh token for a brand new set of access/refresh tokens.
    """
    try:
        token_data = jwt.decode(
            payload.refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        refresh_payload = TokenPayload(**token_data)
        if refresh_payload.type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Provided token is not a refresh token."
            )
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token."
        )

    stmt = select(User).where(User.id == refresh_payload.sub)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )
    elif not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is deactivated."
        )

    access_token = security.create_access_token(
        subject=user.id,
        additional_claims={
            "org_id": str(user.org_id),
            "role": user.role
        }
    )
    new_refresh_token = security.create_refresh_token(subject=user.id)
    
    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }
