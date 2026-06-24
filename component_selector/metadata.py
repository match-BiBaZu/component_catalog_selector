from __future__ import annotations

from dataclasses import dataclass


CATEGORY_ORDER = ("shape", "aspect", "symmetry", "feature")


@dataclass(frozen=True)
class CategoryMetadata:
    key: str
    title: str
    code_labels: dict[str, str]

    def label_for(self, code: str) -> str:
        return self.code_labels.get(code, f"Unmapped code {code}")


CATEGORY_METADATA = {
    "shape": CategoryMetadata(
        key="shape",
        title="Cross section shape",
        code_labels={
            "C": "Circle",
            "S": "Square",
            "R": "Rectangle",
            "T": "Triangle",
        },
    ),
    "aspect": CategoryMetadata(
        key="aspect",
        title="Aspect ratio length",
        code_labels={
            "s": "Short",
            "f": "Flat",
            "l": "Long",
        },
    ),
    "symmetry": CategoryMetadata(
        key="symmetry",
        title="Symmetry type",
        code_labels={
            "1": "X-axis / primary-axis symmetry",
            "2": "Y-axis symmetry",
            "3": "Z-axis symmetry (rectangles)",
            "4": "No symmetry",
        },
    ),
    "feature": CategoryMetadata(
        key="feature",
        title="Feature type",
        code_labels={
            "i": "Internal features",
            "o": "External features",
        },
    ),
}


def category_sort_key(category: str, code: str) -> tuple[int, str]:
    labels = CATEGORY_METADATA[category].code_labels
    known_codes = list(labels)
    if code in labels:
        return known_codes.index(code), code
    return len(known_codes), code

