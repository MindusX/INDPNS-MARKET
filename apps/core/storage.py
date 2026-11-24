"""Stockage privé des fichiers vendus (jamais sous MEDIA_ROOT, jamais public)."""
from django.conf import settings
from django.core.files.storage import FileSystemStorage


def private_storage():
    if settings.S3_ENABLED:
        from storages.backends.s3boto3 import S3Boto3Storage

        class PrivateS3Storage(S3Boto3Storage):
            default_acl = "private"
            querystring_auth = True
            file_overwrite = False
            location = "private"

        return PrivateS3Storage()
    settings.PRIVATE_FILES_ROOT.mkdir(parents=True, exist_ok=True)
    return FileSystemStorage(location=str(settings.PRIVATE_FILES_ROOT), base_url=None)


def public_media_storage():
    if settings.S3_ENABLED:
        from storages.backends.s3boto3 import S3Boto3Storage

        class PublicS3Storage(S3Boto3Storage):
            default_acl = "public-read"
            querystring_auth = False
            file_overwrite = False
            location = "public"

        return PublicS3Storage()
    return FileSystemStorage()
