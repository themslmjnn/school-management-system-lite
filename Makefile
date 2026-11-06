format:
	uv run ruff format .

check-format:
	uv run ruff format --check .

lint:
	uv run ruff check .

typecheck:
	uv run mypy .

mig-auto:
	uv run alembic revision --autogenerate -m "$(m)"

mig-empty:
	uv run alembic revision -m "$(m)"

migrate:
	uv run alembic upgrade head