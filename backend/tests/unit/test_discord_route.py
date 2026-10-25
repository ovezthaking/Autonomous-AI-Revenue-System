from app.main import app
from fastapi.testclient import TestClient
from nacl.signing import SigningKey


def test_discord_interactions_rejects_unsigned_or_unconfigured_requests():
    client = TestClient(app)
    res1 = client.post("/discord/interactions", content=b'{"type":1}')
    assert res1.status_code == 401

    signing = SigningKey.generate()
    body = b'{"type":1}'
    timestamp = "1700000000"
    signature = signing.sign(timestamp.encode() + body).signature.hex()
    res2 = client.post(
        "/discord/interactions",
        content=body,
        headers={
            "X-Signature-Ed25519": signature,
            "X-Signature-Timestamp": timestamp,
        },
    )
    assert res2.status_code == 401
