PYTHON = python3
MAIN = src/a_maze_ing.py
CONFIG = configs/config.txt
MLX_WHEEL = mlx-2.2-py3-none-any.whl

install:
	@test -f $(MLX_WHEEL) || { echo "Error: $(MLX_WHEEL) not found in the project root"; exit 1; }
	$(PYTHON) -m pip install flake8 mypy $(MLX_WHEEL)

run:
	$(PYTHON) $(MAIN) $(CONFIG)

debug:
	$(PYTHON) -m pdb $(MAIN) $(CONFIG)

clean:
	find . -type d \( -name __pycache__ -o -name .mypy_cache \) -prune -exec rm -rf {} +
	rm -f output/*.txt

lint:
	flake8 .
	mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict:
	flake8 .
	mypy . --strict

.PHONY: install run debug clean lint lint-strict
