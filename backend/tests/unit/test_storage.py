from unittest.mock import MagicMock

from botocore.exceptions import ClientError
from revenue_swarm import storage
from revenue_swarm.config import STORAGE_ENDPOINT, STORAGE_PUBLIC_ENDPOINT


def test_client_uses_internal_endpoint_by_default_and_public_for_presigned(
    monkeypatch,
):
    captured: list[str | None] = []
    fake_s3 = MagicMock()
    fake_s3.generate_presigned_url.return_value = (
        "http://localhost:9000/signed"
    )

    def _fake_boto_client(service, **kwargs):
        captured.append(kwargs.get("endpoint_url"))
        return fake_s3

    monkeypatch.setattr(
        "revenue_swarm.storage.boto3.client", _fake_boto_client
    )

    storage.put("ebooks/test.pdf", b"pdf-bytes", "application/pdf")
    url = storage.presigned_url("ebooks/test.pdf", expires_in=300)

    assert captured == [STORAGE_ENDPOINT, STORAGE_PUBLIC_ENDPOINT]
    assert url == "http://localhost:9000/signed"


def test_ensure_bucket_exists_creates_bucket_on_404(monkeypatch):
    fake_s3 = MagicMock()
    fake_s3.head_bucket.side_effect = ClientError(
        {"Error": {"Code": "404", "Message": "Not Found"}}, "HeadBucket"
    )
    monkeypatch.setattr(
        "revenue_swarm.storage._client", lambda *, public=False: fake_s3
    )

    storage.ensure_bucket_exists()

    fake_s3.create_bucket.assert_called_once()


def test_get_returns_object_bytes(monkeypatch):
    fake_body = MagicMock()
    fake_body.read.return_value = b"ebook-data"
    fake_s3 = MagicMock()
    fake_s3.get_object.return_value = {"Body": fake_body}
    monkeypatch.setattr(
        "revenue_swarm.storage._client", lambda *, public=False: fake_s3
    )

    assert storage.get("ebooks/test.pdf") == b"ebook-data"
