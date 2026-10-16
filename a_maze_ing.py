import sys
from typing import TypedDict
from MazeGenerator import Maze


class Config(TypedDict):
    WIDTH: int
    HEIGHT: int
    ENTRY: tuple[int, int]
    EXIT: tuple[int, int]
    OUTPUT_FILE: str
    PERFECT: bool
    SEED: int | None


class ConfigError(Exception):
    """Custom exception for configuration errors."""
    pass


def parse_coordinate(value: str, key: str) -> tuple[int, int]:
    parts = value.split(",")

    if len(parts) != 2:
        raise ConfigError(
            f"{key}: invalid coordinate format '{value}', expected 'x,y'"
        )
    try:
        x = int(parts[0].strip())
        y = int(parts[1].strip())
    except ValueError:
        raise ConfigError(
            f"{key}: coordinates must be integers, got '{value}'"
        )
    return (x, y)


def parse_int(config: dict[str, str], key: str) -> int:
    try:
        return int(config[key])
    except (KeyError, ValueError):
        raise ConfigError(
            f"{key}: must be an integer, got '{config.get(key)}'"
        )


def parse_bool(config: dict[str, str], key: str) -> bool:
    value = config[key].lower()
    if value == "true":
        return True
    if value == "false":
        return False
    raise ConfigError(
        f"{key}: must be a boolean ('true' or 'false'), got '{config[key]}'"
    )


def load_config(filename: str) -> dict[str, str]:
    config = {}
    line_num = 0

    with open(filename, "r", encoding="utf-8") as file:
        for line in file:
            line_num += 1
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                raise ConfigError(
                    f"Line {line_num}: invalid syntax in '{line}'"
                    f" (missing '=')"
                )
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip("\"'")
            if key in config:
                raise ConfigError(
                    f"Line {line_num}: duplicate key '{key}' found"
                )
            config[key] = value
    return config


def validate_config(config: dict[str, str]) -> Config:
    required_keys = [
        "WIDTH",
        "HEIGHT",
        "ENTRY",
        "EXIT",
        "OUTPUT_FILE",
        "PERFECT"
    ]
    # Check for required keys
    for key in required_keys:
        if key not in config or not config[key]:
            raise ConfigError(f"{key}: missing mandatory configuration key")
    # Validation and type casting of WIDTH and HEIGHT
    width = parse_int(config, "WIDTH")
    if width <= 0:
        raise ConfigError(f"WIDTH: must be greater than 0, got {width}")
    height = parse_int(config, "HEIGHT")
    if height <= 0:
        raise ConfigError(f"HEIGHT: must be greater than 0, got {height}")
    # Validation and type casting of ENTRY and EXIT coordinates
    entry_coord = parse_coordinate(config["ENTRY"], "ENTRY")
    exit_coord = parse_coordinate(config["EXIT"], "EXIT")
    if not (0 <= entry_coord[0] < width and 0 <= entry_coord[1] < height):
        raise ConfigError(
            f"ENTRY: coordinate {entry_coord} is outside maze bounds"
            f" (0..{width-1}, 0..{height-1})"
        )
    if not (0 <= exit_coord[0] < width and 0 <= exit_coord[1] < height):
        raise ConfigError(
            f"EXIT: coordinate {exit_coord} is outside maze bounds"
            f" (0..{width-1}, 0..{height-1})"
        )
    if entry_coord == exit_coord:
        raise ConfigError(
            f"ENTRY / EXIT: entry {entry_coord} and exit {exit_coord}"
            f" must be different"
        )
    # Validation and type casting of boolean value
    is_perfect = parse_bool(config, "PERFECT")
    # Validation and type casting of SEED
    seed = None
    if "SEED" in config:
        if not config["SEED"]:
            raise ConfigError("SEED: value cannot be empty")
        seed = parse_int(config, "SEED")
    # Build validated configuration
    validated_config: Config = {
        "WIDTH": width,
        "HEIGHT": height,
        "ENTRY": entry_coord,
        "EXIT": exit_coord,
        "OUTPUT_FILE": config["OUTPUT_FILE"],
        "PERFECT": is_perfect,
        "SEED": seed,
    }
    # Return the validated and parsed configuration
    return validated_config


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python3 a_maze_ing.py config.txt")
        return
    config_file = sys.argv[1]
    try:
        raw_config = load_config(config_file)
        print(raw_config)
        config = validate_config(raw_config)
        print(config)
        maze = Maze(
            config["WIDTH"],
            config["HEIGHT"],
            config["ENTRY"],
            config["EXIT"],
        )
        if config["PERFECT"]:
            maze.generate_perfect(config["SEED"])
        else:
            maze.generate(config["SEED"])
        path = maze.find_path()
        print("Path:", path)
        maze.print_maze(path)
    except ConfigError as e:
        print(f"Configuration Error: {e}")
    except FileNotFoundError:
        print(f"Error: file '{config_file}' not found")
    except OSError as e:
        print(f"File System Error: {e}")
    except KeyboardInterrupt:
        print("\nProgram execution aborted by user.")
    except Exception as e:
        print(f"Unexpected Error: {e}")


if __name__ == "__main__":
    main()
