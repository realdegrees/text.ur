from models.enums import AppErrorCode


class AppException(Exception):  # noqa: D101
    def __init__(self, status_code: int, error_code: AppErrorCode, detail: str) -> None:  # noqa: D107
        self.status_code = status_code
        self.error_code = error_code
        self.detail = detail
