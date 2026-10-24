# 코드 설명 연습: 예상 질문과 핵심 답변

**사용법:** 질문만 보고 30~60초 설명한 다음 **코드 위치**를 열어 메서드 호출과 상태 변화를 확인합니다. 정의만 외우기보다 실제 필드와 분기 근거를 설명합니다.

| 질문 | 답변의 핵심 논리 | 코드 위치 |
| --- | --- | --- |
| 1. 프로그램 시작과 종료는? | `main`이 `MiniRedis` 인스턴스 하나를 만들고 REPL로 입력을 반복한다. `quit`/`exit`/EOF/Ctrl+C면 종료하며 저장 파일은 없다. | `main.py · main` |
| 2. `SET a "Alice Kim"` 입력은? | `shlex.split`이 따옴표 내부 공백을 하나의 값으로 다룬다. `execute`에서 인자 수 검증, `_set` 호출, `OK` 반환을 수행한다. | `mini_redis.py · execute/_set` |
| 3. 내장 해시맵 없이 키를 저장하는 방법은? | 버킷 배열의 인덱스를 UTF-8 바이트로 직접 계산한 후 `_Entry` 체인에 저장한다. | `hash_map.py · _index/put` |
| 4. `a`, `i`의 충돌은? | 8개 버킷에서 모두 인덱스 1이다. 같은 버킷에 각각의 엔트리를 연결하고 키 문자열을 비교해 찾는다. | `hash_map.py · _Entry/get` |
| 5. 로드 팩터 0.75의 처리는? | `size * 4 > capacity * 3`일 때 버킷 개수를 두 배로 늘리고 모든 키의 인덱스를 재계산한다. | `hash_map.py · put/_resize` |
| 6. 해시 조회는 항상 O(1)인가? | 아니다. 평균적으로 체인이 짧으면 O(1)이지만 최악의 충돌은 O(n)이다. 키 길이 O(k), 재해싱 O(n)도 고려한다. | `hash_map.py · _index/get/_resize` |
| 7. 이중 연결 리스트 노드의 필드는? | `data`, 이전 `prev`, 다음 `next`를 가지므로 노드 위치를 알고 있으면 이웃 참조를 고쳐 O(1)에 이동·삭제한다. | `linked_list.py · Node/_detach/_attach` |
| 8. 가상 노드는 왜 쓰는가? | 머리/꼬리 경계를 일정하게 유지하여 빈 리스트의 삽입·삭제를 같은 포인터 연결 로직으로 처리한다. | `linked_list.py · __init__` |
| 9. LRU가 제거하는 키의 결정은? | 성공한 `SET`/`GET`이 노드를 앞으로 옮기므로 리스트의 마지막 데이터 노드가 가장 오래된 키다. | `mini_redis.py · _set/_get` |
| 10. 해시맵+리스트의 O(1) LRU 원리는? | 해시맵 값에 노드 참조를 저장해 평균 O(1) 조회 후 검색 없이 O(1)에 그 노드를 앞으로 이동한다. | `mini_redis.py · _Value/_get`; `linked_list.py · move_to_front` |
| 11. `used_memory` 계산은? | 키와 값 UTF-8 바이트의 합만 포함한다. 버킷·노드·포인터·힙 오버헤드는 제외한다. | `mini_redis.py · _entry_bytes/_delete` |
| 12. `SET` 시 제한을 초과하면? | 성공적으로 저장된 항목을 최신으로 만든 뒤 제한 이하까지 오래된 키를 반복 삭제하고 `evicted_keys`를 증가시킨다. | `mini_redis.py · _set` |
| 13. 기존 값을 너무 큰 값으로 덮어쓰면? | 단일 엔트리 크기를 먼저 검사해 OOM이면 기존 값, TTL, LRU 상태를 수정하지 않는다. | `mini_redis.py · _set` |
| 14. TTL 삭제도 `evicted_keys`에 더하는가? | 아니다. `_delete(evicted=True)`는 LRU 정책일 때만 호출하므로 TTL 만료·사용자 삭제는 제외한다. | `mini_redis.py · _delete/_purge_expired` |
| 15. 만료 시간에 힙이 적합한 이유는? | 최소 만료시각이 루트여서 `peek` O(1)로 확인하고 새 예약 삽입·제거는 O(log h)이다. | `min_heap.py · push/peek/pop` |
| 16. 힙을 배열로 표현하는 방법은? | 부모 `(i-1)//2`, 자식 `2*i+1`, `2*i+2` 인덱스를 계산하고 부모와 자식 교환으로 최소 힙 속성을 유지한다. | `min_heap.py · _heapify_up/_heapify_down` |
| 17. `EXPIRE a 3`의 실행 흐름은? | 현재 단조 시계+3을 계산해 레코드와 힙에 시각·버전을 저장한다. 후속 명령 시 도래한 예약을 검사해 삭제한다. | `mini_redis.py · _expire/_purge_expired/execute` |
| 18. TTL을 재설정해도 안전한 이유는? | 힙 예약의 시각·버전이 현재 해시맵 레코드와 모두 일치할 때만 삭제한다. 지연 삭제로 이전 예약을 무시한다. | `mini_redis.py · _expire/_purge_expired` |
| 19. TTL이 있는 키를 `SET`으로 덮어쓰면? | 성공한 갱신은 `expires_at`/`expire_version`을 `None`으로 초기화하여 기존 예약을 무효화한다. | `mini_redis.py · _set` |
| 20. `TTL`에서 `-1`, `-2`, `0`의 의미는? | `-1`: 키는 있으나 TTL 없음, `-2`: 키 없음/만료, `0`: 살아 있지만 남은 시간이 1초 미만이라 정수 변환된 상태. | `mini_redis.py · _ttl` |
| 21. 삭제할 때 자료구조의 일관성은? | 명령 삭제·TTL 만료·LRU 제거가 같은 `_delete` 경로를 거쳐 해시맵/리스트/메모리를 함께 갱신한다. | `mini_redis.py · _delete` |
| 22. 테스트에서는 무엇을 확인하나? | 충돌·확장, 포인터 이동, 힙 우선순위, LRU 제거 순서, UTF-8 바이트, OOM 보존, TTL 재설정·재삽입, CLI 종료 등. | `tests/test_mini_redis.py` |

## 설명 연습 1: LRU의 상태 변화

```text
CONFIG SET maxmemory 6
SET a 11     → LRU [a],    used=3
SET b 22     → LRU [b,a],  used=6
GET a        → LRU [a,b],  used=6
SET c 33     → [c,a,b]에서 b 제거 → [c,a], used=6, evicted_keys=1
GET b        → (nil)
```

왜 `b`가 지워졌는지, `GET a`를 생략하면 어떤 결과가 되는지, 왜 `used_memory`가 6인지 직접 설명합니다.

## 설명 연습 2: TTL 버전

```text
SET a old
EXPIRE a 2    → heap: (102, v1, a)
EXPIRE a 8    → heap: (102, v1, a), (108, v2, a)
시각 102       → v1 예약은 현재 레코드 v2와 달라 무시
GET a         → "old"
시각 108       → v2가 일치해 a 삭제
GET a         → (nil)
```

이 예시의 초기 시각 100은 테스트에 사용한 `FakeClock`의 값입니다. 실제 CLI에서는 `time.monotonic()`을 사용합니다. 대응 테스트는 `test_expire_reassignment_ignores_stale_heap_event`입니다.

## 설명 연습 3: 오류 입력

| 입력 | 이유 및 예상 결과 |
| --- | --- |
| `GET` | 인자 부족 → `(error) ERR wrong number of arguments for 'GET' command` |
| `HELLO` | 미지원 → `(error) ERR unknown command 'HELLO'` |
| `CONFIG SET maxmemory abc` | 정수 아님 → `(error) ERR value is not an integer or out of range` |
| `CONFIG SET maxmemory -1` | 음수 불허 → 동일한 정수 오류 |
| `EXPIRE missing 5` | 키 없음 → `(integer) 0` |
| `SET a "unterminated` | 따옴표 오류 → `(error) ERR invalid quoting` |

`python -m unittest discover -s tests -v`로 확인한 후, 테스트의 입력과 상태 변화를 실제 프로그램에서 재현할 수 있습니다.
