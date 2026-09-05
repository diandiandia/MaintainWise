from contextvars import ContextVar

current_user_id: ContextVar[int] = ContextVar("current_user_id", default=None)
current_username: ContextVar[str] = ContextVar("current_username", default=None)