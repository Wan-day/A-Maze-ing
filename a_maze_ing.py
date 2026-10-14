import sys
from cell import Maze

def load_config(filename: str) -> dict:
    config = {}


    with open(filename, "r") as file:
        for line in file:
            line = line.strip()

            if not line or line.startswith("#"):
                continue

            key, value = line.split("=", 1)
            config[key.strip()] = value.strip()

    return config


def validate_config(config: dict) -> None:
    required_keys = [
        "WIDTH",
        "HEIGHT",
        "ENTRY",
        "EXIT",
        "OUTPUT_FILE",
        "PERFECT",
        "SEED",
    ]

    for key in required_keys:
        if key not in config:
            raise ValueError(f"Missing configuration key: {key}")

    width = int(config["WIDTH"])
    height = int(config["HEIGHT"])

    if width <= 0:
        raise ValueError("WIDTH must be greater than 0")

    if height <= 0:
        raise ValueError("HEIGHT must be greater than 0")

    entry = tuple(map(int, config["ENTRY"].split(",")))
    exit = tuple(map(int, config["EXIT"].split(",")))

    if len(entry) != 2 or len(exit) != 2:
        raise ValueError("ENTRY and EXIT must have format x,y")

    if not (0 <= entry[0] < width and 0 <= entry[1] < height):
        raise ValueError("ENTRY is outside the maze")

    if not (0 <= exit[0] < width and 0 <= exit[1] < height):
        raise ValueError("EXIT is outside the maze")

    if entry == exit:
        raise ValueError("ENTRY and EXIT must be different")


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 a_maze_ing.py config.txt")
        return

    config_file = sys.argv[1]

    try:
        config = load_config(config_file)
        validate_config(config)

        width = int(config["WIDTH"])
        height = int(config["HEIGHT"])
        entry = tuple(map(int, config["ENTRY"].split(",")))
        exit = tuple(map(int, config["EXIT"].split(",")))
        output_file = config["OUTPUT_FILE"]
        perfect = config["PERFECT"].lower() == "true"
        seed = int(config["SEED"])

        print("Configuration is valid")
        print(config)

    except FileNotFoundError:
        print(f"Error: file '{config_file}' not found")
    except ValueError as e:
        print(f"Error: {e}")

    maze = Maze(width, height)
    maze.remove_wall(5, 5, 6, 5)  # вправо
    maze.remove_wall(5, 5, 4, 5)  # влево
    maze.remove_wall(5, 5, 5, 4)  # вверх
    maze.remove_wall(5, 5, 5, 6)  # вниз
    cell = maze.grid[5][5]

    print(cell.north)
    print(cell.east)
    print(cell.south)
    print(cell.west)


if __name__ == "__main__":
    main()
