from __future__ import annotations

import re
from pathlib import Path

from .models import CatalogScanResult, Component


class CatalogScanner:
    STEP_EXTENSIONS = {".step", ".stp"}
    COMPONENT_ID_PATTERN = re.compile(r"^([A-Za-z])([A-Za-z])([0-9]+)([A-Za-z])$")

    def __init__(self, catalog_dir: Path) -> None:
        self.catalog_dir = catalog_dir

    def scan(self) -> CatalogScanResult:
        if not self.catalog_dir.exists():
            raise FileNotFoundError(f"Catalog folder not found: {self.catalog_dir}")

        components: list[Component] = []
        ignored_non_step_files: list[Path] = []
        ignored_unparsed_step_files: list[Path] = []

        for path in sorted(self.catalog_dir.iterdir(), key=lambda item: item.name.lower()):
            if not path.is_file():
                continue

            if path.suffix.lower() not in self.STEP_EXTENSIONS:
                ignored_non_step_files.append(path)
                continue

            parsed_component = self._parse_component(path)
            if parsed_component is None:
                ignored_unparsed_step_files.append(path)
                continue

            components.append(parsed_component)

        return CatalogScanResult(
            components=components,
            ignored_non_step_files=ignored_non_step_files,
            ignored_unparsed_step_files=ignored_unparsed_step_files,
        )

    def _parse_component(self, path: Path) -> Component | None:
        match = self.COMPONENT_ID_PATTERN.match(path.stem)
        if match is None:
            return None

        shape, aspect, symmetry, feature = match.groups()
        return Component(
            path=path,
            component_id=path.stem,
            shape=shape,
            aspect=aspect,
            symmetry=symmetry,
            feature=feature,
        )

