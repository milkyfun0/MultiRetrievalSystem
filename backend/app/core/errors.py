from typing import Any

from fastapi import HTTPException, status


class ApiError(HTTPException):
    def __init__(
        self,
        code: str,
        message: str,
        detail: dict[str, Any] | None = None,
        retryable: bool = False,
        status_code: int = status.HTTP_400_BAD_REQUEST,
    ):
        super().__init__(
            status_code=status_code,
            detail={
                "code": code,
                "message": message,
                "detail": detail or {},
                "retryable": retryable,
            },
        )
