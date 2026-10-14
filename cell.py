class Cell:
    def __init__(self):
        self.north = True
        self.east = True
        self.south = True
        self.west = True


class Maze:
    def __init__(self, width, height):
        self.width = width
        self.height = height

        self.grid = [
            [Cell() for _ in range(width)]
            for _ in range(height)
        ]

    def remove_wall(self, x1, y1, x2, y2):
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

        if abs(x1 - x2) + abs(y1 - y2) != 1:
            raise ValueError("Cells must be adjacent")