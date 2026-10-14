import random


class Cell:
    def __init__(self) -> None:
        self.north = True
        self.east = True
        self.south = True
        self.west = True
        self.visited = False


class Maze:
    def __init__(
            self, width: int, height: int, entry: tuple[int, int],
            exit: tuple[int, int]
    ) -> None:
        self.width = width
        self.height = height
        self.entry = entry
        self.exit = exit
        # создаем Cell() внутри вложенного листа
        self.grid = [
            [Cell() for _ in range(width)]
            for _ in range(height)
        ]

    def remove_wall(self, x1: int, y1: int, x2: int, y2: int) -> None:
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

    def get_neighbors(self, x: int, y: int) -> list[tuple[int, int]]:
        neighbors = []

        if y > 0:
            nx, ny = x, y - 1
            if not self.grid[ny][nx].visited:
                neighbors.append((nx, ny))

        if x < self.width - 1:
            nx, ny = x + 1, y
            if not self.grid[ny][nx].visited:
                neighbors.append((nx, ny))

        if y < self.height - 1:
            nx, ny = x, y + 1
            if not self.grid[ny][nx].visited:
                neighbors.append((nx, ny))

        if x > 0:
            nx, ny = x - 1, y
            if not self.grid[ny][nx].visited:
                neighbors.append((nx, ny))

        return neighbors

    def generate_perfect(self, seed: int) -> None:
        random.seed(seed)

        x, y = self.entry

        stack = [(x, y)]
        self.grid[y][x].visited = True

        while stack:
            x, y = stack[-1]

            neighbors = self.get_neighbors(x, y)

            if neighbors:
                nx, ny = random.choice(neighbors)

                self.remove_wall(x, y, nx, ny)

                self.grid[ny][nx].visited = True
                stack.append((nx, ny))

            else:
                stack.pop()

    def print_maze(self) -> None:
        for y in range(self.height):
            # Верхняя граница клеток
            for x in range(self.width):
                print("+", end="")
                if self.grid[y][x].north:
                    print("---", end="")
                else:
                    print("   ", end="")
            print("+")

            # Левая/правая стены
            for x in range(self.width):
                if self.grid[y][x].west:
                    print("|", end="")
                else:
                    print(" ", end="")

                if (x, y) == self.entry:
                    print(" E ", end="")
                elif (x, y) == self.exit:
                    print(" X ", end="")
                else:
                    print("   ", end="")

            # Последняя правая стена строки
            if self.grid[y][self.width - 1].east:
                print("|")
            else:
                print(" ")

        # Нижняя граница
        for x in range(self.width):
            print("+", end="")
            if self.grid[self.height - 1][x].south:
                print("---", end="")
            else:
                print("   ", end="")
        print("+")
