import boto3
from decouple import config


class SESService(object):
    def __init__(self) -> None:
        self.key = config("AWS_ACCESS_KEY_ID")
        self.secret = config("AWS_SECRET_ACCESS_KEY")
        self.region = config("AWS_REGION")
        self.ses = boto3.client(
            "ses", region_name=self.region, aws_access_key_id=self.key, aws_secret_access_key=self.secret
        )

    def send_mail(self, subject_name, to_addresses, text_data):
        subject = {"Data": subject_name, "Charset": "UTF-8"}
        body = {"Text": {"Data": text_data, "Charset": "UTF-8"}}

        self.ses.send_email(
            Source="instantiatech@gmail.com",
            Destination={"ToAddresses": to_addresses, "CcAddresses": [], "BccAddresses": []},
            Message={"Subject": subject, "Body": body},
        )
