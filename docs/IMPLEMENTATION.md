# 구현 해설: 입력부터 출력까지

**목표:** 소스 코드를 보고 각 명령 실행 시 어떤 자료구조가 어떻게 바뀌는지 설명합니다. 중요한 코드 위치는 `파일명 · 클래스/메서드`로 표시합니다.

## 1. 실행 구조

```text
사용자: SET a 123
       │
       ▼
main.py · main()                 입력과 종료 제어
       │ redis.execute(line)
       ▼
mini_redis.py · execute()        TTL 정리 → 토큰 분리 → 인자 검사 → 명령 분기
       │
       ├─ HashMap       key → _Value(value, lru_node, expires_at, version)
       ├─ DoublyLinkedList     최근 사용 키가 앞, 오래된 키가 뒤
       └─ MinHeap       만료 시간이 빠른 예약이 맨 위
       │
       ▼
"OK" → main()의 print() → 화면
```

`main.py`의 `if __name__ == "__main__"`은 파일을 직접 실행했을 때만 `main()`을 시작합니다. `input("mini-redis> ")`은 입력받을 때까지 기다리는 **REPL(Read–Eval–Print Loop)**입니다. `quit`/`exit`은 루프를 중단하며 EOF/Ctrl+C도 종료합니다.

`MiniRedis` 인스턴스는 프로그램 시작 시 **한 번** 만들어집니다. 따라서 명령을 여러 번 입력해도 저장 데이터가 유지되고, 프로그램을 종료하면 메모리 데이터는 사라집니다.

## 2. 시작할 때 만드는 상태

`mini_redis.py · MiniRedis.__init__()`:

- `self._data = HashMap()`: 키로 `_Value` 객체를 찾는 본 저장소
- `self._lru = DoublyLinkedList()`: 키를 **최근 사용 순서**로 관리. 앞 = 최신, 뒤 = 가장 오래됨
- `self._expirations = MinHeap()`: `(만료시각, 버전, 키)` 예약을 정렬
- `self._used_memory`: 실제로 살아 있는 키/값 UTF-8 바이트 합
- `self._maxmemory`: 0은 무제한
- `self._evicted_keys`: LRU 정책으로 제거한 횟수 (TTL 삭제는 포함하지 않음)
- `self._next_expire_version`: 이전 예약과 새로운 예약을 구별하는 증가 번호

해시맵 안의 `_Value`는 `value`, `node`, `expires_at`, `expire_version`을 갖습니다. **키 하나의 저장 값과 LRU 노드 참조를 같은 객체에 넣기 때문에** 해시맵 조회 직후 연결 리스트의 해당 노드를 바로 찾아 이동시킬 수 있습니다.

## 3. 모든 명령이 시작되는 공통 경로

`mini_redis.py · MiniRedis.execute(line)`:

1. `_purge_expired()`: 현재 시간 이전의 TTL 예약을 힙에서 꺼내 확인하고, 실제로 만료된 키만 삭제합니다.
2. `shlex.split(line)`: 공백 기준으로 토큰을 나누되 `"Alice Kim"`은 **하나의 값**으로 취급합니다. 닫히지 않은 따옴표는 오류로 처리합니다.
3. 명령을 대문자로 표준화하고 정해진 인자 수를 확인합니다.
4. 해당 명령의 함수를 실행합니다. 모르는 명령/잘못된 정수는 표준 오류 문자열을 반환합니다.
5. `main.py`가 반환 문자열을 출력합니다. 빈 명령은 출력하지 않습니다.

인수 파싱에는 `shlex` 표준 라이브러리를 쓰며, 데이터를 보관하기 위해 `dict`를 사용하지 않습니다.

## 4. `SET`: 저장 → LRU 갱신 → 메모리 초과 처리

`mini_redis.py · _set(key, value)`:

1. `_entry_bytes()`가 `len(key.encode("utf-8")) + len(value.encode("utf-8"))`를 계산합니다.
2. **한 항목만으로 제한을 초과하면 먼저 OOM 반환.** 새 항목도 저장하지 않고, 기존 키의 값/TTL도 변경하지 않습니다.
3. 새 키: 연결 리스트 맨 앞에 키 노드 생성 → `_Value`에 노드를 연결 → 해시맵 저장 → 메모리 증가.
4. 기존 키: 변경 전/후 크기의 차이만 메모리에 더함 → 값 교체 → 기존 TTL 해제 → 해당 LRU 노드를 앞으로 이동.
5. 제한이 있고 초과한 경우 리스트 맨 뒤 키를 `_delete(..., evicted=True)`로 제거합니다. 한도 이하가 될 때까지 반복합니다.
6. `OK` 반환.

예: 제한 6바이트, 모든 키 1바이트, 모든 값 2바이트.

```text
SET a 11         LRU: [a]        used=3
SET b 22         LRU: [b, a]     used=6
GET a            LRU: [a, b]     used=6
SET c 33         LRU: [c, a, b]  used=9
                b 삭제 (최하위 LRU)
결과              LRU: [c, a]     used=6, evicted_keys=1
```

**왜 맨 뒤를 삭제하는가?** 성공한 `SET`/`GET`마다 해당 키를 맨 앞으로 이동시키므로, 뒤에 남아 있는 키는 가장 오래 접근하지 않은 키입니다.

`CONFIG SET maxmemory N`은 한도 값만 바꿉니다. 명시된 제거 규칙에 맞춰 **다음 성공한 `SET`에서** 초과 시 LRU 제거를 수행하며, `CONFIG` 자체로 즉시 제거하지 않습니다.

## 5. `GET`, `EXISTS`, `DEL`, `DBSIZE`, `KEYS`

| 명령 | `execute()`에서의 실제 처리 | LRU 변경 |
| --- | --- | --- |
| `GET` | `_data.get(key)` → 없으면 `(nil)`, 있으면 JSON식 큰따옴표 출력 | **성공한 조회만** `move_to_front()` |
| `EXISTS` | `_data.contains(key)` | 없음 |
| `DEL` | `_delete(key)` → 해시맵/리스트/메모리 정리 | 삭제할 때 노드 제거 |
| `DBSIZE` | `_data.size()` | 없음 |
| `KEYS` | `_data.keys()` 순회 후 `1. "key"` 형태로 출력 | 없음 |

키는 처리 전에 `_purge_expired()`가 정리하므로 만료된 키는 조회되지 않습니다. 큰따옴표 출력 시 `json.dumps(..., ensure_ascii=False)`를 쓰며, 따옴표·백슬래시 등의 문자가 안전하게 표시됩니다.

`_delete()`에서 데이터를 지울 때 `used_memory`도 반드시 감소시킵니다. 이 경로를 **명령 삭제/TTL 만료/LRU 제거가 공유**하므로 메모리 갱신을 빠뜨릴 위험이 줄어듭니다. TTL 예약은 힙에 남더라도 유효하지 않은 예약으로 처리됩니다(7절).

## 6. 자료구조 내부 구현

### 해시맵: `hash_map.py · HashMap`

- `_buckets = [None] * 8`: 고정 개수의 버킷(시작 시 8개)을 **배열**로 보관합니다.
- `_index(key, capacity)`: UTF-8 각 바이트마다 `(index * 31 + byte) % capacity`를 계산하여 버킷 인덱스를 결정합니다.
- 같은 인덱스에서 충돌하면 `_Entry(key, value, next)`를 연결합니다(**체이닝**).
- `put/get/contains/remove`: 해당 버킷 체인의 키를 직접 비교합니다.
- `_resize()`: `size * 4 > capacity * 3`이면 2배 배열에 **기존 엔트리를 재해싱**합니다.

해시 함수가 서로 다른 키를 같은 버킷에 넣더라도 키 비교를 수행하기 때문에 데이터가 섞이지 않습니다. 키가 고르게 분포할 때 평균 조회는 O(1)이며, 모든 키가 한 버킷에 몰리면 O(n)입니다. 키 문자열 길이와 리해싱 비용은 별도로 고려합니다.

### 이중 연결 리스트: `linked_list.py · DoublyLinkedList`

```text
head(가상) ⇄ [최근 사용] ⇄ [덜 최근] ⇄ [가장 오래됨] ⇄ tail(가상)
```

`Node`는 `prev`, `next`, `data`를 가집니다. `head`와 `tail`은 **가상 노드**(센티넬)라 실제 키가 아니며 빈 리스트에서 예외 처리를 단순화합니다. `_attach()`는 양쪽 포인터 4개를 연결하고 `_detach()`는 이웃 포인터를 다시 잇습니다. 이미 위치를 아는 노드의 `remove_node`/`move_to_front`는 탐색 없이 O(1)입니다. `insert_front/back`, `remove_front/back`도 O(1)입니다.

### 최소 힙: `min_heap.py · MinHeap`

항목들은 Python 리스트의 인덱스에 저장됩니다. 부모 인덱스는 `(i-1)//2`, 자식은 `2*i+1`, `2*i+2`입니다.

- `push`: 맨 끝에 추가하고 `_heapify_up`으로 부모보다 작으면 교환
- `peek`: 가장 빠른 만료 항목(루트)을 **제거하지 않고** 반환
- `pop`: 루트를 반환하고 마지막 항목을 루트로 이동한 후 `_heapify_down`

리스트는 **배열 표현**만 담당하고, 힙 정렬 동작은 직접 구현합니다. `push/pop`은 O(log n), `peek`은 O(1)입니다.

## 7. `EXPIRE`와 `TTL`: 만료 예약 관리

`mini_redis.py · _expire / _ttl / _purge_expired`:

1. `EXPIRE a 3`이면 `_clock()`의 현재값에 3초를 더해 `expires_at`을 저장합니다.
2. 고유한 `expire_version`을 발급하고 힙에 `(expires_at, version, "a")`를 추가합니다.
3. 후속 명령이 시작되면 `_purge_expired()`가 현재 시각보다 빠른 예약부터 `pop`합니다.
4. 예약의 **만료시각과 버전이 현재 해시맵 레코드와 모두 같을 때만** `_delete()`를 호출합니다.

**왜 버전이 필요한가?** `EXPIRE a 2` 후 `EXPIRE a 10`을 설정하면 힙에 이전 예약도 남습니다. 이전 예약은 버전이 다르므로 삭제하지 않습니다. `DEL a` 후 `SET a ...`으로 같은 키를 다시 만들더라도 전역 증가 버전이 새로운 예약을 구별합니다. 이를 **lazy deletion(지연 삭제)**이라고 합니다. DEL/덮어쓰기로 TTL은 즉시 논리적으로 무효화되고, 힙의 무효 예약은 만료 시각에 루트에 도달할 때 물리적으로 제거합니다.

`TTL key`의 반환:

- 존재하지 않거나 이미 만료: `-2`
- 존재하지만 TTL 없음: `-1`
- 살아 있는 TTL: `int(expires_at - now)` (남은 초를 정수로 내림; 1초 미만 남아 있으면 `0` 가능)

`time.monotonic()`을 기본 시계로 사용하므로 운영체제의 달력 시계 조정에 TTL이 흔들리지 않습니다. 테스트는 `MiniRedis(clock=FakeClock())`을 전달해 실제로 기다리지 않고 만료를 검증합니다.

## 8. 종료 및 제약 확인

- `main.py`에서 `quit`/`exit`/EOF/Ctrl+C를 만나면 REPL 종료.
- 프로그램이 살아 있는 동안에만 메모리에 저장하며 종료 시 별도 파일을 쓰지 않음.
- 금지된 `dict`, `set`, `collections`를 자료 저장에 사용하지 않음.
- 힙의 지연 삭제 예약은 `used_memory` 계산에 포함하지 않음. 미션의 계산식은 키/값의 UTF-8 바이트만 셈.

테스트에서 각 상태 전이를 확인하려면 [`tests/test_mini_redis.py`](../tests/test_mini_redis.py)를 참고합니다.
