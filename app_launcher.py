import sys


def self_check() -> int:
    import tkinter  # noqa: F401
    import requests  # noqa: F401
    import bs4  # noqa: F401
    import lxml  # noqa: F401
    import playwright  # noqa: F401

    return 0


if __name__ == "__main__":
    if "--self-check" in sys.argv:
        raise SystemExit(self_check())

    from src.app import main

    main()
