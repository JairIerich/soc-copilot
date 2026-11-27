"""Carrega o runtime C++ instalado por pip, sem alterar o Windows globalmente."""

import ctypes
import os
import sys
from pathlib import Path
from typing import Any

_handles: list[Any] = []


def prepare_runtime() -> None:
    if sys.platform != "win32" or _handles:
        return
    directory = Path(sys.prefix) / "Scripts"
    library = directory / "msvcp140.dll"
    if library.is_file():
        _handles.append(os.add_dll_directory(str(directory)))
        _handles.append(ctypes.WinDLL(str(library)))
