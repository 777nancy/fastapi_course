import os
import uuid
from models import transaction
from services.wise import WiseService

from db import database
from models import complaint
from models.enums import RoleType, State
from services.s3 import S3Service
from services.ses import SESService
import constants
from utils.helpers import decode_photo

s3 = S3Service()
ses = SESService()
wise = WiseService()


class ComplaintManager(object):
    @staticmethod
    async def get_complaints(user):
        q = complaint.select()
        if user["role"].value == RoleType.complainer.value:
            q = q.where(complaint.c.complainer_id == user["id"])
        elif user["role"].value == RoleType.approver.value:
            q = q.where(complaint.c.status == State.pending)
        return await database.fetch_all(q)

    @staticmethod
    @database.transaction()
    async def create_complaint(complaint_data, user):
        complaint_data["complainer_id"] = user["id"]
        encoded_photo = complaint_data.pop("encoded_photo")
        extension = complaint_data.pop("extension")
        name = f"{uuid.uuid4()}.{extension}"
        path = os.path.join(constants.TEMP_FILE_FOLDER, name)
        decode_photo(path, encoded_photo)
        complaint_data["photo_url"] = s3.upload(path, name, extension)
        os.remove(path)
        id_ = await database.execute(complaint.insert().values(complaint_data))
        await ComplaintManager.issue_transaction(
            complaint_data["amount"],
            f"{user['first_name']} {user['last_name']}",
            user["iban"],
            id_,
        )
        return await database.fetch_one(complaint.select().where(complaint.c.id == id_))  # type: ignore

    @staticmethod
    @database.transaction()
    async def delete(complaint_id):
        await database.execute(complaint.delete().where(complaint.c.id == complaint_id))

    @staticmethod
    @database.transaction()
    async def approve(id_: int):
        await database.execute(complaint.update().where(complaint.c.id == id_).values(status=State.approved))
        transaction_data = await database.fetch_one(transaction.select().where(transaction.c.complaint_id == id_))  # type: ignore
        wise.fund_transfer(transaction_data["transfer_id"])  # type: ignore
        ses.send_mail(
            "Complaint approved",
            ["takehiro.kitao.0925@gmail.com"],
            "Congrats! Your claim is approved, check your bank account in 2 days for your refund.",
        )

    @staticmethod
    @database.transaction()
    async def reject(id_: int):
        transaction_data = await database.fetch_one(transaction.select().where(transaction.c.complaint_id == id_))  # type: ignore
        wise.cancel_funds(transaction_data["transfer_id"])  # type: ignore
        await database.execute(complaint.update().where(complaint.c.id == id_).values(status=State.rejected))

    @staticmethod
    @database.transaction()
    async def issue_transaction(amount, full_name, iban, complaint_id):
        quote_id = wise.create_quote(amount)
        recipient_id = wise.create_recipient_account(full_name, iban)
        transfer_id = wise.transfer(recipient_id, quote_id)
        data = {
            "quote_id": quote_id,
            "transfer_id": transfer_id,
            "target_account_id": str(recipient_id),
            "amount": amount,
            "complaint_id": complaint_id,
        }
        await database.execute(transaction.insert().values(**data))
