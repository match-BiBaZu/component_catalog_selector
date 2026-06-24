from __future__ import annotations

import random

from .metadata import CATEGORY_METADATA, category_sort_key
from .models import Component, GeneralizationChoice, SplitConfig, SplitPreview, SplitResult
from .split_helpers import (
    clamped_test_count,
    sample_components,
    scaled_counts,
    sort_components,
    validate_component_count,
    validate_holdout_values,
)


class SplitPlanner:
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

        train_candidates, test_candidates, _choices = self._holdout_candidates(
            components=components,
            holdout_values=holdout_values,
        )
        train_count, test_count = scaled_counts(
            selected_count=len(components),
            train_candidate_count=len(train_candidates),
            test_candidate_count=len(test_candidates),
            target_test_count=target_test_count,
        )

        return SplitPreview(
            target_test_count=target_test_count,
            train_count=train_count,
            test_count=test_count,
            unused_count=len(components) - train_count - test_count,
            train_candidate_count=len(train_candidates),
            test_candidate_count=len(test_candidates),
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
        shuffled_components = list(components)
        rng.shuffle(shuffled_components)
        test_count = max(1, min(target_test_count, len(shuffled_components) - 1))
        test_components = shuffled_components[:test_count]
        train_components = shuffled_components[test_count:]
        return sort_components(train_components), sort_components(test_components)

    def _create_holdout_split(
        self,
        components: list[Component],
        holdout_values: dict[str, set[str]],
        target_test_count: int,
        seed: int,
        rng: random.Random,
    ) -> SplitResult:
        train_candidates, test_candidates, choices = self._holdout_candidates(
            components=components,
            holdout_values=holdout_values,
        )
        train_count, test_count = scaled_counts(
            selected_count=len(components),
            train_candidate_count=len(train_candidates),
            test_candidate_count=len(test_candidates),
            target_test_count=target_test_count,
        )
        selected_train = sample_components(train_candidates, train_count, rng)
        selected_test = sample_components(test_candidates, test_count, rng)
        used_paths = {component.path for component in selected_train + selected_test}
        unused_components = [component for component in components if component.path not in used_paths]

        return SplitResult(
            train_components=sort_components(selected_train),
            test_components=sort_components(selected_test),
            unused_components=sort_components(unused_components),
            generalization_choices=choices,
            target_test_count=target_test_count,
            random_seed=seed,
        )

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
                "No non-empty train/test split could be created for the selected held-out values: "
                f"{titles}. Leave at least one value available for training and testing."
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
                raise ValueError(f"{CATEGORY_METADATA[category].title} has no held-out variation in this subset.")
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
