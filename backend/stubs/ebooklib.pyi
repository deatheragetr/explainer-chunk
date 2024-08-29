from typing import Any, List, Iterator

ITEM_COVER: str
ITEM_DOCUMENT: str
ITEM_NAVIGATION: str
ITEM_IMAGE: str
ITEM_STYLE: str
ITEM_SCRIPT: str
ITEM_FONT: str
ITEM_AUDIO: str
ITEM_VIDEO: str

class EpubItem:
    id: str
    file_name: str
    media_type: str
    content: bytes

class EpubBook:
    def get_items(self) -> List[EpubItem]: ...
    def get_items_of_type(self, item_type: str) -> Iterator[EpubItem]: ...

class epub:
    @staticmethod
    def read_epub(path: str) -> EpubBook: ...
    @staticmethod
    def write_epub(
        path: str, book: EpubBook, options: dict[str, Any] = ...
    ) -> None: ...
