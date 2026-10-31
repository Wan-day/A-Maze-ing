"""Reusable maze generation module with no project-specific dependencies."""

import random


class Cell:
    """Represent one maze cell and its four walls."""
    def __init__(self) -> None:
        """Initialize a cell with all walls closed."""
        self.north = True
        self.east = True
        self.south = True
        self.west = True
        self.visited = False


class MazeGenerator:
    """Generate, inspect, solve, and export a maze.

    Coordinates are ``(x, y)`` with the origin at the upper-left corner.
    The generated cell objects are available through :attr:`grid`.
    """
    def __init__(
            self, width: int, height: int,
            entry: tuple[int, int] | None = None,
            exit_: tuple[int, int] | None = None,
            seed: int | None = None,
    ) -> None:
        """Initialize a maze with dimensions and entry/exit cells.

        Args:
            width: Number of cells in each row.
            height: Number of cells in each column.
            entry: Entry coordinates as (x, y), defaults to the upper-left.
            exit_: Exit coordinates as (x, y), defaults to the lower-right.
            seed: Optional seed for reproducible generation.
        """
        if entry is None:
            entry = (0, 0)
        if exit_ is None:
            exit_ = (width - 1, height - 1)
        if width < 1 or height < 1:
            raise ValueError("Maze dimensions must be greater than 0")
        for name, (x, y) in (("entry", entry), ("exit", exit_)):
            if not (0 <= x < width and 0 <= y < height):
                raise ValueError(f"{name} coordinate is outside maze bounds")
        if entry == exit_:
            raise ValueError("Entry and exit must be different")
        if width < 9 or height < 7:
            print("42 was omitted because the maze is too small")
        self.width = width
        self.height = height
        self.entry = entry
        self.exit = exit_
        self.seed = seed
        self.grid = [
            [Cell() for _ in range(width)]
            for _ in range(height)
        ]
        self.maze: list[list[int]] = self.get_maze()
        self.solution: list[tuple[int, int]] = []

    def generate(self) -> None:
        """Generate an imperfect maze using the configured seed, if any."""
        self.generate_imperfect(self.seed)

    def cell_to_hex(self, cell: Cell) -> str:
        """Convert a cell wall configuration to one hexadecimal digit.

        Args:
            cell: Cell whose walls should be converted.

        Returns:
            A hexadecimal character representing the cell walls.
        """
        return format(self.cell_to_int(cell), "x")

    def cell_to_int(self, cell: Cell) -> int:
        """Return a cell's wall configuration as a four-bit integer.

        Bits 0 through 3 represent the north, east, south, and west walls.
        """
        value = 0
        if cell.north:
            value |= 1
        if cell.east:
            value |= 2
        if cell.south:
            value |= 4
        if cell.west:
            value |= 8
        return value

    def get_maze(self) -> list[list[int]]:
        """Return the maze structure as a new list of wall-mask rows.

        Each cell integer uses bit 0 for north, bit 1 for east, bit 2 for
        south, and bit 3 for west. The returned lists can be modified without
        changing the generator's internal grid.
        """
        return [
            [self.cell_to_int(cell) for cell in row]
            for row in self.grid
        ]

    def to_hex(self) -> list[str]:
        """Convert the entire maze to hexadecimal rows.

        Returns:
            A list containing one hexadecimal string for each maze row.
        """
        result = []
        for y in range(self.height):
            row = ""
            for x in range(self.width):
                row += self.cell_to_hex(self.grid[y][x])
            result.append(row)
        return result

    def path_to_directions(self, path: list[tuple[int, int]]) -> str:
        """Convert a coordinate path to movement directions.

        Args:
            path: Ordered coordinates from entry to exit.

        Returns:
            A string containing E, W, S, and N movement directions.
        """
        result = ""
        for i in range(1, len(path)):
            x1, y1 = path[i - 1]
            x2, y2 = path[i]
            if x2 == x1 + 1:
                result += "E"
            elif x2 == x1 - 1:
                result += "W"
            elif y2 == y1 + 1:
                result += "S"
            elif y2 == y1 - 1:
                result += "N"
        return result

    def write_output(self, filename: str, path: list[tuple[int, int]]) -> None:
        """Write the maze, entry, exit, and path to a file.

        Args:
            filename: Path of the output file.
            path: Ordered coordinates forming the solution path.
        """
        hex_maze = self.to_hex()
        directions = self.path_to_directions(path)
        with open(filename, "w", encoding="utf-8") as file:
            for row in hex_maze:
                file.write(row + "\n")
            file.write("\n")
            file.write(f"{self.entry[0]},{self.entry[1]}\n")
            file.write(f"{self.exit[0]},{self.exit[1]}\n")
            file.write(directions + "\n")

    def find_path(self) -> list[tuple[int, int]]:
        """Find the shortest path from entry to exit using BFS.

        Returns:
            The shortest path as a list of coordinates.
            Returns an empty list if the exit is unreachable.
        """
        queue = [self.entry]
        visited = {self.entry}
        parent = {}
        index = 0
        while index < len(queue):
            x, y = queue[index]
            index += 1
            if (x, y) == self.exit:
                break
            cell = self.grid[y][x]
            if not cell.north and y > 0:
                neighbor = (x, y - 1)
                if neighbor not in visited:
                    visited.add(neighbor)
                    parent[neighbor] = (x, y)
                    queue.append(neighbor)
            if not cell.east and x < self.width - 1:
                neighbor = (x + 1, y)
                if neighbor not in visited:
                    visited.add(neighbor)
                    parent[neighbor] = (x, y)
                    queue.append(neighbor)
            if not cell.south and y < self.height - 1:
                neighbor = (x, y + 1)
                if neighbor not in visited:
                    visited.add(neighbor)
                    parent[neighbor] = (x, y)
                    queue.append(neighbor)
            if not cell.west and x > 0:
                neighbor = (x - 1, y)
                if neighbor not in visited:
                    visited.add(neighbor)
                    parent[neighbor] = (x, y)
                    queue.append(neighbor)
        if self.exit not in visited:
            return []
        current = self.exit
        path = []
        while current != self.entry:
            path.append(current)
            current = parent[current]
        path.append(self.entry)
        path.reverse()
        return path

    def solve(self) -> list[tuple[int, int]]:
        """Return the shortest path from entry to exit."""
        return self.find_path()

    def remove_wall(
        self, x1: int, y1: int, x2: int, y2: int,
        blocked: set[tuple[int, int]],
    ) -> None:
        """Remove the wall between two adjacent cells.

        Cells belonging to the 42 pattern are protected.

        Args:
            x1: X coordinate of the first cell.
            y1: Y coordinate of the first cell.
            x2: X coordinate of the second cell.
            y2: Y coordinate of the second cell.
            blocked: Coordinates that must remain closed, such as the 42
                pattern cells.
        """
        if (x1, y1) in blocked or (x2, y2) in blocked:
            return
        current = self.grid[y1][x1]
        neighbor = self.grid[y2][x2]
        if x2 == x1 + 1:
            current.east = False
            neighbor.west = False
        elif x2 == x1 - 1:
            current.west = False
            neighbor.east = False
        elif y2 == y1 - 1:
            current.north = False
            neighbor.south = False
        elif y2 == y1 + 1:
            current.south = False
            neighbor.north = False

    def get_pattern_42(self) -> dict[tuple[int, int], str]:
        """Return the coordinates occupied by the 42 pattern.

        Returns:
            A mapping of pattern coordinates to the character 4 or 2.
        """
        pattern = [
            "4   222",
            "4     2",
            "444 222",
            "  4 2  ",
            "  4 222",
        ]
        pattern_height = len(pattern)
        pattern_width = len(pattern[0])
        # Pattern plus a one-cell margin must fit, otherwise 42 is omitted.
        if (self.width < pattern_width + 2
                or self.height < pattern_height + 2):
            return {}
        # Rounding up moves the pattern towards the right edge when the
        # width is even, so the maze centre never falls inside the "42".
        start_x = (self.width - pattern_width + 1) // 2
        start_y = (self.height - pattern_height) // 2
        result = {}
        for y in range(pattern_height):
            for x in range(pattern_width):
                if pattern[y][x] in ("4", "2"):
                    result[(start_x + x, start_y + y)] = pattern[y][x]
        return result

    def get_neighbors(
        self, x: int, y: int, blocked: set[tuple[int, int]]
    ) -> list[tuple[int, int]]:
        """Find unvisited neighboring cells that are not blocked.

        Args:
            x: X coordinate of the current cell.
            y: Y coordinate of the current cell.
            blocked: Coordinates that cannot be entered.

        Returns:
            A list of available neighboring coordinates.
        """
        neighbors = []
        if y > 0:
            nx, ny = x, y - 1
            if not self.grid[ny][nx].visited and (nx, ny) not in blocked:
                neighbors.append((nx, ny))
        if x < self.width - 1:
            nx, ny = x + 1, y
            if not self.grid[ny][nx].visited and (nx, ny) not in blocked:
                neighbors.append((nx, ny))
        if y < self.height - 1:
            nx, ny = x, y + 1
            if not self.grid[ny][nx].visited and (nx, ny) not in blocked:
                neighbors.append((nx, ny))
        if x > 0:
            nx, ny = x - 1, y
            if not self.grid[ny][nx].visited and (nx, ny) not in blocked:
                neighbors.append((nx, ny))
        return neighbors

    def passage_count(self, x: int, y: int) -> int:
        """Count open passages connected to a cell.

        Args:
            x: X coordinate of the cell.
            y: Y coordinate of the cell.

        Returns:
            The number of open passages.
        """
        cell = self.grid[y][x]
        count = 0
        if not cell.north and y > 0:
            count += 1
        if not cell.east and x < self.width - 1:
            count += 1
        if not cell.south and y < self.height - 1:
            count += 1
        if not cell.west and x > 0:
            count += 1
        return count

    def get_dead_ends(
            self, pattern: set[tuple[int, int]]
    ) -> list[tuple[int, int]]:
        """Find non-pattern cells with exactly one open passage.

        Args:
            pattern: Coordinates occupied by the 42 pattern.

        Returns:
            A list of dead-end cell coordinates.
        """
        dead_ends = []
        for y in range(self.height):
            for x in range(self.width):
                if (x, y) in pattern:
                    continue
                if self.passage_count(x, y) == 1:
                    dead_ends.append((x, y))
        return dead_ends

    def generate_imperfect(self, seed: int | None = None) -> None:
        """Generate an imperfect maze by opening additional walls.

        The method first generates a perfect maze and then removes
        additional walls where possible to eliminate dead ends.

        Args:
            seed: Optional random seed for reproducible generation.
        """
        if seed is None:
            seed = self.seed
        self.generate_perfect(seed)
        pattern = self.get_pattern_42()
        blocked = set(pattern)
        dead_ends = self.get_dead_ends(blocked)
        random.shuffle(dead_ends)
        for x, y in dead_ends:
            if self.passage_count(x, y) != 1:
                continue
            cell = self.grid[y][x]
            neighbors = []
            if y > 0 and (x, y - 1) not in blocked and cell.north:
                neighbors.append((x, y - 1))
            if (x < self.width - 1
                    and (x + 1, y) not in blocked
                    and cell.east):
                neighbors.append((x + 1, y))
            if (y < self.height - 1
                    and (x, y + 1) not in blocked
                    and cell.south):
                neighbors.append((x, y + 1))
            if x > 0 and (x - 1, y) not in blocked and cell.west:
                neighbors.append((x - 1, y))
            if neighbors:
                nx, ny = random.choice(neighbors)
                self.remove_wall(x, y, nx, ny, blocked)
        self.maze = self.get_maze()
        self.solution = self.find_path()

    def generate_perfect(self, seed: int | None = None) -> None:
        """Generate a perfect maze using recursive backtracking.

        Args:
            seed: Optional random seed for reproducible generation.

        Raises:
            ValueError: If entry or exit is inside the 42 pattern.
        """
        if seed is None:
            seed = self.seed
        pattern = self.get_pattern_42()
        blocked = set(pattern)
        if self.entry in blocked:
            raise ValueError("Entry cannot be inside 42 pattern")
        if self.exit in blocked:
            raise ValueError("Exit cannot be inside 42 pattern")
        if seed is not None:
            random.seed(seed)
        self.grid = [
            [Cell() for _ in range(self.width)]
            for _ in range(self.height)
        ]
        x, y = self.entry
        stack = [(x, y)]
        self.grid[y][x].visited = True
        while stack:
            x, y = stack[-1]
            neighbors = self.get_neighbors(x, y, blocked)
            if neighbors:
                nx, ny = random.choice(neighbors)
                self.remove_wall(x, y, nx, ny, blocked)
                self.grid[ny][nx].visited = True
                stack.append((nx, ny))
            else:
                stack.pop()
        self.maze = self.get_maze()
        self.solution = self.find_path()

    def print_maze(self, path: list[tuple[int, int]]) -> None:
        """Print the maze and the solution path to the console.

        Args:
            path: Ordered coordinates forming the solution path.
        """
        path_set = set(path)
        pattern = self.get_pattern_42()
        for y in range(self.height):
            for x in range(self.width):
                print("+", end="")
                if self.grid[y][x].north:
                    print("---", end="")
                else:
                    print("   ", end="")
            print("+")
            for x in range(self.width):
                if self.grid[y][x].west:
                    print("|", end="")
                else:
                    print(" ", end="")
                if (x, y) == self.entry:
                    print(" E ", end="")
                elif (x, y) == self.exit:
                    print(" X ", end="")
                elif (x, y) in pattern:
                    print(f" {pattern[(x, y)]} ", end="")
                elif (x, y) in path_set:
                    print(" * ", end="")
                else:
                    print("   ", end="")
            if self.grid[y][self.width - 1].east:
                print("|")
            else:
                print(" ")
        for x in range(self.width):
            print("+", end="")
            if self.grid[self.height - 1][x].south:
                print("---", end="")
            else:
                print("   ", end="")
        print("+")
