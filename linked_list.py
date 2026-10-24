"""LRU 순서를 관리하는 이중 연결 리스트."""


class Node:
    """앞뒤 노드와 저장된 데이터를 보유한다."""

    def __init__(self, data):
        self.prev = None
        self.next = None
        self.data = data


class DoublyLinkedList:
    """주어진 노드의 삽입, 삭제, 이동을 O(1)에 수행한다."""

    def __init__(self):
        self.head = Node(None)  # 시작/끝 가상 노드로 빈 리스트도 동일하게 처리
        self.tail = Node(None)
        self.head.next = self.tail
        self.tail.prev = self.head
        self._size = 0

    def _attach(self, left, node, right):
        node.prev = left
        node.next = right
        left.next = node
        right.prev = node

    def _detach(self, node):
        node.prev.next = node.next
        node.next.prev = node.prev
        node.prev = None
        node.next = None

    def insert_front(self, data):
        """앞에 새 노드를 넣고 그 노드를 반환한다."""
        node = Node(data)
        self._attach(self.head, node, self.head.next)
        self._size += 1
        return node

    def insert_back(self, data):
        """뒤에 새 노드를 넣고 그 노드를 반환한다."""
        node = Node(data)
        self._attach(self.tail.prev, node, self.tail)
        self._size += 1
        return node

    def remove_node(self, node):
        """이미 알고 있는 노드를 O(1)에 제거한다."""
        if node is self.head or node is self.tail or node.prev is None:
            raise ValueError("list에 연결된 데이터 노드가 필요합니다")
        self._detach(node)
        self._size -= 1
        return node

    def remove_front(self):
        """첫 번째 데이터 노드를 제거한다. 비어 있으면 None."""
        if self._size == 0:
            return None
        return self.remove_node(self.head.next)

    def remove_back(self):
        """마지막 데이터 노드를 제거한다. 비어 있으면 None."""
        if self._size == 0:
            return None
        return self.remove_node(self.tail.prev)

    def move_to_front(self, node):
        """기존 노드를 재생성하지 않고 맨 앞으로 옮긴다."""
        if node is self.head or node is self.tail or node.prev is None:
            raise ValueError("list에 연결된 데이터 노드가 필요합니다")
        if node.prev is self.head:
            return
        self._detach(node)
        self._attach(self.head, node, self.head.next)

    def size(self):
        return self._size
