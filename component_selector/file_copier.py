from __future__ import annotations

import shutil
from pathlib import Path
from typing import Iterable

from .catalog import CatalogScanner
from .models import Component, CopyResult, SplitResult


class ComponentFileCopier:
    TRAIN_DIR_NAME = "ComponentTrain"
    TEST_DIR_NAME = "ComponentTest"

    def __init__(self, output_root: Path) -> None:
        self.output_root = output_root

    def copy_split(self, split_result: SplitResult, clear_existing_step_files: bool) -> CopyResult:
        train_dir = self.output_root / self.TRAIN_DIR_NAME
        test_dir = self.output_root / self.TEST_DIR_NAME

        train_dir.mkdir(exist_ok=True)
        test_dir.mkdir(exist_ok=True)

        if clear_existing_step_files:
            self._clear_step_files(train_dir)
            self._clear_step_files(test_dir)

        self._copy_components(split_result.train_components, train_dir)
        self._copy_components(split_result.test_components, test_dir)

        return CopyResult(
            train_dir=train_dir,
            test_dir=test_dir,
            train_count=len(split_result.train_components),
            test_count=len(split_result.test_components),
        )

    def _clear_step_files(self, folder: Path) -> None:
        for path in folder.iterdir():
            if path.is_file() and path.suffix.lower() in CatalogScanner.STEP_EXTENSIONS:
                path.unlink()

    def _copy_components(self, components: Iterable[Component], destination_dir: Path) -> None:
        for component in components:
            shutil.copy2(component.path, destination_dir / component.path.name)

