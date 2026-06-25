from __future__ import annotations

from tkinter import ttk


class SplitSettingsMixin:
    def _build_target_split_settings(self, parent: ttk.Frame) -> None:
        self.target_test_percent_var.set(30.0)
        self._update_target_test_percent_label()

        row = 2 if self.confirmed_generalization_categories else 1
        self._build_split_context(parent)

        ttk.Label(parent, text="Target validation share").grid(row=row, column=0, sticky="w", padx=(0, 12))
        test_percent_scale = ttk.Scale(
            parent,
            from_=1,
            to=99,
            variable=self.target_test_percent_var,
            command=self._update_target_test_percent_label,
        )
        if len(self.selected_components) < 2:
            test_percent_scale.state(["disabled"])
        test_percent_scale.grid(row=row, column=1, sticky="ew")
        ttk.Label(parent, textvariable=self.target_test_percent_label_var, width=8).grid(
            row=row,
            column=2,
            sticky="e",
            padx=(12, 0),
        )
        ttk.Label(
            parent,
            textvariable=self.actual_split_preview_var,
            foreground="#555555",
            wraplength=720,
        ).grid(row=row + 1, column=0, columnspan=3, sticky="w", pady=(4, 0))
        self._build_seed_controls(parent, start_row=row + 2)
        self._build_clear_existing_control(parent, row=row + 3)

    def _build_split_context(self, parent: ttk.Frame) -> None:
        if self.confirmed_generalization_categories:
            ttk.Label(
                parent,
                text=(
                    "The split is still controllable, but excluded values change which components are eligible "
                    "for each folder. The slider targets the copied development/validation ratio and ignores unused files."
                ),
                foreground="#555555",
                wraplength=720,
            ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))
            summary_text = "\n".join(self._generalization_selection_summary_lines())
            ttk.Label(parent, text=summary_text, wraplength=720).grid(
                row=1,
                column=0,
                columnspan=3,
                sticky="w",
                pady=(0, 8),
            )
            return

        ttk.Label(
            parent,
            text="No values are excluded from development; the live preview shows the balanced split size.",
            foreground="#555555",
            wraplength=720,
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))

    def _build_seed_controls(self, parent: ttk.Frame, start_row: int) -> None:
        ttk.Label(parent, text="Random seed").grid(row=start_row, column=0, sticky="w", padx=(0, 12), pady=(8, 0))
        ttk.Entry(parent, textvariable=self.random_seed_var, width=18).grid(
            row=start_row,
            column=1,
            sticky="w",
            pady=(8, 0),
        )
        ttk.Label(parent, text="Blank = new random sample; whole number = repeatable", foreground="#555555").grid(
            row=start_row,
            column=2,
            sticky="w",
            padx=(12, 0),
            pady=(8, 0),
        )

    def _build_clear_existing_control(self, parent: ttk.Frame, row: int) -> None:
        ttk.Checkbutton(
            parent,
            text="Clear existing STEP/STL files in output folders",
            variable=self.clear_existing_var,
        ).grid(row=row, column=0, columnspan=3, sticky="w", pady=(8, 0))
