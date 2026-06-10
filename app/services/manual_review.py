from app.models.notifications import ManualReviewItem


class ManualReviewQueue:
    def __init__(self) -> None:
        self._items: list[ManualReviewItem] = []

    def enqueue(self, item: ManualReviewItem) -> None:
        self._items.append(item)

    def list_items(self) -> list[ManualReviewItem]:
        return list(self._items)


manual_review_queue = ManualReviewQueue()


def get_manual_review_queue() -> ManualReviewQueue:
    return manual_review_queue

