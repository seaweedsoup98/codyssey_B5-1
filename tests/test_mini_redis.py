"""외부 의존성 없는 자료구조/명령어/CLI 검증."""

import os
import subprocess
import sys
import unittest

from hash_map import HashMap
from linked_list import DoublyLinkedList
from min_heap import MinHeap
from mini_redis import INTEGER_ERROR, OOM_ERROR, MiniRedis


class FakeClock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class LinkedListTests(unittest.TestCase):
    def test_insert_move_and_remove_both_ends(self):
        items = DoublyLinkedList()
        self.assertIsNone(items.remove_front())
        self.assertIsNone(items.remove_back())
        a = items.insert_front("a")
        b = items.insert_back("b")
        c = items.insert_back("c")
        self.assertEqual(items.size(), 3)
        items.move_to_front(c)
        self.assertIs(items.head.next, c)
        self.assertIs(items.tail.prev, b)
        self.assertIs(items.remove_back(), b)
        self.assertIs(items.remove_front(), c)
        self.assertIs(items.remove_front(), a)
        self.assertEqual(items.size(), 0)
        self.assertIs(items.head.next, items.tail)

    def test_remove_specific_and_reject_detached(self):
        items = DoublyLinkedList()
        a = items.insert_front("a")
        b = items.insert_front("b")
        c = items.insert_front("c")
        self.assertIs(items.remove_node(b), b)
        self.assertIs(c.next, a)
        self.assertIs(a.prev, c)
        with self.assertRaises(ValueError):
            items.remove_node(b)
        with self.assertRaises(ValueError):
            items.move_to_front(items.head)

    def test_move_first_is_no_op(self):
        items = DoublyLinkedList()
        node = items.insert_front("key")
        items.move_to_front(node)
        self.assertEqual(items.size(), 1)
        self.assertIs(items.head.next, node)


class HashMapTests(unittest.TestCase):
    def test_put_get_contains_remove_size(self):
        table = HashMap()
        self.assertIsNone(table.put("a", "one"))
        self.assertEqual(table.put("a", "two"), "one")
        self.assertEqual(table.get("a"), "two")
        self.assertEqual(table.size(), 1)
        self.assertTrue(table.contains("a"))
        self.assertFalse(table.contains("missing"))
        self.assertIsNone(table.remove("missing"))
        self.assertEqual(table.remove("a"), "two")
        self.assertEqual(table.keys(), [])
        self.assertFalse(table.contains("a"))

    def test_collision_chain_head_middle_tail(self):
        table = HashMap(capacity=8)
        # ASCII a=97, i=105, q=113 -> mod 8은 모두 1
        for key in ("a", "i", "q"):
            table.put(key, key.upper())
        self.assertEqual(table._index("a", 8), table._index("q", 8))
        self.assertEqual(table.remove("i"), "I")
        self.assertEqual(table.remove("q"), "Q")
        self.assertEqual(table.remove("a"), "A")
        self.assertEqual(table.size(), 0)

    def test_resize_retains_entries(self):
        table = HashMap(capacity=4)
        for i in range(24):
            table.put("key:" + str(i), str(i))
        self.assertGreaterEqual(len(table._buckets), 32)
        self.assertEqual(table.size(), 24)
        for i in range(24):
            self.assertEqual(table.get("key:" + str(i)), str(i))
        self.assertEqual(len(table.keys()), 24)

    def test_empty_key_unicode_and_none_value(self):
        table = HashMap()
        table.put("", None)
        table.put("한글", "😀")
        self.assertTrue(table.contains(""))
        self.assertIsNone(table.get(""))
        self.assertEqual(table.get("한글"), "😀")


class MinHeapTests(unittest.TestCase):
    def test_push_pop_sorted_and_peek(self):
        heap = MinHeap()
        self.assertIsNone(heap.peek())
        self.assertIsNone(heap.pop())
        for item in ((4, "d"), (1, "b"), (3, "c"), (1, "a"), (2, "z")):
            heap.push(item)
        self.assertEqual(heap.size(), 5)
        self.assertEqual(heap.peek(), (1, "a"))
        self.assertEqual([heap.pop() for _ in range(5)],
                         [(1, "a"), (1, "b"), (2, "z"), (3, "c"), (4, "d")])
        self.assertEqual(heap.size(), 0)


class MiniRedisTests(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.redis = MiniRedis(clock=self.clock)

    def run_command(self, line):
        return self.redis.execute(line)

    def test_string_commands_and_empty_store(self):
        self.assertEqual(self.run_command("GET absent"), "(nil)")
        self.assertEqual(self.run_command("dbsize"), "(integer) 0")
        self.assertEqual(self.run_command("keys"), "(empty array)")
        self.assertEqual(self.run_command("SET a one"), "OK")
        self.assertEqual(self.run_command("get a"), '"one"')
        self.assertEqual(self.run_command("EXISTS a"), "(integer) 1")
        self.assertIn('"a"', self.run_command("KEYS"))
        self.assertEqual(self.run_command("DEL a"), "(integer) 1")
        self.assertEqual(self.run_command("DEL a"), "(integer) 0")
        self.assertEqual(self.run_command("EXISTS a"), "(integer) 0")

    def test_quoted_values_spaces_escapes_and_utf8(self):
        self.assertEqual(self.run_command('SET person "Alice Kim"'), "OK")
        self.assertEqual(self.run_command("GET person"), '"Alice Kim"')
        self.assertEqual(self.run_command('SET greet "서울 😀"'), "OK")
        self.assertEqual(self.run_command("GET greet"), '"서울 😀"')
        self.assertEqual(self.run_command('SET empty ""'), "OK")
        self.assertEqual(self.run_command("GET empty"), '""')
        self.assertEqual(self.run_command('SET "spaced key" x'), "OK")
        self.assertIn('"spaced key"', self.run_command("KEYS"))

    def test_memory_counts_utf8_bytes(self):
        self.assertEqual(self.run_command("SET 가 😀"), "OK")
        self.assertIn("used_memory:7", self.run_command("INFO memory"))
        self.assertEqual(self.run_command("SET 가 hi"), "OK")
        self.assertIn("used_memory:5", self.run_command("INFO memory"))
        self.assertEqual(self.run_command("DEL 가"), "(integer) 1")
        self.assertIn("used_memory:0", self.run_command("INFO memory"))

    def test_lru_recent_get_changes_eviction(self):
        self.assertEqual(self.run_command("CONFIG SET maxmemory 6"), "OK")
        self.run_command("SET a 11")
        self.run_command("SET b 22")
        self.assertEqual(self.run_command("GET a"), '"11"')
        self.run_command("SET c 33")
        self.assertEqual(self.run_command("GET b"), "(nil)")
        self.assertEqual(self.run_command("GET a"), '"11"')
        self.assertEqual(self.run_command("GET c"), '"33"')
        self.assertEqual(self.run_command("INFO memory"),
                         "used_memory:6\nmaxmemory:6\nevicted_keys:1")

    def test_overwrite_mru_memory_and_eviction(self):
        self.run_command("CONFIG SET maxmemory 6")
        self.run_command("SET a 11")
        self.run_command("SET b 22")
        self.run_command("SET a 1234")
        self.assertEqual(self.run_command("GET b"), "(nil)")
        self.assertEqual(self.run_command("GET a"), '"1234"')
        self.assertIn("used_memory:5", self.run_command("INFO memory"))
        self.assertIn("evicted_keys:1", self.run_command("INFO memory"))

    def test_oversize_entry_rejected_without_mutation(self):
        self.run_command("CONFIG SET maxmemory 6")
        self.run_command("SET a xx")
        self.assertEqual(self.run_command("SET a 123456"), OOM_ERROR)
        self.assertEqual(self.run_command("SET long_key y"), OOM_ERROR)
        self.assertEqual(self.run_command("GET a"), '"xx"')
        self.assertEqual(self.run_command("TTL a"), "(integer) -1")
        self.assertIn("evicted_keys:0", self.run_command("INFO memory"))

    def test_oversize_overwrite_preserves_existing_ttl(self):
        self.run_command("CONFIG SET maxmemory 6")
        self.run_command("SET a xx")
        self.run_command("EXPIRE a 10")
        self.assertEqual(self.run_command("SET a 123456"), OOM_ERROR)
        self.assertEqual(self.run_command("TTL a"), "(integer) 10")

    def test_unlimited_memory_and_zero_limit(self):
        self.run_command("CONFIG SET maxmemory 1")
        self.run_command("CONFIG SET maxmemory 0")
        self.assertEqual(self.run_command("SET a some-long-value"), "OK")
        self.assertIn("maxmemory:0", self.run_command("INFO memory"))

    def test_config_change_does_not_immediately_evict(self):
        self.run_command("SET a xyz")
        self.run_command("CONFIG SET maxmemory 1")
        self.assertEqual(self.run_command("DBSIZE"), "(integer) 1")
        self.assertEqual(self.run_command("SET b q"), OOM_ERROR)
        self.assertEqual(self.run_command("GET a"), '"xyz"')

    def test_expire_ttl_and_expiration_removal(self):
        self.run_command("SET a xx")
        self.assertEqual(self.run_command("TTL a"), "(integer) -1")
        self.assertEqual(self.run_command("EXPIRE a 3"), "(integer) 1")
        self.assertEqual(self.run_command("TTL a"), "(integer) 3")
        self.clock.advance(0.2)
        self.assertEqual(self.run_command("TTL a"), "(integer) 2")
        self.clock.advance(2.8)
        self.assertEqual(self.run_command("GET a"), "(nil)")
        self.assertEqual(self.run_command("TTL a"), "(integer) -2")
        self.assertIn("used_memory:0", self.run_command("INFO memory"))

    def test_database_wide_queries_purge_expired(self):
        self.run_command("SET a x")
        self.run_command("EXPIRE a 1")
        self.clock.advance(1)
        self.assertEqual(self.run_command("DBSIZE"), "(integer) 0")
        self.assertEqual(self.run_command("KEYS"), "(empty array)")

    def test_immediate_expire_and_missing_expire(self):
        self.assertEqual(self.run_command("EXPIRE missing 0"), "(integer) 0")
        self.run_command("SET a x")
        self.assertEqual(self.run_command("EXPIRE a -4"), "(integer) 1")
        self.assertEqual(self.run_command("GET a"), "(nil)")

    def test_expire_reassignment_ignores_stale_heap_event(self):
        self.run_command("SET a x")
        self.run_command("EXPIRE a 2")
        self.run_command("EXPIRE a 8")
        self.clock.advance(2)
        self.assertEqual(self.run_command("GET a"), '"x"')
        self.assertEqual(self.run_command("TTL a"), "(integer) 6")
        self.clock.advance(6)
        self.assertEqual(self.run_command("GET a"), "(nil)")

    def test_delete_reinsert_same_key_ignores_stale_expiration(self):
        self.run_command("SET a old")
        self.run_command("EXPIRE a 2")
        self.run_command("DEL a")
        self.run_command("SET a new")
        self.run_command("EXPIRE a 4")
        self.clock.advance(2)
        self.assertEqual(self.run_command("GET a"), '"new"')
        self.clock.advance(2)
        self.assertEqual(self.run_command("GET a"), "(nil)")

    def test_overwrite_resets_ttl(self):
        self.run_command("SET a old")
        self.run_command("EXPIRE a 2")
        self.run_command("SET a new")
        self.clock.advance(3)
        self.assertEqual(self.run_command("GET a"), '"new"')
        self.assertEqual(self.run_command("TTL a"), "(integer) -1")

    def test_expired_keys_are_not_evictions(self):
        self.run_command("CONFIG SET maxmemory 6")
        self.run_command("SET a xx")
        self.run_command("SET b yy")
        self.run_command("EXPIRE a 1")
        self.clock.advance(1)
        self.run_command("SET c zz")
        self.assertEqual(self.run_command("GET a"), "(nil)")
        self.assertEqual(self.run_command("GET b"), '"yy"')
        self.assertIn("evicted_keys:0", self.run_command("INFO memory"))

    def test_errors_and_malformed_arguments(self):
        self.assertEqual(self.run_command("HELLO"), "(error) ERR unknown command 'HELLO'")
        self.assertEqual(self.run_command("GET"),
                         "(error) ERR wrong number of arguments for 'GET' command")
        self.assertEqual(self.run_command("SET a"),
                         "(error) ERR wrong number of arguments for 'SET' command")
        self.assertEqual(self.run_command("KEYS *"),
                         "(error) ERR wrong number of arguments for 'KEYS' command")
        self.assertEqual(self.run_command("CONFIG SET maxmemory abc"), INTEGER_ERROR)
        self.assertEqual(self.run_command("CONFIG SET maxmemory -1"), INTEGER_ERROR)
        self.assertEqual(self.run_command("EXPIRE a x"), INTEGER_ERROR)
        self.assertEqual(self.run_command('SET a "unterminated'),
                         "(error) ERR invalid quoting")
        self.assertEqual(self.run_command(""), "")

    def test_eviction_before_expiration_does_not_delete_replacement(self):
        self.run_command("CONFIG SET maxmemory 6")
        self.run_command("SET a xx")
        self.run_command("EXPIRE a 5")
        self.run_command("SET b yy")
        self.run_command("SET c zz")  # a 제거
        self.run_command("DEL b")
        self.run_command("SET a q")
        self.run_command("EXPIRE a 9")
        self.clock.advance(5)
        self.assertEqual(self.run_command("GET a"), '"q"')
        self.clock.advance(4)
        self.assertEqual(self.run_command("GET a"), "(nil)")


class CliTests(unittest.TestCase):
    def test_repl_with_quit(self):
        main_file = os.path.join(os.path.dirname(__file__), "..", "main.py")
        output = subprocess.run(
            [sys.executable, main_file],
            input='SET a "Alice Kim"\nGET a\nEXISTS a\nquit\n',
            text=True, capture_output=True, check=True, timeout=5
        )
        self.assertIn("mini-redis> ", output.stdout)
        self.assertIn('"Alice Kim"', output.stdout)
        self.assertIn("(integer) 1", output.stdout)
        self.assertEqual(output.stderr, "")

    def test_repl_exits_on_eof(self):
        main_file = os.path.join(os.path.dirname(__file__), "..", "main.py")
        output = subprocess.run(
            [sys.executable, main_file], input="SET a x\n", text=True,
            capture_output=True, check=True, timeout=5
        )
        self.assertIn("OK", output.stdout)
        self.assertEqual(output.stderr, "")


if __name__ == "__main__":
    unittest.main()
