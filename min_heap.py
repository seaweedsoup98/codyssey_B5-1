"""Python 리스트 위에 직접 구현한 이진 최소 힙."""


class MinHeap:
    """가장 작은 항목을 루트에 유지하는 우선순위 큐."""

    def __init__(self):
        self._items = []

    def _heapify_up(self, index):
        """새 항목을 부모와 비교하며 위로 올린다."""
        while index > 0:
            parent = (index - 1) // 2
            if self._items[parent] <= self._items[index]:
                break
            self._items[parent], self._items[index] = (
                self._items[index], self._items[parent]
            )
            index = parent

    def _heapify_down(self, index):
        """루트 항목을 더 작은 자식과 교환하며 아래로 내린다."""
        count = len(self._items)
        while 2 * index + 1 < count:
            child = 2 * index + 1
            if child + 1 < count and self._items[child + 1] < self._items[child]:
                child += 1
            if self._items[index] <= self._items[child]:
                break
            self._items[index], self._items[child] = (
                self._items[child], self._items[index]
            )
            index = child

    def push(self, item):
        """항목을 삽입한다: O(log n)."""
        self._items.append(item)
        self._heapify_up(len(self._items) - 1)

    def peek(self):
        """가장 작은 항목을 제거하지 않고 반환한다: O(1)."""
        return self._items[0] if self._items else None

    def pop(self):
        """가장 작은 항목을 꺼낸다: O(log n)."""
        if not self._items:
            return None
        minimum = self._items[0]
        last = self._items.pop()
        if self._items:
            self._items[0] = last
            self._heapify_down(0)
        return minimum

    def size(self):
        return len(self._items)
