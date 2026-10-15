import sys
from MazeGenerator import Maze


def parse_coordinate(value: str) -> tuple[int, int]:
    parts = value.split(",")

    if len(parts) != 2:
        raise ValueError("Coordinate must have format x,y")

    return (int(parts[0]), int(parts[1]))


def load_config(filename: str) -> dict[str, str]:
    config = {}

    with open(filename, "r") as file:
        for line in file:
            line = line.strip()

            if not line or line.startswith("#"):
                continue

            key, value = line.split("=", 1)
            config[key.strip()] = value.strip()

    return config


def validate_config(config: dict[str, str]) -> None:
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

    entry = parse_coordinate(config["ENTRY"])
    exit = parse_coordinate(config["EXIT"])

    if len(entry) != 2 or len(exit) != 2:
        raise ValueError("ENTRY and EXIT must have format x,y")

    if not (0 <= entry[0] < width and 0 <= entry[1] < height):
        raise ValueError("ENTRY is outside the maze")

    if not (0 <= exit[0] < width and 0 <= exit[1] < height):
        raise ValueError("EXIT is outside the maze")

    if entry == exit:
        raise ValueError("ENTRY and EXIT must be different")


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python3 a_maze_ing.py config.txt")
        return

    config_file = sys.argv[1]

    try:
        config = load_config(config_file)
        validate_config(config)

        width = int(config["WIDTH"])
        height = int(config["HEIGHT"])
        entry = parse_coordinate(config["ENTRY"])
        exit = parse_coordinate(config["EXIT"])
        output_file = config["OUTPUT_FILE"]
        perfect = config["PERFECT"].lower() == "true"
        seed = int(config["SEED"])

        maze = Maze(width, height, entry, exit)
        maze.generate_perfect(seed)
        path = maze.find_path()
        print("Path:", path)
        maze.print_maze(path)

    except FileNotFoundError:
        print(f"Error: file '{config_file}' not found")
    except ValueError as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
