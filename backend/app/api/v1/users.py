from fastapi import APIRouter, Depends
from app.api import deps
from app.models.user import User
from app.schemas.user import UserOut

router = APIRouter()

@router.get("/me", response_model=UserOut)
async def read_user_me(
    current_user: User = Depends(deps.get_current_active_user)
):
    """
    Acquire the profile of the current active authenticated user.
    """
    return current_user
