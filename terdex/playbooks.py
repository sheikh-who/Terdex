"""Playbook execution helpers for Terdex."""

from __future__ import annotations

import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Iterable, List, Optional, Sequence


def execute_playbook(
    commands: Iterable[str],
    *,
    shell: bool = True,
    parallel: bool = False,
    max_workers: Optional[int] = None,
) -> int:
    """Execute the provided shell ``commands``.

    The function defaults to sequential execution for backwards compatibility but
    can process commands in parallel when ``parallel`` is ``True``. Parallel mode
    improves throughput for independent commands such as package downloads or
    formatting jobs.

    :param commands: Commands to execute.
    :param shell: Whether to execute through the system shell.
    :param parallel: Enable threaded execution across commands.
    :param max_workers: Optional limit for the thread pool size in parallel mode.
    :return: Exit code from the execution (``0`` on success).
    """

    command_list: Sequence[str] = list(commands)
    if not command_list:
        return 0

    if not parallel:
        for command in command_list:
            print(f"$ {command}")
            completed = subprocess.run(command, shell=shell, check=False)
            if completed.returncode != 0:
                print(f"Command failed with exit code {completed.returncode}")
                return completed.returncode
        return 0

    results: List[int] = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_run_command, command, shell): command
            for command in command_list
        }
        for future in as_completed(futures):
            command = futures[future]
            return_code = future.result()
            results.append(return_code)
            status = "succeeded" if return_code == 0 else f"failed ({return_code})"
            print(f"[parallel] {command} -> {status}")

    for return_code in results:
        if return_code != 0:
            return return_code
    return 0


def _run_command(command: str, shell: bool) -> int:
    completed = subprocess.run(command, shell=shell, check=False)
    if completed.returncode != 0:
        print(f"Command failed with exit code {completed.returncode}")
    return completed.returncode

