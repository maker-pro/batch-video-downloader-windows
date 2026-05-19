from __future__ import annotations

import importlib
import sys


REQUIRED_MODULES = [
    "requests",
    "bs4",
    "lxml",
    "playwright",
    "tkinter",
]


def main() -> int:
    missing: list[str] = []
    for module_name in REQUIRED_MODULES:
        try:
            importlib.import_module(module_name)
        except Exception:
            missing.append(module_name)

    if missing:
        print("Missing modules: " + ", ".join(missing))
        return 1

    print("Runtime check passed: " + sys.executable)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
