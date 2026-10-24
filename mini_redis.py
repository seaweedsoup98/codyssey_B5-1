"""해시맵 + 이중 연결 리스트 + 최소 힙을 연결한 Mini Redis."""

import json
import shlex
import time

from hash_map import HashMap
from linked_list import DoublyLinkedList
from min_heap import MinHeap

INTEGER_ERROR = "(error) ERR value is not an integer or out of range"
OOM_ERROR = "(error) OOM command not allowed when used_memory > 'maxmemory'"


class _Value:
    """값과 LRU 노드, TTL 정보를 하나의 해시맵 값으로 보관한다."""

    def __init__(self, value, node):
        self.value = value
        self.node = node
        self.expires_at = None
        self.expire_version = None


class MiniRedis:
    """문자열 명령을 실행하고 Redis 스타일 결과를 돌려준다."""

    def __init__(self, clock=None):
        self._clock = clock if clock is not None else time.monotonic
        self._data = HashMap()
        self._lru = DoublyLinkedList()
        self._expirations = MinHeap()
        self._used_memory = 0
        self._maxmemory = 0  # 0: 무제한
        self._evicted_keys = 0
        self._next_expire_version = 0

    def _entry_bytes(self, key, value):
        return len(key.encode("utf-8")) + len(value.encode("utf-8"))

    def _delete(self, key, evicted=False):
        """데이터, LRU 노드, 메모리 사용량을 항상 함께 정리한다."""
        entry = self._data.remove(key)
        if entry is None:
            return False
        self._lru.remove_node(entry.node)
        self._used_memory -= self._entry_bytes(key, entry.value)
        if evicted:
            self._evicted_keys += 1
        # 힙에 남은 이전 만료 예약은 _purge_expired에서 무시한다.
        return True

    def _purge_expired(self):
        """힙의 가장 빠른 예약부터 검사해 만료된 키를 지운다."""
        now = self._clock()
        while self._expirations.size() and self._expirations.peek()[0] <= now:
            expires_at, version, key = self._expirations.pop()
            entry = self._data.get(key)
            if (entry is not None and entry.expires_at == expires_at
                    and entry.expire_version == version):
                self._delete(key)

    def _set(self, key, value):
        size = self._entry_bytes(key, value)
        if self._maxmemory and size > self._maxmemory:
            return OOM_ERROR  # 기존 키를 덮어쓰려던 경우도 원래 값을 보존한다.

        entry = self._data.get(key)
        if entry is None:
            node = self._lru.insert_front(key)
            self._data.put(key, _Value(value, node))
            self._used_memory += size
        else:
            self._used_memory += size - self._entry_bytes(key, entry.value)
            entry.value = value
            entry.expires_at = None  # SET으로 덮어쓰면 TTL 초기화
            entry.expire_version = None
            self._lru.move_to_front(entry.node)

        while self._maxmemory and self._used_memory > self._maxmemory:
            oldest_key = self._lru.tail.prev.data
            self._delete(oldest_key, evicted=True)
        return "OK"

    def _get(self, key):
        entry = self._data.get(key)
        if entry is None:
            return "(nil)"
        self._lru.move_to_front(entry.node)
        return json.dumps(entry.value, ensure_ascii=False)

    def _expire(self, key, seconds):
        entry = self._data.get(key)
        if entry is None:
            return "(integer) 0"
        if seconds <= 0:
            self._delete(key)
            return "(integer) 1"
        self._next_expire_version += 1
        entry.expires_at = self._clock() + seconds
        entry.expire_version = self._next_expire_version
        self._expirations.push((entry.expires_at, entry.expire_version, key))
        return "(integer) 1"

    def _ttl(self, key):
        entry = self._data.get(key)
        if entry is None:
            return "(integer) -2"
        if entry.expires_at is None:
            return "(integer) -1"
        return "(integer) " + str(max(0, int(entry.expires_at - self._clock())))

    def _wrong_args(self, command):
        return "(error) ERR wrong number of arguments for '{}' command".format(command)

    def execute(self, line):
        """한 줄 파싱 → 만료 정리 → 명령 실행 → 출력 문자열 반환."""
        self._purge_expired()
        try:
            parts = shlex.split(line)
        except ValueError:
            return "(error) ERR invalid quoting"
        if not parts:
            return ""

        command = parts[0].upper()
        args = parts[1:]
        lengths = (("SET", 2), ("GET", 1), ("DEL", 1),
                   ("EXISTS", 1), ("DBSIZE", 0), ("KEYS", 0),
                   ("EXPIRE", 2), ("TTL", 1))
        for name, count in lengths:
            if command == name and len(args) != count:
                return self._wrong_args(command)

        if command == "SET":
            return self._set(args[0], args[1])
        if command == "GET":
            return self._get(args[0])
        if command == "DEL":
            return "(integer) " + str(int(self._delete(args[0])))
        if command == "EXISTS":
            return "(integer) " + str(int(self._data.contains(args[0])))
        if command == "DBSIZE":
            return "(integer) " + str(self._data.size())
        if command == "KEYS":
            keys = self._data.keys()
            if not keys:
                return "(empty array)"
            return "\n".join("{}. {}".format(i, json.dumps(key, ensure_ascii=False))
                             for i, key in enumerate(keys, start=1))
        if command == "CONFIG":
            if len(args) != 3 or args[0].upper() != "SET" or args[1].lower() != "maxmemory":
                return self._wrong_args(command)
            try:
                limit = int(args[2])
            except ValueError:
                return INTEGER_ERROR
            if limit < 0:
                return INTEGER_ERROR
            self._maxmemory = limit
            return "OK"
        if command == "INFO":
            if len(args) != 1 or args[0].lower() != "memory":
                return self._wrong_args(command)
            return "used_memory:{}\nmaxmemory:{}\nevicted_keys:{}".format(
                self._used_memory, self._maxmemory, self._evicted_keys
            )
        if command == "EXPIRE":
            try:
                seconds = int(args[1])
            except ValueError:
                return INTEGER_ERROR
            return self._expire(args[0], seconds)
        if command == "TTL":
            return self._ttl(args[0])
        return "(error) ERR unknown command '{}'".format(parts[0])
