from __future__ import annotations

import random

from .metadata import CATEGORY_METADATA, CATEGORY_ORDER, category_sort_key
from .models import Component, GeneralizationChoice, SplitConfig, SplitPreview, SplitResult
from .split_helpers import (
    clamped_test_count,
    sort_components,
    validate_component_count,
    validate_holdout_values,
)


class SplitPlanner:
    def holdout_candidate_counts(
        self,
        components: list[Component],
        holdout_values: dict[str, set[str]],
    ) -> tuple[int, int, dict[str, GeneralizationChoice]]:
        train_candidates, test_candidates, choices = self._holdout_candidates(
            components=components,
            holdout_values=holdout_values,
        )
        return len(train_candidates), len(test_candidates), choices

    def estimate_development_candidates_in_validation(
        self,
        components: list[Component],
        holdout_values: dict[str, set[str]],
        target_test_count: int,
    ) -> int:
        train_candidates, _test_candidates, _choices = self._holdout_candidates(
            components=components,
            holdout_values=holdout_values,
        )
        target_test_count = clamped_test_count(len(components), target_test_count)
        estimated_count = round(target_test_count * (len(train_candidates) / len(components)))
        return max(0, min(estimated_count, len(train_candidates), target_test_count))

    def preview_split(
        self,
        components: list[Component],
        holdout_values: dict[str, set[str]],
        target_test_count: int,
    ) -> SplitPreview:
        validate_component_count(components)
        target_test_count = clamped_test_count(len(components), target_test_count)

        if not holdout_values:
            return SplitPreview(
                target_test_count=target_test_count,
                train_count=len(components) - target_test_count,
                test_count=target_test_count,
                unused_count=0,
                train_candidate_count=len(components) - target_test_count,
                test_candidate_count=target_test_count,
                holdout_active=False,
            )

        selected_train, selected_test, unused_components, _choices = self._plan_holdout_split(
            components=components,
            holdout_values=holdout_values,
            target_test_count=target_test_count,
            rng=random.Random(0),
        )
        train_candidates, _holdout_candidates, _choices = self._holdout_candidates(
            components=components,
            holdout_values=holdout_values,
        )

        return SplitPreview(
            target_test_count=target_test_count,
            train_count=len(selected_train),
            test_count=len(selected_test),
            unused_count=len(unused_components),
            train_candidate_count=len(train_candidates),
            test_candidate_count=len(components),
            holdout_active=True,
        )

    def create_split(self, components: list[Component], config: SplitConfig) -> SplitResult:
        validate_component_count(components)

        seed = config.random_seed
        if seed is None:
            seed = random.SystemRandom().randrange(1, 2**31)

        rng = random.Random(seed)
        target_test_count = clamped_test_count(len(components), config.target_test_count)

        if config.holdout_values:
            return self._create_holdout_split(
                components=components,
                holdout_values=config.holdout_values,
                target_test_count=target_test_count,
                seed=seed,
                rng=rng,
            )

        train_components, test_components = self._create_random_split(
            components=components,
            target_test_count=target_test_count,
            rng=rng,
        )
        return SplitResult(
            train_components=train_components,
            test_components=test_components,
            unused_components=[],
            generalization_choices={},
            target_test_count=target_test_count,
            random_seed=seed,
        )

    def _create_random_split(
        self,
        components: list[Component],
        target_test_count: int,
        rng: random.Random,
    ) -> tuple[list[Component], list[Component]]:
        test_count = max(1, min(target_test_count, len(components) - 1))
        test_components = self._select_balanced_components(
            candidates=components,
            count=test_count,
            rng=rng,
        )
        test_paths = {component.path for component in test_components}
        train_components = [component for component in components if component.path not in test_paths]
        return sort_components(train_components), sort_components(test_components)

    def _create_holdout_split(
        self,
        components: list[Component],
        holdout_values: dict[str, set[str]],
        target_test_count: int,
        seed: int,
        rng: random.Random,
    ) -> SplitResult:
        selected_train, selected_test, unused_components, choices = self._plan_holdout_split(
            components=components,
            holdout_values=holdout_values,
            target_test_count=target_test_count,
            rng=rng,
        )

        return SplitResult(
            train_components=sort_components(selected_train),
            test_components=sort_components(selected_test),
            unused_components=sort_components(unused_components),
            generalization_choices=choices,
            target_test_count=target_test_count,
            random_seed=seed,
        )

    def _plan_holdout_split(
        self,
        components: list[Component],
        holdout_values: dict[str, set[str]],
        target_test_count: int,
        rng: random.Random,
    ) -> tuple[list[Component], list[Component], list[Component], dict[str, GeneralizationChoice]]:
        train_candidates, _holdout_candidates, choices = self._holdout_candidates(
            components=components,
            holdout_values=holdout_values,
        )
        required_test_values = {
            category: set(choice.test_values)
            for category, choice in choices.items()
        }
        values_by_category = self._values_by_category(components)
        preferred_test_values = {
            category: values
            for category, values in required_test_values.items()
            if len(values_by_category[category]) <= 2
        }
        selected_test = self._select_balanced_components(
            candidates=components,
            count=target_test_count,
            rng=rng,
            required_values=required_test_values,
            preferred_values=preferred_test_values,
        )
        selected_test = self._improve_holdout_test_selection(
            components=components,
            train_candidates=train_candidates,
            selected_test=selected_test,
            required_test_values=required_test_values,
            preferred_test_values=preferred_test_values,
            rng=rng,
        )
        selected_test_paths = {component.path for component in selected_test}
        selected_train = [
            component for component in train_candidates if component.path not in selected_test_paths
        ]
        used_paths = {component.path for component in selected_train + selected_test}
        unused_components = [component for component in components if component.path not in used_paths]

        return selected_train, selected_test, unused_components, choices

    def _improve_holdout_test_selection(
        self,
        components: list[Component],
        train_candidates: list[Component],
        selected_test: list[Component],
        required_test_values: dict[str, set[str]],
        preferred_test_values: dict[str, set[str]],
        rng: random.Random,
    ) -> list[Component]:
        if not selected_test:
            return selected_test

        selected_components = list(selected_test)
        selected_paths = {component.path for component in selected_components}
        unselected_components = [component for component in components if component.path not in selected_paths]
        current_key = self._holdout_balance_key(
            components=components,
            train_candidates=train_candidates,
            selected_test=selected_components,
            required_test_values=required_test_values,
            preferred_test_values=preferred_test_values,
        )
        improved = True

        while improved:
            improved = False
            best_swap: tuple[tuple[float, float, int, float, float, float], str, str, int, int] | None = None

            for selected_index, selected_component in enumerate(selected_components):
                for unselected_index, unselected_component in enumerate(unselected_components):
                    candidate_test = list(selected_components)
                    candidate_test[selected_index] = unselected_component
                    if not self._has_required_values(candidate_test, required_test_values):
                        continue

                    candidate_key = self._holdout_balance_key(
                        components=components,
                        train_candidates=train_candidates,
                        selected_test=candidate_test,
                        required_test_values=required_test_values,
                        preferred_test_values=preferred_test_values,
                    )
                    swap_key = (
                        candidate_key,
                        selected_component.name.lower(),
                        unselected_component.name.lower(),
                        selected_index,
                        unselected_index,
                    )
                    if candidate_key < current_key and (best_swap is None or swap_key < best_swap):
                        best_swap = swap_key

            if best_swap is None:
                continue

            current_key, _selected_name, _unselected_name, selected_index, unselected_index = best_swap
            selected_components[selected_index], unselected_components[unselected_index] = (
                unselected_components[unselected_index],
                selected_components[selected_index],
            )
            improved = True

        return selected_components

    def _holdout_balance_key(
        self,
        components: list[Component],
        train_candidates: list[Component],
        selected_test: list[Component],
        required_test_values: dict[str, set[str]],
        preferred_test_values: dict[str, set[str]],
    ) -> tuple[float, float, int, float, float, float]:
        selected_test_paths = {component.path for component in selected_test}
        remaining_train_candidates = [
            component for component in train_candidates if component.path not in selected_test_paths
        ]
        test_values_by_category = self._values_by_category(components)
        test_availability_counts = self._category_counts(components, test_values_by_category)
        test_key = self._balance_key(
            selected_test,
            test_values_by_category,
            test_availability_counts,
            preferred_test_values,
        )

        if remaining_train_candidates:
            train_values_by_category = self._values_by_category(train_candidates)
            train_availability_counts = self._category_counts(
                train_candidates,
                train_values_by_category,
            )
            train_key = self._balance_key(
                remaining_train_candidates,
                train_values_by_category,
                train_availability_counts,
                {},
            )
        else:
            train_key = (0.0, 0.0, 0.0)

        return (
            max(test_key[0], train_key[0]),
            test_key[0] + train_key[0],
            -len(remaining_train_candidates),
            test_key[1] + train_key[1],
            test_key[2] + train_key[2],
            test_key[0],
        )

    def _select_balanced_components(
        self,
        candidates: list[Component],
        count: int,
        rng: random.Random,
        required_values: dict[str, set[str]] | None = None,
        preferred_values: dict[str, set[str]] | None = None,
    ) -> list[Component]:
        if count <= 0 or not candidates:
            return []
        if count >= len(candidates):
            return list(candidates)

        remaining = list(candidates)
        selected: list[Component] = []
        values_by_category = self._values_by_category(remaining)
        availability_counts = self._category_counts(remaining, values_by_category)
        preferred_values = preferred_values or {}

        for category, values in (required_values or {}).items():
            for value in sorted(values, key=lambda code: category_sort_key(category, code)):
                if len(selected) >= count:
                    break
                if any(component.value_for(category) == value for component in selected):
                    continue
                matching_components = [
                    component for component in remaining if component.value_for(category) == value
                ]
                if not matching_components:
                    continue
                component = self._best_balanced_addition(
                    matching_components,
                    selected,
                    values_by_category,
                    availability_counts,
                    preferred_values,
                    rng,
                )
                selected.append(component)
                remaining.remove(component)

        while len(selected) < count and remaining:
            component = self._best_balanced_addition(
                remaining,
                selected,
                values_by_category,
                availability_counts,
                preferred_values,
                rng,
            )
            selected.append(component)
            remaining.remove(component)

        return self._improve_balanced_selection(
            selected=selected,
            unselected=remaining,
            values_by_category=values_by_category,
            availability_counts=availability_counts,
            required_values=required_values or {},
            preferred_values=preferred_values,
            rng=rng,
        )

    def _best_balanced_addition(
        self,
        candidates: list[Component],
        selected: list[Component],
        values_by_category: dict[str, set[str]],
        availability_counts: dict[str, dict[str, int]],
        preferred_values: dict[str, set[str]],
        rng: random.Random,
    ) -> Component:
        return min(
            candidates,
            key=lambda component: (
                self._balance_key(
                    [*selected, component],
                    values_by_category,
                    availability_counts,
                    preferred_values,
                ),
                component.name.lower(),
            ),
        )

    def _improve_balanced_selection(
        self,
        selected: list[Component],
        unselected: list[Component],
        values_by_category: dict[str, set[str]],
        availability_counts: dict[str, dict[str, int]],
        required_values: dict[str, set[str]],
        preferred_values: dict[str, set[str]],
        rng: random.Random,
    ) -> list[Component]:
        if not selected or not unselected:
            return selected

        selected_components = list(selected)
        unselected_components = list(unselected)
        current_key = self._balance_key(
            selected_components,
            values_by_category,
            availability_counts,
            preferred_values,
        )
        improved = True

        while improved:
            improved = False
            best_swap: tuple[tuple[float, float, float], str, str, int, int] | None = None

            for selected_index, selected_component in enumerate(selected_components):
                for unselected_index, unselected_component in enumerate(unselected_components):
                    candidate_selection = list(selected_components)
                    candidate_selection[selected_index] = unselected_component
                    if not self._has_required_values(candidate_selection, required_values):
                        continue

                    candidate_key = self._balance_key(
                        candidate_selection,
                        values_by_category,
                        availability_counts,
                        preferred_values,
                    )
                    swap_key = (
                        candidate_key,
                        selected_component.name.lower(),
                        unselected_component.name.lower(),
                        selected_index,
                        unselected_index,
                    )
                    if candidate_key < current_key and (best_swap is None or swap_key < best_swap):
                        best_swap = swap_key

            if best_swap is None:
                continue

            current_key, _selected_name, _unselected_name, selected_index, unselected_index = best_swap
            selected_components[selected_index], unselected_components[unselected_index] = (
                unselected_components[unselected_index],
                selected_components[selected_index],
            )
            improved = True

        return selected_components

    def _has_required_values(
        self,
        components: list[Component],
        required_values: dict[str, set[str]],
    ) -> bool:
        return all(
            any(component.value_for(category) == value for component in components)
            for category, values in required_values.items()
            for value in values
        )

    def _balance_key(
        self,
        components: list[Component],
        values_by_category: dict[str, set[str]],
        availability_counts: dict[str, dict[str, int]],
        preferred_values: dict[str, set[str]],
    ) -> tuple[float, float, float]:
        total_score = 0.0
        worst_category_score = 0.0
        preferred_value_deficit_penalty = 0.0
        rare_value_deficit_penalty = 0.0
        for category, values in values_by_category.items():
            if not values:
                continue
            expected_count = len(components) / len(values)
            counts = {value: 0 for value in values}
            for component in components:
                value = component.value_for(category)
                if value in counts:
                    counts[value] += 1
            category_score = sum((count - expected_count) ** 2 for count in counts.values()) / len(values)
            total_score += category_score
            worst_category_score = max(worst_category_score, category_score)
            for value, count in counts.items():
                if count < expected_count:
                    if value in preferred_values.get(category, set()):
                        preferred_value_deficit_penalty += expected_count - count
                    availability_count = max(1, availability_counts[category][value])
                    rare_value_deficit_penalty += (expected_count - count) / availability_count
        balance_score = worst_category_score * 1000 + total_score
        return balance_score, preferred_value_deficit_penalty, rare_value_deficit_penalty

    def _category_counts(
        self,
        components: list[Component],
        values_by_category: dict[str, set[str]],
    ) -> dict[str, dict[str, int]]:
        counts = {
            category: {value: 0 for value in values}
            for category, values in values_by_category.items()
        }
        for component in components:
            for category in values_by_category:
                counts[category][component.value_for(category)] += 1
        return counts

    def _values_by_category(self, components: list[Component]) -> dict[str, set[str]]:
        return {
            category: {component.value_for(category) for component in components}
            for category in CATEGORY_ORDER
        }

    def _holdout_candidates(
        self,
        components: list[Component],
        holdout_values: dict[str, set[str]],
    ) -> tuple[list[Component], list[Component], dict[str, GeneralizationChoice]]:
        choices = self._create_holdout_choices(
            values_by_category=self._values_by_holdout_category(components, holdout_values),
            holdout_values=holdout_values,
        )
        train_candidates: list[Component] = []
        test_candidates: list[Component] = []

        for component in components:
            belongs_to_train = all(
                component.value_for(category) in choice.train_values
                for category, choice in choices.items()
            )
            (train_candidates if belongs_to_train else test_candidates).append(component)

        if not train_candidates or not test_candidates:
            titles = ", ".join(CATEGORY_METADATA[category].title for category in sorted(holdout_values))
            raise ValueError(
                "No non-empty development/validation split could be created for the selected excluded values: "
                f"{titles}. Leave at least one value available for development and validation."
            )

        return train_candidates, test_candidates, choices

    def _values_by_holdout_category(
        self,
        components: list[Component],
        holdout_values: dict[str, set[str]],
    ) -> dict[str, list[str]]:
        values_by_category = {
            category: sorted(
                {component.value_for(category) for component in components},
                key=lambda code, selected_category=category: category_sort_key(selected_category, code),
            )
            for category in holdout_values
        }
        for category, values in values_by_category.items():
            if len(values) < 2:
                raise ValueError(f"{CATEGORY_METADATA[category].title} has no exclusion variation in this subset.")
        return values_by_category

    def _create_holdout_choices(
        self,
        values_by_category: dict[str, list[str]],
        holdout_values: dict[str, set[str]],
    ) -> dict[str, GeneralizationChoice]:
        choices: dict[str, GeneralizationChoice] = {}
        for category, values in values_by_category.items():
            available_values = set(values)
            test_values = set(holdout_values[category])
            validate_holdout_values(category, available_values, test_values)
            choices[category] = GeneralizationChoice(
                train_values=available_values - test_values,
                test_values=test_values,
            )
        return choices
