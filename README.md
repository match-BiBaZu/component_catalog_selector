# component_catalog_selector

This is a small selection tool for a 39-component catalog of industrially relevant STEP components. Components are encoded by cross-section shape, aspect ratio, symmetry type, and feature type.

## Run the selector

```powershell
python component_train_test_selector.py
```

The GUI works in three stages:

1. Select the subset of `FullCatalog` to use with checkboxes for shape, aspect ratio, symmetry type, and feature type.
2. Select the characteristic values to hold out from `ComponentTrain`. Holding out means those values are excluded from the training folder and are used only as test candidates.
3. Create the train/test folders. The target test-share slider is applied after the hold-out choices are confirmed.

When the split is created, the script copies the selected STEP files into:

- `ComponentTrain`
- `ComponentTest`

The GUI also reports the component names and counts for each split.

The test slider is a percentage target. The split is still controllable, but hold-out choices change which components are eligible for each folder. The GUI shows a live preview of the actual files that will be copied, including any selected components that will remain unused because of hold-out constraints.

## ID format

Each filename uses this pattern:

```text
<shape><aspect><symmetry><feature>.STEP
```

Examples:

- `C`: circle, `S`: square, `R`: rectangle, `T`: triangle
- `s`: short, `f`: flat, `l`: long
- `1`: X-axis / primary-axis symmetry, `2`: Y-axis symmetry, `3`: Z-axis symmetry for rectangles, `4`: no symmetry
- `i`: internal features, `o`: external features

The random seed field can be left blank for a new random split each time. Enter any whole number, such as `123`, to make the split repeatable.

## Code layout

`component_train_test_selector.py` is the launcher. The implementation lives in `component_selector/` and is split by responsibility: catalog scanning, data models, split planning, file copying, shared widgets, and GUI stage mixins.
