# Papermill Path Resolution Research

**Date:** 2026-03-14
**Objective:** Determine how papermill handles notebook execution paths, working directories, and parameterization for notebooks inside `SC2-gamestate-extractor/EDA/` that read data from a path relative to the project root.

---

## Findings

### 1. Working Directory Behavior

**When `cwd` is NOT set:** The notebook executes in the calling process's current working directory (i.e., `os.getcwd()` at the time `execute_notebook()` is called). Papermill does NOT automatically change to the notebook's directory.

**When `cwd` IS set:** Papermill uses `os.chdir(cwd)` via a context manager before executing the notebook kernel, then restores the original directory afterward.

**Evidence (from papermill source `execute.py` and `utils.py`):**

```python
# utils.py - chdir context manager
@contextmanager
def chdir(path):
    """Change working directory to `path` and restore old path on exit.
    `path` can be `None` in which case this is a no-op.
    """
    if path is None:
        yield          # <-- NO directory change when cwd=None
    else:
        old_dir = os.getcwd()
        os.chdir(path)
        try:
            yield
        finally:
            os.chdir(old_dir)

# execute.py - usage
with chdir(cwd):
    nb = papermill_engines.execute_notebook_with_engine(...)
```

When `cwd=None` (the default), the `chdir` context manager is a no-op, meaning the notebook runs in whatever directory the Python process is currently in.

**Source:** [papermill/execute.py](https://github.com/nteract/papermill/blob/main/papermill/execute.py), [papermill/utils.py](https://github.com/nteract/papermill/blob/main/papermill/utils.py)

**Important caveat:** The `cwd` implementation uses `os.chdir()`, which is a process-global operation. It is NOT thread-safe. If multiple notebooks are executed concurrently via threads, `cwd` cannot be relied upon. See [GitHub Issue #473](https://github.com/nteract/papermill/issues/473). This is irrelevant for our use case (sequential execution) but worth noting.

---

### 2. In-Place Execution

**Can you use the same path for input and output?** Yes. This is safe.

**Evidence from source code analysis:**

In `execute.py`, the execution flow is:
1. `nb = load_notebook_node(input_path)` -- Reads the entire notebook into memory as a Python object
2. `nb = parameterize_notebook(nb, parameters, ...)` -- Modifies the in-memory object
3. `nb = prepare_notebook_metadata(nb, ...)` -- Modifies the in-memory object
4. `nb = papermill_engines.execute_notebook_with_engine(...)` -- Executes in memory; if `request_save_on_cell_execute=True`, writes incrementally to `output_path`
5. `write_ipynb(nb, output_path)` -- Final write

Since step 1 reads the entire notebook into memory before any writing occurs, using the same path for input and output is safe. The notebook content is fully loaded before any overwrite happens.

**Caveats:**
- If execution **fails midway** with `request_save_on_cell_execute=True` (the default), the output file will contain the partially-executed notebook. This means the original notebook is overwritten with a partially-executed version. The error-handling code in `raise_for_execution_errors()` writes the notebook with error markers before raising the exception.
- This is actually **desirable** for our use case: even on failure, we get a notebook with visible error output, and the user can re-run the pipeline to regenerate it.
- If `request_save_on_cell_execute=False`, the output is only written once at the end, after all cells have executed (or after error handling).

**Re-execution behavior:** If you re-run papermill on a notebook that was previously executed by papermill, it will find the existing `injected-parameters` cell and replace it with the new parameters. This is explicitly documented behavior.

**Source:** [papermill execute.py source](https://github.com/nteract/papermill/blob/main/papermill/execute.py), [Parameterize docs](https://papermill.readthedocs.io/en/latest/usage-parameterize.html)

---

### 3. Parameter Injection

**How it works:**
1. Designate a cell in the notebook with the tag `parameters` (via cell metadata: `"tags": ["parameters"]`).
2. This cell contains default values for parameters (e.g., `parquet_dir = "../data/quickstart/parquet"`).
3. When papermill executes, it inserts a NEW cell tagged `injected-parameters` immediately AFTER the `parameters` cell, containing only the overridden values.
4. The `parameters` cell still runs first (setting defaults), then the `injected-parameters` cell runs (overriding them).

**Tag requirement:** The cell must have `"parameters"` in its metadata tags array:
```json
"metadata": {
    "tags": ["parameters"]
}
```

**Can the parameter be a string path?** Yes. Papermill parameters support all JSON-serializable types: strings, numbers, booleans, lists, dicts. A string path is a perfectly valid parameter:
```python
# In the parameters cell:
parquet_dir = "../data/quickstart/parquet"  # default, will be overridden

# In the next cell:
from pathlib import Path
parquet_path = Path(parquet_dir)
```

**What happens to defaults?** The parameters cell runs first and sets the defaults. Then the injected-parameters cell runs and overwrites any values that were passed. Variables NOT overridden keep their default values.

**Caveat with inter-dependent parameters:** If the parameters cell has `a = 1; twice = a * 2`, and you override `a = 9`, `twice` will still be 2 (not 18) because `twice` was computed from the default `a` in the parameters cell and is not re-computed in the injected cell. For our use case this is not an issue since we only need a single `parquet_dir` string parameter.

**If no parameters cell exists:** The injected-parameters cell is inserted at the TOP of the notebook. This works but is less clean. It is better to explicitly create a parameters cell.

**Current notebook state:** Neither `raw_data_summary.ipynb` nor `data_verification.ipynb` currently has a `parameters` tag on any cell. This must be added as part of implementation.

**Source:** [Parameterize documentation](https://papermill.readthedocs.io/en/latest/usage-parameterize.html)

---

### 4. Recommended Path Resolution Pattern

**Strategy:** Pass an **absolute path** string as a papermill parameter from `quickstart.py` to each notebook. The notebooks receive this absolute path and use it directly. This makes the notebooks immune to working directory differences.

#### 4a. In `quickstart.py`: Resolve notebook paths using `__file__`

```python
from pathlib import Path

# Resolve the directory containing quickstart.py (SC2-gamestate-extractor/)
SCRIPT_DIR = Path(__file__).resolve().parent

# Notebook paths (relative to quickstart.py's location)
RAW_DATA_SUMMARY_NB = SCRIPT_DIR / "EDA" / "raw_data_summary.ipynb"
DATA_VERIFICATION_NB = SCRIPT_DIR / "EDA" / "data_verification.ipynb"
```

#### 4b. In `quickstart.py`: Resolve the data path to an absolute path

```python
# args.output is a relative path from the user's cwd (e.g., "data/quickstart")
# Path.resolve() converts it to an absolute path using the current cwd
parquet_dir_abs = (args.output / "parquet").resolve()

# Convert to string for papermill parameter injection
parquet_dir_str = str(parquet_dir_abs)
```

#### 4c. In `quickstart.py`: Execute with papermill

```python
import papermill as pm

def run_eda_notebooks(output_dir: Path):
    """Execute EDA notebooks with the resolved parquet directory path.

    Parameters:
        output_dir (Path): The --output argument from argparse (e.g., Path('data/quickstart')).
                           Will be resolved to an absolute path before injection.

    Depends on / calls:
        - papermill.execute_notebook()
        - RAW_DATA_SUMMARY_NB, DATA_VERIFICATION_NB (module-level constants)
    """
    # Resolve to absolute path so notebooks work regardless of cwd
    parquet_dir_abs = str((output_dir / "parquet").resolve())

    notebooks = [RAW_DATA_SUMMARY_NB, DATA_VERIFICATION_NB]

    for nb_path in notebooks:
        nb_path_str = str(nb_path)
        print(f"  Running EDA notebook: {nb_path.name}...")
        try:
            pm.execute_notebook(
                input_path=nb_path_str,
                output_path=nb_path_str,   # in-place execution
                parameters={"parquet_dir": parquet_dir_abs},
                cwd=str(nb_path.parent),   # set cwd to EDA/ directory
                kernel_name="python3",
            )
            print(f"  OK: {nb_path.name}")
        except pm.PapermillExecutionError as e:
            print(f"  FAILED: {nb_path.name}")
            print(f"    Error in cell [{e.exec_count}]: {e.ename}: {e.evalue}")
            # Notebook is already saved with error markers; continue to next
```

**Why `cwd=str(nb_path.parent)`?** While not strictly necessary when using absolute paths for data, setting `cwd` to the notebook's directory ensures that any OTHER relative paths in the notebook (e.g., relative imports, output file writes like the CSV export in `raw_data_summary.ipynb` cell 17) resolve correctly. This matches the behavior a user would get when running the notebook manually from JupyterLab.

**Why `kernel_name="python3"`?** Both notebooks have `"name": "python3"` in their kernelspec metadata. Explicitly passing it avoids potential issues if the kernel name in metadata drifts or if the environment has a different default. The `python3` kernel will use whatever Python executable is associated with that kernel spec (typically the current venv's Python if `ipykernel` is installed into the venv).

#### 4d. In the notebooks: Parameters cell

Each notebook needs a new parameters cell. Add as the FIRST code cell, tagged with `parameters`:

**`raw_data_summary.ipynb` -- new parameters cell:**
```python
# ---- Papermill parameters (defaults for interactive use) ----
# When run via papermill, these are overridden by injected values.
# When run manually in Jupyter, these defaults apply.
parquet_dir = "../data/quickstart/parquet"
```

**`data_verification.ipynb` -- new parameters cell:**
```python
# ---- Papermill parameters (defaults for interactive use) ----
# When run via papermill, these are overridden by injected values.
# When run manually in Jupyter, these defaults apply.
parquet_dir = "../../data/quickstart/parquet"
```

The default values preserve the current hardcoded relative paths so the notebooks still work when opened manually in Jupyter from their existing locations.

#### 4e. In the notebooks: Use the parameter

Replace all hardcoded path references with the `parquet_dir` variable (already defined in the parameters cell or injected by papermill):

```python
from pathlib import Path

parquet_path = Path(parquet_dir)
parquet_files = sorted(parquet_path.glob("*_game_state.parquet"))
```

#### 4f. Verification -- both invocation scenarios

**Scenario 1: Running from project root**
```bash
python SC2-gamestate-extractor/quickstart.py --output data/quickstart -EDA
```
- `__file__` resolves to `<project_root>/SC2-gamestate-extractor/quickstart.py`
- `SCRIPT_DIR` = `<project_root>/SC2-gamestate-extractor/`
- `RAW_DATA_SUMMARY_NB` = `<project_root>/SC2-gamestate-extractor/EDA/raw_data_summary.ipynb`
- `args.output` = `Path("data/quickstart")`, relative to cwd (project root)
- `parquet_dir_abs` = `<project_root>/data/quickstart/parquet` (absolute)
- `cwd` for notebook = `<project_root>/SC2-gamestate-extractor/EDA/`
- Result: Notebook receives absolute path, works correctly.

**Scenario 2: Running from submodule directory**
```bash
cd SC2-gamestate-extractor
python quickstart.py --output ../data/quickstart -EDA
```
- `__file__` resolves to `<project_root>/SC2-gamestate-extractor/quickstart.py`
- `SCRIPT_DIR` = `<project_root>/SC2-gamestate-extractor/`
- `RAW_DATA_SUMMARY_NB` = `<project_root>/SC2-gamestate-extractor/EDA/raw_data_summary.ipynb`
- `args.output` = `Path("../data/quickstart")`, relative to cwd (`SC2-gamestate-extractor/`)
- `(Path("../data/quickstart") / "parquet").resolve()` = `<project_root>/data/quickstart/parquet` (absolute)
- `cwd` for notebook = `<project_root>/SC2-gamestate-extractor/EDA/`
- Result: Same absolute path, works correctly.

Both scenarios produce identical absolute paths. The pattern is robust.

---

### 5. Kernel/Environment

**Default behavior:** Papermill reads the `kernelspec` from the notebook's metadata to determine which kernel to use. If `kernel_name` is explicitly passed to `execute_notebook()`, it overrides the metadata.

**Current notebook kernelspecs:**
- `raw_data_summary.ipynb`: `{"display_name": ".venv-3_11", "language": "python", "name": "python3"}`
- `data_verification.ipynb`: `{"display_name": "Python 3", "language": "python", "name": "python3"}`

Both use `"name": "python3"`, which is the standard Jupyter kernel for the current Python environment.

**Will it work in the same venv?** Yes, provided:
1. `ipykernel` is installed in the venv (`pip install ipykernel`)
2. The `python3` kernel is registered for the venv (usually automatic when `ipykernel` is installed)
3. `papermill` is installed in the venv (`pip install papermill`)

**Recommendation:** Add `papermill` and `ipykernel` to the project's requirements. Explicitly pass `kernel_name="python3"` in the `execute_notebook()` call for clarity and robustness.

**Source:** [Troubleshooting docs](https://papermill.readthedocs.io/en/latest/troubleshooting.html), [Issue #338](https://github.com/nteract/papermill/issues/338)

---

### 6. Error Handling

**Exception types raised by papermill:**

| Exception | When | Key Attributes |
|-----------|------|----------------|
| `PapermillExecutionError` | A cell raises an exception during execution | `cell_index`, `exec_count`, `source`, `ename`, `evalue`, `traceback` |
| `PapermillException` | General papermill operation failure | (base class) |
| `PapermillMissingParameterException` | A required parameter has no value | (base class) |
| `PapermillOptionalDependencyException` | An optional plugin is missing | (base class) |

**On execution error:**
1. Papermill writes the notebook to the output path with error markers (HTML anchors pointing to the failed cell)
2. Then raises `PapermillExecutionError`

**On kernel death (e.g., OOM):**
- CLI exits with status code 138
- Python API raises a `DeadKernelError` from `jupyter_client`

**Recommended error handling in `quickstart.py`:**

```python
from papermill.exceptions import PapermillExecutionError

try:
    pm.execute_notebook(...)
except PapermillExecutionError as e:
    print(f"Notebook execution failed at cell [{e.exec_count}]:")
    print(f"  {e.ename}: {e.evalue}")
    print(f"  The notebook has been saved with error details.")
    # Decide whether to continue to the next notebook or abort
except Exception as e:
    print(f"Unexpected error running notebook: {e}")
    # Handle kernel death, missing dependencies, etc.
```

**Source:** [papermill/exceptions.py](https://github.com/nteract/papermill/blob/main/papermill/exceptions.py), [Issue #464](https://github.com/nteract/papermill/issues/464), [Issue #344](https://github.com/nteract/papermill/issues/344)

---

## Recommended Implementation

### Step-by-step plan:

1. **Add `papermill` and `ipykernel` to project dependencies** (requirements.txt or pyproject.toml).

2. **Modify `raw_data_summary.ipynb`:**
   - Insert a new first code cell with the `parameters` tag containing: `parquet_dir = "../data/quickstart/parquet"`
   - In cell 3 (PyArrow schema inspection): replace `parquet_dir = Path("../data/quickstart/parquet")` with `parquet_path = Path(parquet_dir)` and update subsequent references
   - In cell 15 (`main()` function): replace `input_dir = Path("../data/quickstart/parquet")` with `input_dir = Path(parquet_dir)`
   - In cell 17 (ad-hoc pandas read): replace the hardcoded path with a path derived from `parquet_dir`

3. **Modify `data_verification.ipynb`:**
   - Insert a new first code cell (after the markdown header) with the `parameters` tag containing: `parquet_dir = "../../data/quickstart/parquet"`
   - In cell 3 (auto-discover): replace `parquet_dir = Path("../../data/quickstart/parquet")` with `parquet_path = Path(parquet_dir)` and rename variable usage downstream

4. **Modify `quickstart.py`:**
   - Add `-EDA` / `--run-eda` argument to argparse
   - Add `run_eda_notebooks()` function (as shown in section 4c above)
   - Call it at the appropriate point in the `main()` flow (after processing/downloading completes, before dataset upload)

5. **Parameter name:** Use `parquet_dir` (string) as the single shared parameter name across both notebooks.

6. **Path resolution in `quickstart.py`:**
   ```python
   SCRIPT_DIR = Path(__file__).resolve().parent
   RAW_DATA_SUMMARY_NB = SCRIPT_DIR / "EDA" / "raw_data_summary.ipynb"
   DATA_VERIFICATION_NB = SCRIPT_DIR / "EDA" / "data_verification.ipynb"

   # In the -EDA handler:
   parquet_dir_abs = str((args.output / "parquet").resolve())
   ```

---

## All Hardcoded Paths Found in Notebooks

### `raw_data_summary.ipynb`

| Cell | Line | Hardcoded Path | Context |
|------|------|---------------|---------|
| Cell 3 (code) | `parquet_dir = Path("../data/quickstart/parquet")` | `../data/quickstart/parquet` | PyArrow schema inspection -- reads parquet files |
| Cell 15 (code, `main()`) | `input_dir = Path("../data/quickstart/parquet")` | `../data/quickstart/parquet` | Main profiling function -- reads parquet files |
| Cell 17 (code) | `pd.read_parquet("../data\quickstart\parquet\match_4184393_game_state.parquet")` | `../data\quickstart\parquet\match_4184393_game_state.parquet` | Ad-hoc single-file read (also has Windows backslash path issue) |
| Cell 17 (code) | `df.to_csv("match_4184393_game_state.csv", index=False)` | `match_4184393_game_state.csv` | Writes CSV to cwd (not a parquet input path, but a relative output) |

**Note:** Cell 17 has a hardcoded specific filename (`match_4184393_game_state.parquet`) and writes a CSV output to cwd. This cell appears to be an ad-hoc exploration cell, not part of the main analysis. Consider whether to keep, parameterize, or remove it.

### `data_verification.ipynb`

| Cell | Line | Hardcoded Path | Context |
|------|------|---------------|---------|
| Cell 3 (code) | `parquet_dir = Path("../../data/quickstart/parquet")` | `../../data/quickstart/parquet` | Auto-discover parquet files and load first file |

**Note:** `data_verification.ipynb` has only ONE hardcoded path reference. All subsequent data access goes through `df` (the loaded DataFrame) and `entity_catalog` (derived from `df`), so parameterizing `parquet_dir` in cell 3 covers the entire notebook.

---

## Risks and Caveats

1. **In-place overwrite on failure:** If a notebook fails mid-execution, the in-place output will contain a partially-executed notebook with error markers. The original "clean" notebook is lost. This is acceptable for our use case (notebooks are generated output, not source code), but consider adding a git-based recovery note in the CLI output.

2. **Thread safety of `cwd`:** The `cwd` parameter in papermill uses `os.chdir()`, which is process-global. If `quickstart.py` ever runs notebooks in parallel (e.g., via threads), `cwd` will cause race conditions. The current design executes notebooks sequentially, so this is not an issue. If parallelism is added later, either remove `cwd` (relying on absolute paths alone) or use separate processes.

3. **Kernel availability:** The `python3` kernel must be installed and registered in the environment. If the user is in a venv without `ipykernel`, execution will fail with a `NoSuchKernel` error. The error message from papermill is not always clear about this. Add a pre-flight check or helpful error message.

4. **Cell 17 in `raw_data_summary.ipynb`:** Contains a hardcoded specific filename (`match_4184393_game_state.parquet`) and writes a CSV to cwd. This cell will fail if that specific file doesn't exist. Options:
   - Remove the cell (it's ad-hoc exploration)
   - Guard it with a try/except
   - Skip it in papermill execution (not easily done without restructuring)

5. **Notebook output size:** Executed notebooks contain all cell outputs (including matplotlib figures as base64 PNG). This can make the `.ipynb` files very large. This is normal for executed notebooks but may affect git diff readability.

6. **Display name mismatch in `raw_data_summary.ipynb`:** The kernelspec has `"display_name": ".venv-3_11"` but `"name": "python3"`. The `name` field is what papermill uses, so this works, but the display name may confuse users opening the notebook in Jupyter.

---

## Uncertainty Flag

**All key questions have been resolved with source-code-level evidence. No uncertainties remain.**

Specifically:
- **Working directory:** Confirmed via source code that `cwd=None` is a no-op (notebook runs in caller's cwd). The `chdir` context manager source code is unambiguous.
- **In-place execution:** Confirmed safe via source code: `load_notebook_node()` reads fully into memory before any writes to `output_path`.
- **Parameter injection:** Confirmed via official documentation and source code.
- **Path resolution pattern:** Verified algebraically for both invocation scenarios (project root and submodule directory). Uses only `__file__`, `Path.resolve()`, and `Path.parent` -- no hardcoded absolute paths.
- **Kernel behavior:** Confirmed via source code and documentation that `kernel_name` falls back to notebook metadata `kernelspec.name`.
- **Error handling:** Confirmed exception types via source code of `exceptions.py`.

---

## Sources

- [papermill/execute.py (source)](https://github.com/nteract/papermill/blob/main/papermill/execute.py)
- [papermill/utils.py (source)](https://github.com/nteract/papermill/blob/main/papermill/utils.py)
- [papermill/exceptions.py (source)](https://github.com/nteract/papermill/blob/main/papermill/exceptions.py)
- [Parameterize documentation](https://papermill.readthedocs.io/en/latest/usage-parameterize.html)
- [Execute documentation](https://papermill.readthedocs.io/en/latest/usage-execute.html)
- [CLI documentation](https://papermill.readthedocs.io/en/latest/usage-cli.html)
- [Troubleshooting documentation](https://papermill.readthedocs.io/en/latest/troubleshooting.html)
- [Issue #268 -- cwd behavior](https://github.com/nteract/papermill/issues/268)
- [Issue #473 -- thread safety of cwd](https://github.com/nteract/papermill/issues/473)
- [Issue #338 -- default kernel inference](https://github.com/nteract/papermill/issues/338)
- [Issue #344 -- error handling](https://github.com/nteract/papermill/issues/344)
- [Issue #464 -- execution stops on exceptions](https://github.com/nteract/papermill/issues/464)
