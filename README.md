# A-Maze-ing

A project about generating labyrinths.

## Reusable `mazegen` module

The generator is also available as a standalone Python package. From the
repository root, create a virtual environment and build the package from its
source files with:

```bash
python3 -m venv venv
source venv/bin/activate
pip install build
python -m build
cp dist/mazegen-1.0.0-py3-none-any.whl .
```

Install the wheel in another project with
`python -m pip install mazegen-1.0.0-py3-none-any.whl`.

Create a generator and generate a maze. The default entry is the upper-left
cell and the default exit is the lower-right cell:

```python
from mazegen import MazeGenerator

generator = MazeGenerator(width=15, height=11)
generator.generate()

# Cell objects, including their north/east/south/west wall flags.
grid = generator.grid

# Ordered (x, y) coordinates from entry to exit.
solution = generator.find_path()
# Equivalent interfaces:
solution = generator.solution
solution = generator.solve()

# Integer wall masks, one row per maze row.
maze = generator.maze
# Equivalent: maze = generator.get_maze()
```

Pass custom dimensions and a seed to the constructor:

```python
generator = MazeGenerator(
    width=20,
    height=20,
    seed=42,
)
generator.generate()
```

You can also pass `entry=(x, y)` and `exit=(x, y)` to choose different
endpoints. Dimensions must be at least 9 by 7 to fit the protected 42 pattern.
Use `generate_imperfect()` for an imperfect maze. A seed makes repeated
generation reproducible; omit it for a fresh random maze.

`generator.maze` contains rows of integer wall masks, and
`generator.get_maze()` returns a copy of that structure. Bits 0, 1, 2, and 3
indicate north, east, south, and west walls. The detailed `generator.grid`
representation is also available as `Cell` objects. These structures are
independent of the text output format.

The distribution includes the MIT license in `LICENSE.md`.
