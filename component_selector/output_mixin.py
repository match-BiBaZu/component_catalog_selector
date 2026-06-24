from __future__ import annotations

from typing import Iterable

from .metadata import CATEGORY_METADATA, CATEGORY_ORDER, category_sort_key
from .models import Component, CopyResult, GeneralizationChoice, SplitResult


class OutputMixin:
    def _generalization_selection_summary_lines(self) -> list[str]:
        if not self.confirmed_generalization_categories:
            return ["Held out from ComponentTrain: none; the selected subset will be randomly split."]

        lines = ["Confirmed values held out from ComponentTrain:"]
        for category in CATEGORY_ORDER:
            if category not in self.confirmed_generalization_categories:
                continue

            test_values = self._format_category_values(
                category,
                self.confirmed_generalization_test_values[category],
            )
            lines.append(f"- {CATEGORY_METADATA[category].title}: {test_values}")
        return lines

    def _write_split_result(self, split_result: SplitResult, copy_result: CopyResult) -> None:
        lines = [
            "Selection complete",
            "",
            self._random_seed_summary(split_result),
            f"Target test share: {self._selected_target_test_percent()}%",
            self._actual_split_summary(split_result),
            f"ComponentTrain folder: {copy_result.train_dir}",
            f"ComponentTest folder:  {copy_result.test_dir}",
            "",
        ]

        lines.extend(self._generalization_summary_lines(split_result.generalization_choices))
        lines.extend(
            [
                "",
                f"ComponentTrain ({len(split_result.train_components)} component(s)):",
                *self._component_lines(split_result.train_components),
                "",
                f"ComponentTest ({len(split_result.test_components)} component(s)):",
                *self._component_lines(split_result.test_components),
                "",
            ]
        )

        if split_result.unused_components:
            lines.extend(
                [
                    f"Unused selected components ({len(split_result.unused_components)} component(s)):",
                    *self._component_lines(split_result.unused_components),
                    "",
                ]
            )

        self._write_output_text("\n".join(lines))

    def _generalization_summary_lines(
        self,
        choices: dict[str, GeneralizationChoice],
    ) -> list[str]:
        if not choices:
            return ["Held out from ComponentTrain: none; random split was used."]

        lines = ["Hold-out choices:"]
        for category in CATEGORY_ORDER:
            if category not in choices:
                lines.append(f"- {CATEGORY_METADATA[category].title}: not held out")
                continue

            choice = choices[category]
            train_values = self._format_category_values(category, choice.train_values)
            test_values = self._format_category_values(category, choice.test_values)
            lines.append(
                f"- {CATEGORY_METADATA[category].title}: train uses {train_values}; "
                f"held out from train {test_values}"
            )
        return lines

    def _random_seed_summary(self, split_result: SplitResult) -> str:
        return f"Random seed: {split_result.random_seed}"

    def _actual_split_summary(self, split_result: SplitResult) -> str:
        summary = (
            f"Actual copied split: {len(split_result.train_components)} train / "
            f"{len(split_result.test_components)} test"
        )
        if split_result.unused_components:
            summary += f" / {len(split_result.unused_components)} unused due to hold-out constraints"
        return summary

    def _format_category_values(self, category: str, values: Iterable[str]) -> str:
        sorted_values = sorted(values, key=lambda code: category_sort_key(category, code))
        return ", ".join(f"{code} ({CATEGORY_METADATA[category].label_for(code)})" for code in sorted_values)

    def _component_lines(self, components: list[Component]) -> list[str]:
        if not components:
            return ["- none"]
        return [f"- {component.display_summary()}" for component in components]

    def _write_output_text(self, text: str) -> None:
        if self.output_text is None:
            return
        self.output_text.configure(state="normal")
        self.output_text.delete("1.0", "end")
        self.output_text.insert("1.0", text)
        self.output_text.configure(state="disabled")
