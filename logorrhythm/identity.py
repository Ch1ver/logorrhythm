"""Lightweight shared-secret identity handshake."""

from __future__ import annotations

import hashlib
import hmac
import os


def issue_challenge() -> str:
    return os.urandom(12).hex()


def prove_identity(*, agent_id: str, challenge: str, shared_secret: str) -> str:
    msg = f"{agent_id}:{challenge}".encode("utf-8")
    return hmac.new(shared_secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()[:16]


def verify_identity(*, agent_id: str, challenge: str, shared_secret: str, proof: str) -> bool:
    expected = prove_identity(agent_id=agent_id, challenge=challenge, shared_secret=shared_secret)
    return hmac.compare_digest(expected, proof)
