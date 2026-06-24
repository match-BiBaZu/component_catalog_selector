from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .metadata import CATEGORY_METADATA, CATEGORY_ORDER


@dataclass(frozen=True)
class Component:
    path: Path
    component_id: str
    shape: str
    aspect: str
    symmetry: str
    feature: str

    @property
    def name(self) -> str:
        return self.path.name

    def value_for(self, category: str) -> str:
        return getattr(self, category)

    def display_summary(self) -> str:
        parts = []
        for category in CATEGORY_ORDER:
            code = self.value_for(category)
            label = CATEGORY_METADATA[category].label_for(code)
            parts.append(f"{code}: {label}")
        return f"{self.name} ({', '.join(parts)})"


@dataclass(frozen=True)
class CatalogScanResult:
    components: list[Component]
    ignored_non_step_files: list[Path]
    ignored_unparsed_step_files: list[Path]

    def values_by_category(self, components: Iterable[Component] | None = None) -> dict[str, set[str]]:
        selected_components = list(components) if components is not None else self.components
        return {
            category: {component.value_for(category) for component in selected_components}
            for category in CATEGORY_ORDER
        }


@dataclass(frozen=True)
class SelectionCriteria:
    allowed_values: dict[str, set[str]]

    def filter_components(self, components: Iterable[Component]) -> list[Component]:
        return [
            component
            for component in components
            if all(component.value_for(category) in values for category, values in self.allowed_values.items())
        ]


@dataclass(frozen=True)
class SplitConfig:
    holdout_values: dict[str, set[str]]
    target_test_count: int
    random_seed: int | None
    clear_existing_step_files: bool


@dataclass(frozen=True)
class GeneralizationChoice:
    train_values: set[str]
    test_values: set[str]


@dataclass(frozen=True)
class SplitResult:
    train_components: list[Component]
    test_components: list[Component]
    unused_components: list[Component]
    generalization_choices: dict[str, GeneralizationChoice]
    target_test_count: int
    random_seed: int


@dataclass(frozen=True)
class SplitPreview:
    target_test_count: int
    train_count: int
    test_count: int
    unused_count: int
    train_candidate_count: int
    test_candidate_count: int
    holdout_active: bool


@dataclass(frozen=True)
class CopyResult:
    train_dir: Path
    test_dir: Path
    train_count: int
    test_count: int

