"""Mini Redis CLI 진입점: python main.py"""

from mini_redis import MiniRedis


def main():
    redis = MiniRedis()
    while True:
        try:
            line = input("mini-redis> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if line.strip().lower() in ("exit", "quit"):
            break
        result = redis.execute(line)
        if result:
            print(result)


if __name__ == "__main__":
    main()
