"""Windows native folder picker via tkinter (runs on main thread in worker)."""

import threading


def pick_folder_dialog() -> str | None:
    result: list[str | None] = [None]
    done = threading.Event()

    def run():
        try:
            import tkinter as tk
            from tkinter import filedialog

            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            path = filedialog.askdirectory(title="选择扫描文件夹")
            root.destroy()
            if path:
                result[0] = path
        except Exception:
            result[0] = None
        finally:
            done.set()

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    done.wait(timeout=120)
    return result[0]
