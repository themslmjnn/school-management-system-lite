format:
	uv run ruff format .

check-format:
	uv run ruff format --check .

lint:
	uv run ruff check .

typecheck:
	uv run mypy .