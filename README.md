*This project has been created as part of the 42 curriculum by dboldino, denibyko.*

# A-Maze-ing

## Description

**A-Maze-ing** is a maze generator and viewer written in Python 3.10+.

The program reads a configuration file, generates a maze of the requested size, writes it to an output file in a compact hexadecimal format, and displays it in a graphical window where you can walk through it, show or hide the shortest solution, regenerate the maze and switch colour themes.

Main features:

- Perfect mazes (exactly one path between any two cells) and imperfect mazes (loops, no dead ends).
- Reproducible mazes through an optional `SEED`.
- A "42" pattern drawn with fully closed cells in the middle of the maze (omitted if the maze is too small).
- Strict validation of the configuration file with clear error messages.
- Shortest path from entry to exit (BFS), written to the output file.
- MLX graphical renderer with walking player, path toggle, 3 colour themes, clickable buttons and a "Generating..." spinner popup.
- The generator is packaged as a standalone, reusable Python package (`mazegen`), described [below](#reusable-module-mazegen).

## Instructions

### Requirements

- Python 3.10 or later
- The MLX wheel `mlx-2.2-py3-none-any.whl` located in the project root (already included in the repository)
- `flake8` and `mypy` (installed by `make install`, only needed for linting)

### Installation

The program refuses to start outside a virtual environment, so create one first:

```bash
python3 -m venv venv
source venv/bin/activate
make install
```

`make install` installs `flake8`, `mypy` and the MLX wheel.

### Execution

```bash
make run
```

which is equivalent to:

```bash
python3 src/a_maze_ing.py configs/config.txt
```

The maze is printed in the terminal, written to `OUTPUT_FILE`, and then shown in the graphical window. If MLX is not installed, the maze is still generated and written to the output file, and a message explains how to enable the display.

### Makefile rules

| Rule | Description |
|------|-------------|
| `make install` | Install `flake8`, `mypy` and the MLX wheel |
| `make run` | Run the program with `configs/config.txt` |
| `make debug` | Run the program under `pdb` |
| `make lint` | Run `flake8` and `mypy` with the standard flags |
| `make lint-strict` | Run `flake8` and `mypy --strict` |
| `make clean` | Remove `__pycache__`, `.mypy_cache` and generated `output/*.txt` files |

### Controls

| Key | Button | Action |
|-----|--------|--------|
| Arrow keys | – | Move the player (walls block the movement) |
| `SPACE` | Regenerate | Generate a new maze (the same maze if `SEED` is set) |
| `V` | Path | Show / hide the shortest path |
| `C` | Colors | Switch theme (Classic → Ocean → Sunset) |
| `ESC` | – | Quit |

The buttons can also be clicked with the mouse. The maximum size that can be displayed is 120 × 120 cells, with `WIDTH + HEIGHT` at most 160.

## Config file

### Format

The configuration file is a plain text file with one `KEY=VALUE` pair per line.

- Empty lines and lines starting with `#` are ignored.
- Spaces around keys and values are ignored, and values may be wrapped in single or double quotes.
- A key may appear only once.
- Keys are case-sensitive, boolean values are not (`True`, `true`, `FALSE`...).

### Keys

| Key | Required | Type | Description | Example |
|-----|----------|------|-------------|---------|
| `WIDTH` | yes | integer ≥ 1 | Number of cells in each row | `WIDTH=20` |
| `HEIGHT` | yes | integer ≥ 1 | Number of cells in each column | `HEIGHT=15` |
| `ENTRY` | yes | `x,y` | Entry cell, must be inside the maze | `ENTRY=0,0` |
| `EXIT` | yes | `x,y` | Exit cell, inside the maze and different from `ENTRY` | `EXIT=19,14` |
| `OUTPUT_FILE` | yes | path | File where the maze is written (missing directories are created) | `OUTPUT_FILE=output/maze.txt` |
| `PERFECT` | yes | `True` / `False` | `True`: perfect maze, `False`: imperfect maze with loops | `PERFECT=False` |
| `SEED` | no | integer | Seed for reproducible generation. Without it, every run gives a new maze | `SEED=42` |

Coordinates are `(x, y)` with the origin `(0, 0)` in the upper-left corner, `x` growing to the right and `y` growing downwards. `ENTRY` and `EXIT` must not be on a cell of the "42" pattern.

### Example

```text
# Maze size
WIDTH=20
HEIGHT=20

# Entry and exit coordinates
ENTRY=0,0
EXIT=19,19

OUTPUT_FILE=output/maze.txt
PERFECT=False
# SEED=42
```

Any invalid value (missing key, non-integer, coordinate outside the maze, duplicated key...) stops the program with a `Configuration Error` message that names the faulty key or line.

### Output file format

The output file contains one hexadecimal digit per cell, one row of the maze per line. Each digit encodes the closed walls of the cell, with a set bit meaning a closed wall:

| Bit | 0 | 1 | 2 | 3 |
|-----|---|---|---|---|
| Wall | North | East | South | West |

After the grid come an empty line, the entry coordinates, the exit coordinates, and the shortest path as a string of `N`, `E`, `S`, `W` letters. Example (10 × 8 maze):

```text
d555395553
93fbaafffa
aefc4457fa
83fffbfffa
ac53fafd52
c3bafafffa
baac14793a
c447c556c6

0,0
9,7
EEEESSENNEEEESSSSSSS
```

The "42" pattern cells are the fully closed ones (`f`). The renderer validates this file when loading it: ragged rows, invalid digits, a path that crosses a wall or a path that does not end at the exit are all reported as errors.

## Maze generation algorithm

### Algorithm

The maze is generated with the **recursive backtracker** (randomized depth-first search), implemented iteratively with an explicit stack:

1. Start from the entry cell and mark it as visited.
2. Look at the unvisited neighbours of the cell on top of the stack, ignoring the cells of the "42" pattern.
3. If there are some, pick one at random, remove the wall between the two cells, mark the neighbour as visited and push it.
4. Otherwise, pop the stack (backtrack).
5. Stop when the stack is empty.

This produces a **perfect maze**: a spanning tree of the grid in which every reachable cell is connected by exactly one path.

For `PERFECT=False`, the same perfect maze is generated first, then every dead end (a cell with a single opening) is visited in random order and one of its walls is removed (never a wall of the "42" pattern). This creates loops and removes dead ends, so several paths exist between entry and exit.

The solution path is always found with a **breadth-first search**, which guarantees the shortest path, including in imperfect mazes.

### Why this algorithm

- It is simple to implement, to read and to test, and it is easy to guarantee that the result is a perfect maze.
- It generates long, winding corridors with few short branches, which gives mazes that are interesting to solve.
- Marking the "42" cells as blocked is enough to keep them closed, and the maze stays fully connected around them.
- The iterative version has no recursion limit, so big mazes (up to the 120 × 120 limit of the renderer) are generated without any problem.
- Starting the carving from the entry makes it easy to build the imperfect variant on top of the perfect one.

## Reusable code

- **`mazegen` package** (`src/mazegen/`): the whole generation logic (`MazeGenerator`, `Cell`) has no dependency on the rest of the project. It can be built into a wheel and installed in any other Python project, see [Reusable module: mazegen](#reusable-module-mazegen) below. It can generate perfect or imperfect mazes, solve them, and export them to the hexadecimal format.
- **`MazeFileParser`** (`src/maze_parser.py`): reads and validates the output file format into a `MazeData` object. It can be used by any tool that needs to read a maze file.
- **Configuration parsing** (`src/a_maze_ing.py`): `load_config` and `validate_config` are independent from the generator and can be reused for other `KEY=VALUE` configuration files with a different set of keys.
- **`MazeRenderer`** (`src/renderer.py`): only needs a validated config and an optional `regenerate` callback, so it can display any maze file in the output format. Layout values (`RenderConfig`) and colour palettes (`themes.py`) are separate from the drawing code, which makes it simple to add a theme or change the layout.

## Team and project management

### Roles

| Member | Responsibilities |
|--------|------------------|
| **dboldino** | Graphical renderer (MLX window, UI panel, player, themes, spinner popup), configuration files, Makefile |
| **denibyko** | Maze generation (perfect and imperfect), BFS solver, output file writer, configuration parsing and validation, "42" pattern, `mazegen` package and its documentation |

### Planning and how it evolved

The first plan was to work in parallel on two independent parts: the generator on one side and the renderer on the other, joined through the output file format defined by the subject. The Git history shows how it went:

1. **Week 1 (11–16 Oct)**: repository setup, basic perfect maze generation, then path finding, console display and a first version of the config validation.
2. **Week 2 (23–26 Oct)**: validation merged into the main branch, generator ready for testing; the renderer was developed on its own branch.
3. **26 Oct**: renderer merged with the generator and project restructured into `src/`, with a dedicated parser for the output file so the renderer only depends on the file format.
4. **27–28 Oct**: code reusability requirements (`mazegen` package, `pyproject.toml`, wheel), then the spinner popup and the path toggle.
5. **31 Oct**: final cleanup, linting and documentation.

The main change from the initial plan was the integration step: the renderer started with its own config handling, and we decided to derive a small `RenderConfig` from the base config instead of parsing the file twice. The reusable package was also planned late and ended up requiring a restructuring of the files.

### What worked well and what could be improved

**What worked well**

- Agreeing early on the output file format let both of us work independently, and the integration only needed a parser on the renderer side.
- Working with feature branches and pull requests kept the main branch working and made every change visible before it was merged.
- Strict validation and clear error messages made debugging configs much faster.
- Keeping the generator free of project-specific imports made the packaging easy.

**What could be improved**

- Plan the package structure and the integration earlier, to avoid the restructuring of the project in the middle of the work.
- Add automated tests (for example, check that every generated maze is perfect or fully connected for many seeds and sizes).
- Add more generation algorithms and let the user choose one in the config file.
- Make the display settings (theme, cell size) configurable from the config file.

### Tools used

- **Git and GitHub**: version control, feature branches, pull requests.
- **Python virtual environments**, `pip`, `setuptools` and `build`: dependencies and packaging of `mazegen`.
- **Make**: install, run, debug, lint and clean rules.
- **flake8** and **mypy**: code style and static typing checks.
- **MLX** (Python wheel provided by the 42 subject): graphical display.
- **pdb**: debugging.

## Resources

### References

- [Maze generation algorithm (Wikipedia)](https://en.wikipedia.org/wiki/Maze_generation_algorithm)
- [Think Labyrinth: Maze algorithms (Walter D. Pullen)](https://www.astrolog.org/labyrnth/algrithm.htm)
- [Maze generation: Recursive backtracking (Jamis Buck)](https://weblog.jamisbuck.org/2010/12/27/maze-generation-recursive-backtracking)
- [Breadth-first search (Wikipedia)](https://en.wikipedia.org/wiki/Breadth-first_search)
- [Python documentation: `random`, `dataclasses`, `typing`](https://docs.python.org/3/)
- [Python Packaging User Guide: packaging projects, `pyproject.toml`](https://packaging.python.org/)
- [setuptools documentation](https://setuptools.pypa.io/)
- [PEP 8](https://peps.python.org/pep-0008/), [PEP 257](https://peps.python.org/pep-0257/) and [mypy documentation](https://mypy.readthedocs.io/)

### Use of AI

AI was used as a development and documentation aid for this project. The source code itself remains the responsibility of the project author. AI was not used as a substitute for understanding the implementation or for validating the behaviour of the submitted code.

## Reusable module: mazegen

The standalone package documentation is also available on its own in [README_mazegen.md](README_mazegen.md), which is the description shipped inside the wheel.

The maze generator is also distributed as a standalone Python package named mazegen.

The package can be built into a standard Python Wheel (.whl) and then installed and reused in other Python projects without copying the source files.

### Building the package

The package is configured using pyproject.toml. It uses setuptools as the build backend.

The project should have the following structure:

```text
project/
├── pyproject.toml
├── README.md
├── LICENSE.md
└── src/
    └── mazegen/
        ├── __init__.py
        └── maze_generator.py
```

#### 1. Create a virtual environment

From the project root:

```bash
python3 -m venv venv
```

Activate it:

```bash
source venv/bin/activate
```

#### 2. Install the Python build tool

```bash
python -m pip install build
```

The build package is used to build distributable Python packages from pyproject.toml.

#### 3. Build the package

Run:

```bash
python -m build --wheel
```

The build process creates a dist/ directory containing distribution files:

```text
dist/
└── mazegen-1.0.0-py3-none-any.whl
```

The .whl file is the ready-to-install binary distribution of the package. It can be copied to another project and installed there.

### Installing the package in another project

Copy the wheel:

```text
mazegen-1.0.0-py3-none-any.whl
```

to the project where you want to use the generator.

Create and activate a virtual environment if necessary:

```bash
python3 -m venv venv
source venv/bin/activate
```

Install the wheel:

```bash
python -m pip install mazegen-1.0.0-py3-none-any.whl
```

After installation, the package can be imported normally:

```python
from mazegen import MazeGenerator
```

You do not need to copy maze_generator.py into the new project.

### Basic usage

Create a generator:

```python
from mazegen import MazeGenerator

generator = MazeGenerator(
    width=15,
    height=11,
    entry=(0,0),
    exit_=(9,9),
    seed=42,
)
```

Generate a perfect maze:

```python
generator.generate_perfect()
```

Find a path from the entry to the exit:

```python
path = generator.find_path()
```

Print the maze:

```python
generator.print_maze(path)
```

A complete example:

```python
from mazegen import MazeGenerator


generator = MazeGenerator(
    width=15,
    height=11,
    entry=(0,0),
    exit_=(9,9),
    seed=42,
)

generator.generate_perfect()

path = generator.find_path()

generator.print_maze(path)
```