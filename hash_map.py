"""직접 만든 해시 함수와 체이닝을 사용하는 문자열 키 해시맵."""


class _Entry:
    """충돌한 키들을 단방향으로 연결하는 버킷 노드."""

    def __init__(self, key, value, next_entry=None):
        self.key = key
        self.value = value
        self.next = next_entry


class HashMap:
    """평균 O(1) 조회/저장/삭제, 로드 팩터 0.75 초과 시 두 배 확장."""

    def __init__(self, capacity=8):
        if capacity < 1:
            raise ValueError("capacity는 1 이상이어야 합니다")
        self._buckets = [None] * capacity
        self._size = 0

    def _index(self, key, capacity):
        # UTF-8의 각 바이트로 계산하므로 실행마다 해시 결과가 같다.
        index = 0
        for byte in key.encode("utf-8"):
            index = (index * 31 + byte) % capacity
        return index

    def _resize(self):
        new_capacity = len(self._buckets) * 2
        new_buckets = [None] * new_capacity
        for head in self._buckets:
            entry = head
            while entry is not None:
                next_entry = entry.next
                index = self._index(entry.key, new_capacity)
                entry.next = new_buckets[index]
                new_buckets[index] = entry
                entry = next_entry
        self._buckets = new_buckets

    def put(self, key, value):
        """키를 저장한다. 덮어쓴 경우 이전 값을 반환한다."""
        index = self._index(key, len(self._buckets))
        entry = self._buckets[index]
        while entry is not None:
            if entry.key == key:
                previous = entry.value
                entry.value = value
                return previous
            entry = entry.next

        self._buckets[index] = _Entry(key, value, self._buckets[index])
        self._size += 1
        if self._size * 4 > len(self._buckets) * 3:
            self._resize()
        return None

    def get(self, key):
        """키에 해당하는 값, 없으면 None을 반환한다."""
        entry = self._buckets[self._index(key, len(self._buckets))]
        while entry is not None:
            if entry.key == key:
                return entry.value
            entry = entry.next
        return None

    def contains(self, key):
        entry = self._buckets[self._index(key, len(self._buckets))]
        while entry is not None:
            if entry.key == key:
                return True
            entry = entry.next
        return False

    def remove(self, key):
        """체인에서 키를 찾아 제거하고 이전 값을 반환한다."""
        index = self._index(key, len(self._buckets))
        previous = None
        entry = self._buckets[index]
        while entry is not None:
            if entry.key == key:
                if previous is None:
                    self._buckets[index] = entry.next
                else:
                    previous.next = entry.next
                self._size -= 1
                return entry.value
            previous = entry
            entry = entry.next
        return None

    def keys(self):
        result = []
        for head in self._buckets:
            entry = head
            while entry is not None:
                result.append(entry.key)
                entry = entry.next
        return result

    def size(self):
        return self._size
