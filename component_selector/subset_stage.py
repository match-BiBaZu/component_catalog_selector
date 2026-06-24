from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from .metadata import CATEGORY_METADATA, CATEGORY_ORDER, category_sort_key
from .models import Component, SelectionCriteria
from .widgets import ScrollableFrame


class SubsetStageMixin:
    def _build_subset_stage(self) -> None:
        self._clear_main_frame()
        self.category_vars = {}

        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1)
        self.main_frame.grid_rowconfigure(2, weight=0)
        self.main_frame.grid_rowconfigure(3, weight=0)
        self.main_frame.grid_rowconfigure(4, weight=0)

        header = ttk.Frame(self.main_frame)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        header.grid_columnconfigure(0, weight=1)

        ttk.Label(header, text="Stage 1: Catalog subset", font=("", 16, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(header, text=self._catalog_status_text()).grid(row=1, column=0, sticky="w", pady=(4, 0))

        button_bar = ttk.Frame(header)
        button_bar.grid(row=0, column=1, rowspan=2, sticky="e")
        ttk.Button(button_bar, text="Select all", command=lambda: self._set_all_subset_values(True)).grid(
            row=0,
            column=0,
            padx=(0, 8),
        )
        ttk.Button(button_bar, text="Clear", command=lambda: self._set_all_subset_values(False)).grid(row=0, column=1)

        scrollable = ScrollableFrame(self.main_frame)
        scrollable.grid(row=1, column=0, sticky="nsew")
        scrollable.content.grid_columnconfigure(0, weight=1)
        scrollable.content.grid_columnconfigure(1, weight=1)

        values_by_category = self.catalog.values_by_category()
        for index, category in enumerate(CATEGORY_ORDER):
            category_frame = ttk.LabelFrame(scrollable.content, text=CATEGORY_METADATA[category].title, padding=10)
            category_frame.grid(
                row=index // 2,
                column=index % 2,
                sticky="nsew",
                padx=(0 if index % 2 == 0 else 8, 0 if index % 2 == 1 else 8),
                pady=8,
            )
            category_frame.grid_columnconfigure(0, weight=1)
            self._build_subset_category(category_frame, category, values_by_category[category])

        footer = ttk.Frame(self.main_frame)
        footer.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        footer.grid_columnconfigure(0, weight=1)
        ttk.Label(footer, textvariable=self.selected_count_var).grid(row=0, column=0, sticky="w")
        ttk.Button(footer, text="Confirm subset", command=self._confirm_subset).grid(row=0, column=1, sticky="e")
        self._update_selected_count()

    def _build_subset_category(self, frame: ttk.LabelFrame, category: str, values: set[str]) -> None:
        self.category_vars[category] = {}
        sorted_values = sorted(values, key=lambda code: category_sort_key(category, code))
        for row_index, code in enumerate(sorted_values):
            var = tk.BooleanVar(value=True)
            self.category_vars[category][code] = var
            ttk.Checkbutton(
                frame,
                text=self._checkbox_label(category, code, self.catalog.components),
                variable=var,
                command=self._update_selected_count,
            ).grid(row=row_index, column=0, sticky="w", pady=2)

    def _catalog_status_text(self) -> str:
        text = f"Loaded {len(self.catalog.components)} STEP files from {self.catalog_dir.name}"
        if self.catalog.ignored_non_step_files:
            ignored_names = ", ".join(path.name for path in self.catalog.ignored_non_step_files)
            text += f"; ignored non-STEP files: {ignored_names}"
        if self.catalog.ignored_unparsed_step_files:
            ignored_names = ", ".join(path.name for path in self.catalog.ignored_unparsed_step_files)
            text += f"; ignored unparsed STEP files: {ignored_names}"
        return text

    def _checkbox_label(self, category: str, code: str, components: list[Component]) -> str:
        label = CATEGORY_METADATA[category].label_for(code)
        count = sum(1 for component in components if component.value_for(category) == code)
        return f"{code} - {label} ({count})"

    def _set_all_subset_values(self, value: bool) -> None:
        for category_vars in self.category_vars.values():
            for var in category_vars.values():
                var.set(value)
        self._update_selected_count()

    def _selected_criteria(self) -> SelectionCriteria:
        allowed_values = {
            category: {code for code, var in code_vars.items() if var.get()}
            for category, code_vars in self.category_vars.items()
        }
        return SelectionCriteria(allowed_values=allowed_values)

    def _selected_subset(self) -> list[Component]:
        return self._selected_criteria().filter_components(self.catalog.components)

    def _update_selected_count(self) -> None:
        selected_count = len(self._selected_subset())
        self.selected_count_var.set(f"Selected subset: {selected_count} component(s)")

    def _confirm_subset(self) -> None:
        empty_categories = [
            CATEGORY_METADATA[category].title
            for category, code_vars in self.category_vars.items()
            if not any(var.get() for var in code_vars.values())
        ]
        if empty_categories:
            messagebox.showerror("Subset incomplete", "Select at least one value for: " + ", ".join(empty_categories))
            return

        self.selected_components = self._selected_subset()
        if not self.selected_components:
            messagebox.showerror("No components selected", "The selected category filters contain no STEP files.")
            return

        self.confirmed_generalization_categories = set()
        self.confirmed_generalization_test_values = {}
        self._build_generalization_stage()
