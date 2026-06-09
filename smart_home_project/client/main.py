"""GUI client entry point."""

from __future__ import annotations

import os
import subprocess
import sys
import tkinter as tk
from pathlib import Path

from smart_home_project.client.gui import ClientGUI


def launch_detached_for_pycharm() -> bool:
    """Open the GUI as a detached process when PyCharm runs this file.

    PyCharm normally keeps a run configuration "busy" while the Tkinter window
    is open. Detaching lets the green Run button open another client window
    every time it is clicked.
    """
    if os.environ.get("PYCHARM_HOSTED") != "1":
        return False
    if "--attached" in sys.argv:
        return False

    env = os.environ.copy()
    env.pop("PYCHARM_HOSTED", None)
    python_executable = Path(sys.executable)
    project_root = Path(__file__).resolve().parents[2]
    launcher_log = Path(__file__).resolve().parents[2] / "smart_home_client_launcher.log"
    creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    try:
        with launcher_log.open("a", encoding="utf-8") as log_file:
            subprocess.Popen(
                [str(python_executable), "-m", "smart_home_project.client.main", "--attached"],
                cwd=str(project_root),
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=log_file,
                stderr=log_file,
                creationflags=creationflags,
            )
    except Exception as exc:
        launcher_log.write_text(f"Unable to launch detached client: {exc}\n", encoding="utf-8")
        return False

    print("Client window launched. You can press Run again to open another one.")
    return True


def main() -> None:
    if launch_detached_for_pycharm():
        return

    root = tk.Tk()
    root.geometry("850x500")
    ClientGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
    