from typing import Protocol, Coroutine, Any, Dict, Optional

class PubSub(Protocol):
    def subscribe(self, *args: str) -> Coroutine[Any, Any, Any]: ...
    def get_message(
        self, ignore_subscribe_messages: bool = False
    ) -> Coroutine[Any, Any, Optional[Dict[str, Any]]]: ...
    def unsubscribe(self) -> Coroutine[Any, Any, Any]: ...