from app.services.discord_auth import is_allowed, verify_signature
from nacl.signing import SigningKey


def test_empty_allowlist_denies_everyone():
    assert is_allowed("123", frozenset()) is False


def test_allowlist_checks_exact_id():
    allowed = frozenset({"123"})
    assert is_allowed("123", allowed) is True
    assert is_allowed("124", allowed) is False
    assert is_allowed("", allowed) is False


def test_verify_signature_accepts_a_real_key():
    signing = SigningKey.generate()
    body = b'{"type":1}'
    timestamp = "1700000000"
    signature = signing.sign(timestamp.encode() + body).signature.hex()
    public_key = signing.verify_key.encode().hex()
    assert verify_signature(
        body, signature, timestamp, public_key, now=1700000000
    )


def test_verify_signature_rejects_skew_and_tampering():
    signing = SigningKey.generate()
    body = b'{"type":1}'
    timestamp = "1700000000"
    signature = signing.sign(timestamp.encode() + body).signature.hex()
    public_key = signing.verify_key.encode().hex()
    assert (
        verify_signature(
            body, signature, timestamp, public_key, now=1700000401
        )
        is False
    )
    assert (
        verify_signature(
            body + b"x", signature, timestamp, public_key, now=1700000000
        )
        is False
    )
    assert (
        verify_signature(body, signature, timestamp, "", now=1700000000)
        is False
    )
