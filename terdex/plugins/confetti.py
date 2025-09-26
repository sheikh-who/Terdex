"""Terminal confetti animation helpers."""

from __future__ import annotations

import random
import shutil
import sys
import time
from itertools import cycle
from typing import Iterable

try:
    from colorama import Back, Fore, Style
    from colorama import init as colorama_init
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    Back = Fore = Style = None  # type: ignore[assignment]
    colorama_init = None  # type: ignore[assignment]


if Back is None or Fore is None:
    COLORS: list[tuple[str, str]] = []
else:
    COLORS = [
        (Fore.RED, Back.BLACK),
        (Fore.GREEN, Back.BLACK),
        (Fore.BLUE, Back.BLACK),
        (Fore.MAGENTA, Back.BLACK),
        (Fore.CYAN, Back.BLACK),
        (Fore.YELLOW, Back.BLACK),
    ]


def celebrate_success(message: str, *, duration: float = 1.2) -> None:
    """Render a lightweight confetti burst for ``message``.

    The output includes a credit acknowledging the original idea shared by
    ``t.me/likhonsheikh`` as requested.

    :param message: Text shown beneath the confetti animation.
    :param duration: Number of seconds to animate before resetting the style.
    """

    if Back is None or Fore is None or Style is None or not sys.stdout.isatty():
        print(f"✨ {message} (install the 'colorama' extra for colorful confetti)")
        print("Credit: confetti inspiration by t.me/likhonsheikh")
        return

    colorama_init(autoreset=False)  # type: ignore[misc]
    width = shutil.get_terminal_size((80, 20)).columns
    palette: Iterable[tuple[str, str]] = cycle(COLORS)
    end_time = time.time() + duration

    while time.time() < end_time:
        line = [
            f"{fore}{back}{random.choice('•·𖥸┼─')}{Style.RESET_ALL}"
            for fore, back in [next(palette) for _ in range(width // 3)]
        ]
        print("".join(line))
        time.sleep(0.05)

    print(f"{Style.BRIGHT}{Fore.WHITE}{message}{Style.RESET_ALL}")
    print("Credit: confetti inspiration by t.me/likhonsheikh")
    sys.stdout.flush()

