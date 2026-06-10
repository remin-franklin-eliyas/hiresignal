import hashlib


def hash_candidate_identifier(identifier: str) -> str:
    normalized = identifier.strip().lower().encode("utf-8")
    return hashlib.sha256(normalized).hexdigest()

