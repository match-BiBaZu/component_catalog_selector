from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from .metadata import CATEGORY_METADATA, CATEGORY_ORDER, category_sort_key


class HoldoutStageMixin:
    def _build_generalization_stage(self) -> None:
        self._clear_main_frame()
        self.generalization_test_value_vars = {}

        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1)
        self.main_frame.grid_rowconfigure(2, weight=0)
        self.main_frame.grid_rowconfigure(3, weight=0)
        self.main_frame.grid_rowconfigure(4, weight=0)

        header = ttk.Frame(self.main_frame)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        header.grid_columnconfigure(0, weight=1)

        ttk.Label(header, text="Stage 2: Hold out from training", font=("", 16, "bold")).grid(
            row=0,
            column=0,
            sticky="w",
        )
        ttk.Label(
            header,
            text=f"Subset size: {len(self.selected_components)} component(s). "
            "Checked values are excluded from ComponentTrain.",
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))
        ttk.Button(header, text="Back", command=self._build_subset_stage).grid(row=0, column=1, rowspan=2, sticky="e")

        options_frame = ttk.Frame(self.main_frame)
        options_frame.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        options_frame.grid_columnconfigure(0, weight=1)
        options_frame.grid_columnconfigure(1, weight=1)

        values_by_category = self.catalog.values_by_category(self.selected_components)
        for index, category in enumerate(CATEGORY_ORDER):
            frame = ttk.LabelFrame(options_frame, text=CATEGORY_METADATA[category].title, padding=10)
            frame.grid(
                row=index // 2,
                column=index % 2,
                sticky="nsew",
                padx=(0 if index % 2 == 0 else 8, 0 if index % 2 == 1 else 8),
                pady=8,
            )
            frame.grid_columnconfigure(0, weight=1)
            self._build_holdout_category(frame, category, values_by_category[category])

        footer = ttk.Frame(self.main_frame)
        footer.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        footer.grid_columnconfigure(0, weight=1)
        ttk.Button(footer, text="Confirm hold-out selection", command=self._confirm_generalization_config).grid(
            row=0,
            column=1,
            sticky="e",
        )

    def _build_holdout_category(self, frame: ttk.LabelFrame, category: str, values: set[str]) -> None:
        sorted_values = sorted(values, key=lambda code: category_sort_key(category, code))
        self.generalization_test_value_vars[category] = {}

        if len(sorted_values) < 2:
            labels = [f"{code} - {CATEGORY_METADATA[category].label_for(code)}" for code in sorted_values]
            ttk.Label(
                frame,
                text="No hold-out variation available: " + ", ".join(labels),
                foreground="#555555",
                wraplength=380,
            ).grid(row=0, column=0, sticky="w", pady=(6, 0))
            return

        ttk.Label(frame, text="Hold out from ComponentTrain:", foreground="#555555").grid(
            row=0,
            column=0,
            sticky="w",
            pady=(0, 6),
        )
        for value_index, code in enumerate(sorted_values):
            value_var = tk.BooleanVar(value=False)
            self.generalization_test_value_vars[category][code] = value_var
            ttk.Checkbutton(
                frame,
                text=f"{code} - {CATEGORY_METADATA[category].label_for(code)}",
                variable=value_var,
            ).grid(row=value_index + 1, column=0, sticky="w", padx=(16, 0), pady=1)

    def _selected_holdout_values(self) -> dict[str, set[str]] | None:
        holdout_values: dict[str, set[str]] = {}

        for category in CATEGORY_ORDER:
            value_vars = self.generalization_test_value_vars[category]
            selected_values = {code for code, value_var in value_vars.items() if value_var.get()}
            available_values = set(value_vars)
            category_title = CATEGORY_METADATA[category].title

            if not selected_values:
                continue

            if selected_values == available_values:
                messagebox.showerror(
                    "No train type left",
                    f"Leave at least one {category_title} value unchecked so it can remain in ComponentTrain.",
                )
                return None

            holdout_values[category] = selected_values

        return holdout_values

    def _confirm_generalization_config(self) -> None:
        holdout_values = self._selected_holdout_values()
        if holdout_values is None:
            return

        self.confirmed_generalization_categories = set(holdout_values)
        self.confirmed_generalization_test_values = holdout_values
        self._build_split_stage()
