import boto3
from decouple import config
from fastapi import HTTPException, status


class S3Service(object):
    def __init__(self):
        self.key = config("AWS_ACCESS_KEY_ID")
        self.secret = config("AWS_SECRET_ACCESS_KEY")
        self.s3 = boto3.client("s3", aws_access_key_id=self.key, aws_secret_access_key=self.secret)
        self.bucket = config("AWS_BUCKET_NAME")
        self.region = config("AWS_REGION")

    def upload(self, path, key, ext):
        try:
            self.s3.upload_file(
                path, self.bucket, key, ExtraArgs={"ACL": "public-read", "ContentType": f"image/{ext}"}
            )

            return f"https://{self.bucket}.s3.{self.region}.amazonaws.com/{key}"
        except Exception:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "S3 is not available")
