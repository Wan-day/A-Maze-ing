import random
from errors import ConfigError


class Cell:
    """Represent one maze cell and its four walls."""
    def __init__(self) -> None:
        """Initialize a cell with all walls closed."""
        self.north = True
        self.east = True
        self.south = True
        self.west = True
        self.visited = False


class Maze:
    """Represent a maze grid and provide generation and path utilities."""
    def __init__(
            self, width: int, height: int, entry: tuple[int, int],
            exit: tuple[int, int]
    ) -> None:
        """Initialize a maze with dimensions and entry/exit cells.

        Args:
            width: Number of cells in each row.
            height: Number of cells in each column.
            entry: Entry coordinates as (x, y).
            exit: Exit coordinates as (x, y).
        """
        self.width = width
        self.height = height
        self.entry = entry
        self.exit = exit
        self.grid = [
            [Cell() for _ in range(width)]
            for _ in range(height)
        ]

    def cell_to_hex(self, cell: Cell) -> str:
        """Convert a cell wall configuration to one hexadecimal digit.

        Args:
            cell: Cell whose walls should be converted.

        Returns:
            A hexadecimal character representing the cell walls.
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
        return format(value, "x")

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

    def is_reachable(self) -> bool:
        """Check whether the exit is reachable from the entry.

        Returns:
            True if the exit is reachable, otherwise False.
        """
        stack = [self.entry]
        visited = {self.entry}
        while stack:
            x, y = stack.pop()
            if (x, y) == self.exit:
                return True
            cell = self.grid[y][x]
            if not cell.north and y > 0:
                neighbor = (x, y - 1)
                if neighbor not in visited:
                    visited.add(neighbor)
                    stack.append(neighbor)
            if not cell.east and x < self.width - 1:
                neighbor = (x + 1, y)
                if neighbor not in visited:
                    visited.add(neighbor)
                    stack.append(neighbor)
            if not cell.south and y < self.height - 1:
                neighbor = (x, y + 1)
                if neighbor not in visited:
                    visited.add(neighbor)
                    stack.append(neighbor)
            if not cell.west and x > 0:
                neighbor = (x - 1, y)
                if neighbor not in visited:
                    visited.add(neighbor)
                    stack.append(neighbor)
        return False

    def remove_wall(self, x1: int, y1: int, x2: int, y2: int) -> None:
        """Remove the wall between two adjacent cells.

        Cells belonging to the 42 pattern are protected.

        Args:
            x1: X coordinate of the first cell.
            y1: Y coordinate of the first cell.
            x2: X coordinate of the second cell.
            y2: Y coordinate of the second cell.
        """
        pattern = self.get_pattern_42()
        if (x1, y1) in pattern or (x2, y2) in pattern:
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
        start_x = (self.width - pattern_width) // 2
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
        self.generate_perfect(seed)
        pattern = self.get_pattern_42()
        blocked = set(pattern)
        while True:
            dead_ends = self.get_dead_ends(blocked)
            candidates = []
            for x, y in dead_ends:
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
                    candidates.append((x, y, neighbors))
            if not candidates:
                break
            x, y, neighbors = random.choice(candidates)
            nx, ny = random.choice(neighbors)
            self.remove_wall(x, y, nx, ny)

    def generate_perfect(self, seed: int | None = None) -> None:
        """Generate a perfect maze using recursive backtracking.

        Args:
            seed: Optional random seed for reproducible generation.

        Raises:
            ConfigError: If entry or exit is inside the 42 pattern.
        """
        if seed is not None:
            random.seed(seed)
        pattern = self.get_pattern_42()
        blocked = set(pattern)
        if self.entry in blocked:
            raise ConfigError("Entry cannot be inside 42 pattern")
        if self.exit in blocked:
            raise ConfigError("Exit cannot be inside 42 pattern")
        x, y = self.entry
        stack = [(x, y)]
        self.grid[y][x].visited = True
        while stack:
            x, y = stack[-1]
            neighbors = self.get_neighbors(x, y, blocked)
            if neighbors:
                nx, ny = random.choice(neighbors)
                self.remove_wall(x, y, nx, ny)
                self.grid[ny][nx].visited = True
                stack.append((nx, ny))
            else:
                stack.pop()

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
