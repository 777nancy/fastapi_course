from fastapi import APIRouter, Depends, status
from managers.complaint import ComplaintManager
from managers.user import UserManager, is_admin, is_approver, is_complainer
from schemas.request.complaint import ComplaintIn
from schemas.response.complaint import ComplaintOut

router = APIRouter(tags=["Complaints"])


@router.get("/complaints/")
async def get_complaints(user=Depends(UserManager.get_current_user)):
    return await ComplaintManager.get_complaints(user)


@router.post("/complaints/", response_model=ComplaintOut)
async def create_complaint(complaint: ComplaintIn, user=Depends(is_complainer)):
    return await ComplaintManager.create_complaint(complaint.dict(), user)


@router.delete("/complaints/{complaint_id}", dependencies=[Depends(is_admin)], status_code=status.HTTP_204_NO_CONTENT)
async def delete_complaint(complaint_id: int):
    await ComplaintManager.delete(complaint_id)


@router.put(
    "/complaints/{complaint_id}/approve", dependencies=[Depends(is_approver)], status_code=status.HTTP_204_NO_CONTENT
)
async def approve_complaint(complaint_id: int):
    await ComplaintManager.approve(complaint_id)


@router.put(
    "/complaints/{complaint_id}/reject", dependencies=[Depends(is_approver)], status_code=status.HTTP_204_NO_CONTENT
)
async def reject_complaint(complaint_id: int):
    await ComplaintManager.reject(complaint_id)
