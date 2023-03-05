from fastapi import APIRouter, Depends, status
from managers.user import UserManager, is_admin
from models.enums import RoleType
from schemas.response.user import UserOut

router = APIRouter(tags=["Users"])


@router.get("/users", dependencies=[Depends(is_admin)], response_model=UserOut | list[UserOut])
async def get_users(email: str | None = None):
    if email:
        return await UserManager.get_user_by_email(email)

    return await UserManager.get_all_users()


@router.put("/users/{user_id}/make-admin", dependencies=[Depends(is_admin)], status_code=status.HTTP_204_NO_CONTENT)
async def make_admin(user_id: int):
    await UserManager.change_role(RoleType.admin, user_id)


@router.put("/users/{user_id}/make-approver", dependencies=[Depends(is_admin)], status_code=status.HTTP_204_NO_CONTENT)
async def make_approver(user_id: int):
    await UserManager.change_role(RoleType.approver, user_id)

