import json
from pickletools import TAKEN_FROM_ARGUMENT1
import uuid
from venv import create
from fastapi import HTTPException, status
from decouple import config
import requests


class WiseService(object):
    def __init__(self) -> None:
        self.main_url = config("WISE_URL")
        self.headers = {"Content-Type": "application/json", "Authorization": f"Bearer {config('WISE_TOKEN')}"}

        self.profile_id = self._get_profile_id()

    def _get_profile_id(self):
        url = f"{self.main_url}/v2/profiles"
        resp = requests.get(url, headers=self.headers)
        if resp.status_code == 200:
            resp = resp.json()
            return [el.get("id") for el in resp if el["type"] == "PERSONAL"][0]
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Payment provider is not available at the moment")

    def create_quote(self, amount):
        url = f"{self.main_url}/v3/profiles/{self.profile_id}/quotes"
        data = {
            "sourceCurrency": "EUR",
            "targetCurrency": "EUR",
            "sourceAmount": amount,
        }

        resp = requests.post(url, headers=self.headers, data=json.dumps(data))

        if resp.status_code == 200:
            resp = resp.json()
            return resp["id"]
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Payment provider is not available at the moment")

    def create_recipient_account(self, full_name, iban):
        url = f"{self.main_url}/v1/accounts"
        data = {
            "currency": "EUR",
            "type": "iban",
            "profile": self.profile_id,
            "ownedByCustomer": True,
            "accountHolderName": full_name,
            "details": {"iban": iban},
        }

        resp = requests.post(url, headers=self.headers, data=json.dumps(data))

        if resp.status_code == 200:
            resp = resp.json()
            return resp["id"]
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Payment provider is not available at the moment")

    def transfer(self, target_account_id, quote):
        customer_transaction_id = str(uuid.uuid4())
        url = f"{self.main_url}/v1/transfers"
        data = {
            "targetAccount": target_account_id,
            "quoteUuid": quote,
            "customerTransactionId": customer_transaction_id,
        }

        resp = requests.post(url, headers=self.headers, data=json.dumps(data))

        if resp.status_code == 200:
            resp = resp.json()
            return resp["id"]
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Payment provider is not available at the moment")

    def fund_transfer(self, transfer_id):
        url = f"{self.main_url}/v3/profiles/{self.profile_id}/transfers/{transfer_id}/payments"
        data = {"type": "BALANCE"}

        resp = requests.post(url, headers=self.headers, data=json.dumps(data))

        if resp.status_code == 201:
            resp = resp.json()
            return resp["status"], resp["errorCode"]
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Payment provider is not available at the moment")

    def cancel_funds(self, transfer_id):
        url = f"{self.main_url}/v1/transfers/{transfer_id}/cancel"
        resp = requests.put(url, headers=self.headers)

        if resp.status_code == 200:
            resp = resp.json()
            return resp["id"]
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Payment provider is not available at the moment")


if __name__ == "__main__":
    wise = WiseService()
    quote_id = wise.create_quote(23.33)
    recipient_id = wise.create_recipient_account("Takehiro Kitao", "AL35202111090000000001234567")
    transfer_id = wise.transfer(recipient_id, quote_id)
    res = wise.fund_transfer(transfer_id)
    print(res)
