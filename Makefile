.PHONY: build demo sidecar-install sidecar-stub test clean

build:
	cmake -B build -S . && cmake --build build

demo: build
	./build/battle_demo

sidecar-install:
	cd sidecar && uv sync

sidecar-stub:
	cd sidecar && POKEMON_SIDECAR_STUB=1 uv run python -m pokemon_sidecar

test: build
	ctest --test-dir build && cd sidecar && uv run pytest

clean:
	rm -rf build sidecar/.venv sidecar/.pytest_cache

.PHONY: loop-install tournament
loop-install:
	cd loop && uv sync --extra dev

tournament: build loop-install
	cd loop && POKEMON_REPO=$(shell pwd) uv run python -m pokemon_loop --n-battles=12

.PHONY: evolve
evolve: build loop-install
	cd loop && POKEMON_REPO=$(shell pwd) uv run python -m pokemon_loop evolve --generations=5 --pop=8 --battles-per-gen=12

.PHONY: dashboard dashboard-install
dashboard-install:
	cd dashboard && uv sync
dashboard: dashboard-install
	cd dashboard && uv run python -m pokemon_dashboard --host=127.0.0.1 --port=8765
