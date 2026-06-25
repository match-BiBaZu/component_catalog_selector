from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from .models import SplitConfig


class SplitStageMixin:
    def _selected_target_test_percent(self) -> int:
        if not self.selected_components:
            return 0
        percent = round(self.target_test_percent_var.get())
        return max(1, min(percent, 99))

    def _selected_target_test_count(self) -> int:
        if len(self.selected_components) < 2:
            return 0
        percent = self._selected_target_test_percent()
        if self.confirmed_generalization_test_values:
            return self._target_test_count_for_used_split(percent)
        test_count = round(len(self.selected_components) * (percent / 100))
        return max(1, min(test_count, len(self.selected_components) - 1))

    def _target_test_count_for_used_split(self, percent: int) -> int:
        target_share = percent / 100
        train_candidates, _test_candidates, _choices = self.split_planner.holdout_candidate_counts(
            components=self.selected_components,
            holdout_values=self.confirmed_generalization_test_values,
        )
        best_count = 1
        best_score: tuple[float, int, int] | None = None

        for test_count in range(1, len(self.selected_components)):
            train_candidate_test_count = self.split_planner.estimate_development_candidates_in_validation(
                components=self.selected_components,
                holdout_values=self.confirmed_generalization_test_values,
                target_test_count=test_count,
            )
            train_count = max(0, train_candidates - train_candidate_test_count)
            copied_count = train_count + test_count
            if copied_count == 0:
                continue

            score = (
                abs((test_count / copied_count) - target_share),
                len(self.selected_components) - copied_count,
                test_count,
            )
            if best_score is None or score < best_score:
                best_score = score
                best_count = test_count

        return best_count

    def _update_target_test_percent_label(self, _value: str | None = None) -> None:
        percent = self._selected_target_test_percent()
        self.target_test_percent_var.set(float(percent))
        test_count = self._selected_target_test_count()

        if not self.selected_components:
            self.target_test_percent_label_var.set("0%")
            self.actual_split_preview_var.set("Will copy: 0 development / 0 validation")
            return

        self.target_test_percent_label_var.set(f"{percent}%")
        self.actual_split_preview_var.set(self._split_preview_text(test_count))

    def _split_preview_text(self, target_test_count: int) -> str:
        try:
            preview = self.split_planner.preview_split(
                components=self.selected_components,
                holdout_values=self.confirmed_generalization_test_values,
                target_test_count=target_test_count,
            )
        except ValueError as error:
            return f"Preview unavailable: {error}"

        text = f"Will copy: {preview.train_count} development / {preview.test_count} validation"
        if preview.unused_count:
            text += f" / {preview.unused_count} unused after exclusion/balancing constraints"

        if preview.holdout_active:
            text += (
                f" (eligible: {preview.train_candidate_count} development candidates, "
                f"{preview.test_candidate_count} validation candidates)"
            )
        return text

    def _build_split_stage(self) -> None:
        self._clear_main_frame()

        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=0)
        self.main_frame.grid_rowconfigure(2, weight=1)
        self.main_frame.grid_rowconfigure(3, weight=0)
        self.main_frame.grid_rowconfigure(4, weight=0)

        header = ttk.Frame(self.main_frame)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        header.grid_columnconfigure(0, weight=1)

        ttk.Label(header, text="Stage 3: Create split", font=("", 16, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(header, text=f"Subset size: {len(self.selected_components)} component(s)").grid(
            row=1,
            column=0,
            sticky="w",
            pady=(4, 0),
        )
        ttk.Label(
            header,
            text=(
                "Exclusion and balancing constraints can alter the overall number of components in "
                "DevelopmentSet and ValidationSet."
            ),
            foreground="#555555",
            wraplength=760,
        ).grid(row=2, column=0, sticky="w", pady=(4, 0))
        ttk.Button(header, text="Back", command=self._build_generalization_stage).grid(
            row=0,
            column=1,
            rowspan=3,
            sticky="e",
        )

        settings_frame = ttk.LabelFrame(self.main_frame, text="Split settings", padding=10)
        settings_frame.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        settings_frame.grid_columnconfigure(1, weight=1)
        self._build_target_split_settings(settings_frame)

        self._build_output_area(row=2)
        self._build_create_button(row=3)

        initial_lines = ["Ready to create split.", ""]
        initial_lines.extend(self._generalization_selection_summary_lines())
        self._write_output_text("\n".join(initial_lines))

    def _build_output_area(self, row: int) -> None:
        output_frame = ttk.LabelFrame(self.main_frame, text="Split output", padding=10)
        output_frame.grid(row=row, column=0, sticky="nsew")
        output_frame.grid_rowconfigure(0, weight=1)
        output_frame.grid_columnconfigure(0, weight=1)

        self.output_text = tk.Text(output_frame, height=14, wrap="word")
        output_scrollbar = ttk.Scrollbar(output_frame, orient="vertical", command=self.output_text.yview)
        self.output_text.configure(yscrollcommand=output_scrollbar.set)
        self.output_text.grid(row=0, column=0, sticky="nsew")
        output_scrollbar.grid(row=0, column=1, sticky="ns")

    def _build_create_button(self, row: int) -> None:
        button_bar = ttk.Frame(self.main_frame)
        button_bar.grid(row=row, column=0, sticky="ew", pady=(12, 0))
        button_bar.grid_columnconfigure(0, weight=1)
        ttk.Button(button_bar, text="Create development/validation folders", command=self._create_train_test_split).grid(
            row=0,
            column=1,
            sticky="e",
        )

    def _create_train_test_split(self) -> None:
        random_seed = self._parse_random_seed()
        if random_seed is False:
            return

        config = SplitConfig(
            holdout_values=self.confirmed_generalization_test_values,
            target_test_count=self._selected_target_test_count(),
            random_seed=random_seed,
            clear_existing_files=self.clear_existing_var.get(),
            selected_data_types=self._selected_data_types(),
        )

        try:
            split_result = self.split_planner.create_split(self.selected_components, config)
            copy_result = self.file_copier.copy_split(
                split_result=split_result,
                clear_existing_files=config.clear_existing_files,
                selected_data_types=config.selected_data_types,
            )
        except OSError as error:
            messagebox.showerror("File copy failed", str(error))
            return
        except ValueError as error:
            messagebox.showerror("Split failed", str(error))
            return

        self._write_split_result(split_result, copy_result)
        messagebox.showinfo(
            "Split complete",
            (
                f"Copied {copy_result.train_file_count} development and "
                f"{copy_result.test_file_count} validation file(s)."
            ),
        )

    def _parse_random_seed(self) -> int | None | bool:
        seed_text = self.random_seed_var.get().strip()
        if not seed_text:
            return None

        try:
            return int(seed_text)
        except ValueError:
            messagebox.showerror("Invalid seed", "Random seed must be a whole number or blank.")
            return False
