from __future__ import annotations

from typing import Iterable

from .metadata import CATEGORY_METADATA, category_sort_key
from .models import Component


def validate_component_count(components: list[Component]) -> None:
    if not components:
        raise ValueError("No components are available for the selected subset.")
    if len(components) < 2:
        raise ValueError("A development/validation split needs at least two selected components.")


def clamped_test_count(selected_count: int, target_test_count: int) -> int:
    return max(1, min(target_test_count, selected_count - 1))


def scaled_counts(
    selected_count: int,
    train_candidate_count: int,
    test_candidate_count: int,
    target_test_count: int,
) -> tuple[int, int]:
    target_test_count = clamped_test_count(selected_count, target_test_count)
    target_train_count = selected_count - target_test_count
    scale = min(1.0, train_candidate_count / target_train_count, test_candidate_count / target_test_count)
    train_count = max(1, min(train_candidate_count, round(target_train_count * scale)))
    test_count = max(1, min(test_candidate_count, round(target_test_count * scale)))
    return train_count, test_count


def format_codes(category: str, values: Iterable[str]) -> str:
    sorted_values = sorted(values, key=lambda code: category_sort_key(category, code))
    return ", ".join(sorted_values)


def validate_holdout_values(category: str, available_values: set[str], test_values: set[str]) -> None:
    unknown_values = test_values - available_values
    if unknown_values:
        unknown_text = format_codes(category, unknown_values)
        raise ValueError(f"{CATEGORY_METADATA[category].title} has unknown excluded value(s): {unknown_text}.")
    if not test_values:
        raise ValueError(f"Select at least one excluded value for {CATEGORY_METADATA[category].title}.")
    if test_values == available_values:
        raise ValueError(f"Leave at least one {CATEGORY_METADATA[category].title} value available for development.")


def sort_components(components: Iterable[Component]) -> list[Component]:
    return sorted(components, key=lambda component: component.name.lower())
