*This project has been created as part of the 42 curriculum by dboldino, denibyko.*

# Reusable mazegen package

The maze generator is also distributed as a standalone Python package named mazegen.

The package can be built into a standard Python Wheel (.whl) and then installed and reused in other Python projects without copying the source files.

## Building the package

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

### 1. Create a virtual environment

From the project root:

```bash
python3 -m venv venv
```

Activate it:

```bash
source venv/bin/activate
```

### 2. Install the Python build tool

```bash
python -m pip install build
```

The build package is used to build distributable Python packages from pyproject.toml.

### 3. Build the package

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

## Installing the package in another project

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

## Basic usage

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
