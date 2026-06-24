# component_catalog_selector

This is a small selection tool for a 39-component catalog of industrially relevant STEP and STL components. Components are encoded by cross-section shape, aspect ratio, symmetry type, and feature type.

## Run the executable

Use the executable if you just want to run the selector without opening or editing the Python code.

The executable is:

```text
component_selector_ready2run\ComponentCatalogSelector.exe
```

Place the full catalog folders in the same folder as the executable:


Then double-click `ComponentCatalogSelector.exe`.

The selector creates or updates these folders beside the executable:

- `DevelopmentSet`
- `ValidationSet`

## Run from Python source

The app uses only the Python standard library at runtime. No extra Python packages are needed to run the source code.

Required runtime libraries:

- Python 3.11 or newer recommended
- `tkinter`, included with the standard Windows Python install

Run the selector from this project folder:

```powershell
python component_train_test_selector.py
```

The catalog folders must be in the same folder as `component_train_test_selector.py`:

```text
FullCatalogSTEP
FullCatalogSTL
```

## Build the executable

Install the build dependency once:

```powershell
python -m pip install -r requirements-build.txt
```

Build the executable:

```powershell
.\build_exe.ps1
```

If PowerShell blocks scripts on your machine, run:

```powershell
powershell -ExecutionPolicy Bypass -File .\build_exe.ps1
```

There is a ready to run example of the executable and the STEP and STL catalogs if you would like to just run the selector executable

Build dependency:

- PyInstaller 6.21.0

## Development environment

This project was developed and built on:

- OS: Windows 10 Education, Windows NT 10.0.26100.0 / Windows version 10.0.26100.8655
- Python: 3.11.9
- Tkinter GUI backend: Tcl/Tk 8.6
- PyInstaller: 6.21.0, only needed to build the executable

## Step-by-step example

Example goal: create a validation set that contains circular components with external features, and create STEP and STL output files.

1. Start the selector.

   Double-click `ComponentCatalogSelector.exe`, or run:

   ```powershell
   python component_train_test_selector.py
   ```

2. Stage 1: Catalog subset.

   Select the categories to include in the validation set from the overall catalog. For this example:

   - In `Data type`, check `STEP` and `STL`.
   - In `Shape`, leave `C - circle` checked and clear the other shapes.
   - In `Feature type`, leave `o - external features` checked and clear `i - internal features`.
   - Leave the aspect ratio and symmetry values checked unless you want to narrow the subset further.
   - Click `Confirm subset`.

3. Stage 2: Exclude from development.

   Select categories to exclude from the development catalog only if you want to validate generalisation to those categories. For this example:

   - If you want every selected circle/external component to be split randomly, leave all exclusions unchecked.
   - If you want to validate generalisation to a specific value, check that value so it is excluded from development and used as a validation candidate.
   - Click `Confirm exclusions`.

4. Stage 3: Create split.

   Choose the target validation share with the slider. The preview shows how many components will go to development and validation. Exclusions can change the final counts because some selected components may become ineligible for one side of the split.

   Optionally enter a random seed such as `123` to make the split repeatable.

   Click `Create development/validation folders`.

5. Check the output folders.

   The selected files are copied into:

   - `DevelopmentSet`
   - `ValidationSet`

   If both `STEP` and `STL` were checked, each selected component is copied in both formats.

## GUI stages

1. Select the subset of `FullCatalogSTEP` and `FullCatalogSTL` to use with checkboxes for data type, shape, aspect ratio, symmetry type, and feature type.
2. Select characteristic values to exclude from `DevelopmentSet`. Excluded values are removed from the development folder and are used only as validation candidates.
3. Create the development/validation folders. The target validation-share slider is applied after the exclusion choices are confirmed.

The validation slider is a percentage target. The split is still controllable, but exclusion choices change which components are eligible for each folder. The GUI shows a live preview of the actual files that will be copied, including any selected components that will remain unused because of exclusion constraints.

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
