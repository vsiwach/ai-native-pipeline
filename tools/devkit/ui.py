"""Terminal output helpers. No deps, degrades to plain text when not a TTY."""

import os
import sys

_COLOR = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def _wrap(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _COLOR else text


def green(text: str) -> str:
    return _wrap("32", text)


def red(text: str) -> str:
    return _wrap("31", text)


def yellow(text: str) -> str:
    return _wrap("33", text)


def dim(text: str) -> str:
    return _wrap("2", text)


def bold(text: str) -> str:
    return _wrap("1", text)


def ok(msg: str) -> None:
    print(f"  {green('✓')} {msg}")


def fail(msg: str) -> None:
    print(f"  {red('✗')} {msg}")


def warn(msg: str) -> None:
    print(f"  {yellow('!')} {msg}")


def info(msg: str) -> None:
    print(f"  {dim('·')} {msg}")


def heading(msg: str) -> None:
    print(f"\n{bold(msg)}")
