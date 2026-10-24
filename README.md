# B5-1 · Mini Redis

Python 기본 기능만으로 구현한 **CLI 기반 In-Memory Key-Value 저장소**입니다. Redis 라이브러리를 사용하지 않고 **해시맵(체이닝), 이중 연결 리스트, 최소 힙**을 직접 구현해 `SET`/`GET`, **LRU 자동 제거**, **TTL 만료**를 연결합니다.

## 실행

- 요구 환경: **Python 3.8 이상**
- 추가 설치: **없음** (표준 라이브러리만 사용)

```bash
python main.py
```

```text
mini-redis> CONFIG SET maxmemory 6
OK
mini-redis> SET a 11
OK
mini-redis> SET b 22
OK
mini-redis> GET a
"11"
mini-redis> SET c 33
OK
mini-redis> GET b
(nil)
mini-redis> INFO memory
used_memory:6
maxmemory:6
evicted_keys:1
mini-redis> quit
```

명령어는 대소문자를 구분하지 않습니다. 키/값은 문자열이며, `SET name "Alice Kim"`처럼 **공백이 있는 값은 따옴표로 입력**합니다. `quit`, `exit` 또는 Ctrl+D로 종료할 수 있습니다.

## 지원 명령어

| 명령어 | 결과 / 설명 |
| --- | --- |
| `SET key value` | 저장 또는 덮어쓰기: `OK` |
| `GET key` | 값 조회: `"value"` 또는 `(nil)` |
| `DEL key` | 삭제: `(integer) 1` / `0` |
| `EXISTS key` | 존재 확인: `(integer) 1` / `0` |
| `DBSIZE` | 살아 있는 키 개수: `(integer) N` |
| `KEYS` | 전체 키 목록 (순서 보장 없음, 패턴 미지원) |
| `CONFIG SET maxmemory bytes` | 메모리 제한 설정 (`0`은 무제한) |
| `INFO memory` | `used_memory`, `maxmemory`, `evicted_keys` |
| `EXPIRE key seconds` | TTL 설정: `(integer) 1` / `0` |
| `TTL key` | 남은 초, 미설정 `-1`, 없는 키 `-2` |

모든 키/값의 크기는 **UTF-8 바이트**로 계산하고, 자료구조 오버헤드는 제외합니다. 메모리 한도 초과는 `SET` 시 LRU 순서대로 제거하며, **단일 키+값이 한도보다 크면 OOM 오류를 내고 이전 데이터는 그대로 유지**합니다. 제한을 낮추는 `CONFIG SET` 자체에서는 제거하지 않습니다. TTL은 만료 시점을 최소 힙에서 확인해 다음 명령 실행 전에 정리합니다.

## 파일 구성

```text
main.py                CLI 입력/출력, 종료
mini_redis.py          명령 처리, 메모리 계산, LRU와 TTL 연결
hash_map.py            해시 함수, 충돌 체이닝, 버킷 2배 확장
linked_list.py         prev/next 노드 기반 이중 연결 리스트
min_heap.py            push/pop/peek, 상향·하향 힙 복구
tests/test_mini_redis.py  자료구조·명령어·실제 CLI 테스트
docs/IMPLEMENTATION.md   시작부터 종료까지 실행 흐름과 주요 설계
docs/CONCEPTS.md         Python 기초부터 해시맵·LRU·TTL의 동작 원리
docs/REVIEW.md           설명 연습용 핵심 질문/답변/코드 위치
```

## 검증

```bash
python -m unittest discover -s tests -v
```

외부 테스트 도구 없이 자료구조, 해시 충돌·리해싱, 10개 명령어, LRU 순서, UTF-8 메모리, OOM 원자성, TTL 재설정/삭제/만료, 오류 입력, CLI 종료를 확인합니다. TTL 테스트는 실제 대기 대신 **가짜 시계**를 사용합니다.

## 권장 학습 순서

1. [핵심 개념](docs/CONCEPTS.md): `self`, 참조, 배열, 해시, 연결 리스트, 힙을 먼저 파악
2. [구현 해설](docs/IMPLEMENTATION.md): `main.py`에서 시작해 `SET` → `GET` → `EXPIRE` 순으로 추적
3. [예상 질문](docs/REVIEW.md): 답을 가리고 설명한 다음 관련 코드로 검증
4. `python main.py` 및 테스트를 실행하여 **코드와 실제 상태 변화**를 대조

### 범위 및 제약

내장 `dict`, `set`, `collections`로 해시맵을 대체하지 않았습니다. Python 리스트는 **버킷 배열/힙 배열** 용도로만 사용합니다. 네트워크, 파일 저장, 멀티스레딩, Redis 복합 자료형 및 보너스 기능은 구현하지 않습니다.
