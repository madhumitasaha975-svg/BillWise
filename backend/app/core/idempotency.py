import hashlib
import json
from typing import Any
from fastapi import Header, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.system import IdempotencyKey

from fastapi import Depends, Header, HTTPException, Request, Response, status
from app.core.database import get_db


def compute_request_hash(body: bytes) -> str:
    """Compute SHA-256 hash of the incoming request body."""
    return hashlib.sha256(body).hexdigest()


class IdempotentRequest:
    """Dependency that ensures non-safe billing/payment requests are idempotent."""

    def __init__(self, required: bool = True):
        self.required = required

    async def __call__(
        self,
        request: Request,
        session: AsyncSession = Depends(get_db),
        idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    ) -> IdempotencyKey | None:
        if not idempotency_key:
            if self.required:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Idempotency-Key header is required for this operation",
                )
            return None

        # Read the raw request body
        body = await request.body()
        req_hash = compute_request_hash(body)

        # Check if this key was already processed
        stmt = select(IdempotencyKey).where(IdempotencyKey.key == idempotency_key)
        result = await session.execute(stmt)
        record = result.scalar_one_or_none()

        if record:
            # Check if payload was tampered with
            if record.request_hash != req_hash:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Idempotency-Key already used with a different request payload",
                )

            # Replay the saved response
            raise HTTPException(
                status_code=record.response_status or 200,
                detail=record.response_body,
                headers={"X-Cache-Lookup": "HIT-IDEMPOTENT"},
            )

        # Record new key
        new_record = IdempotencyKey(
            key=idempotency_key,
            request_path=request.url.path,
            request_hash=req_hash,
        )
        session.add(new_record)
        await session.flush()
        return new_record