from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey

_MAX_SKEW_SECONDS = 300


def is_allowed(user_id: str, allowed: frozenset[str]) -> bool:
    return bool(user_id) and user_id in allowed


def verify_signature(
    body: bytes,
    signature: str,
    timestamp: str,
    public_key: str,
    *,
    now: int,
) -> bool:
    if not public_key or not signature or not timestamp:
        return False
    try:
        sent = int(timestamp)
    except ValueError:
        return False
    if abs(now - sent) > _MAX_SKEW_SECONDS:
        return False
    try:
        key = VerifyKey(bytes.fromhex(public_key))
        key.verify(timestamp.encode() + body, bytes.fromhex(signature))
    except (BadSignatureError, ValueError):
        return False
    return True
