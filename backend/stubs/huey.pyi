from typing import Any, Callable, TypeVar

T = TypeVar("T")

class RedisHuey:
    def __init__(
        self,
        name: str,
        host: str = ...,
        port: int = ...,
        db: int = ...,
        connection_pool: Any = ...,
        **kwargs: Any
    ) -> None: ...
    def task(self, **kwargs: Any) -> Callable[[Callable[..., T]], Callable[..., T]]: ...
    def current_task(self) -> Any: ...
