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


def test_discord_interactions_handles_signed_requests(monkeypatch):
    from unittest.mock import MagicMock

    import app.api.discord as discord_api

    signing = SigningKey.generate()
    public_key = signing.verify_key.encode().hex()
    monkeypatch.setattr(discord_api, "DISCORD_PUBLIC_KEY", public_key)

    fake_db = MagicMock()
    monkeypatch.setattr(discord_api, "SessionLocal", lambda: fake_db)

    client = TestClient(app)
    now = 1700000000
    monkeypatch.setattr(discord_api.time, "time", lambda: now)

    def _signed_post(raw: bytes):
        ts = str(now)
        sig = signing.sign(ts.encode() + raw).signature.hex()
        return client.post(
            "/discord/interactions",
            content=raw,
            headers={
                "X-Signature-Ed25519": sig,
                "X-Signature-Timestamp": ts,
            },
        )

    # 1. Invalid JSON
    r_bad_json = _signed_post(b"{not-json")
    assert r_bad_json.status_code == 400
    assert r_bad_json.json() == {"error": "invalid json"}

    # 2. Valid JSON but not a dict
    r_list_json = _signed_post(b"[1, 2, 3]")
    assert r_list_json.status_code == 400
    assert r_list_json.json() == {"error": "invalid json"}

    # 3. Valid PING interaction -> calls _handle and closes session
    r_ping = _signed_post(b'{"type": 1}')
    assert r_ping.status_code == 200
    assert r_ping.json() == {"type": 1}
    fake_db.close.assert_called_once()
