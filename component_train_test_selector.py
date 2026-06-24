from __future__ import annotations

from pathlib import Path
from tkinter import messagebox

from component_selector.app import ComponentSelectorApp


def main() -> None:
    project_root = Path(__file__).resolve().parent
    try:
        app = ComponentSelectorApp(project_root=project_root)
    except FileNotFoundError as error:
        messagebox.showerror("Catalog not found", str(error))
        return

    app.mainloop()


if __name__ == "__main__":
    main()
