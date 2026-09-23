.PHONY: help install dev install-all test lint format clean uninstall install-service uninstall-service enable-service disable-service

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-18s\033[0m %s\n", $$1, $$2}'

install:  ## Install the package (auto-detects root, uv, pipx, or pip)
	@if [ "$$(id -u)" = "0" ]; then \
		echo "Running as root, installing system-wide..."; \
		pip install .; \
	elif command -v uv >/dev/null 2>&1; then \
		echo "Installing with uv..."; \
		uv tool install --reinstall .; \
	elif command -v pipx >/dev/null 2>&1; then \
		echo "Installing with pipx..."; \
		pipx install --force .; \
	else \
		echo "Tip: Install uv or pipx for isolated installs (pacman -S uv, apt install pipx, brew install uv)"; \
		echo "Falling back to pip install --user ..."; \
		PIP_BREAK_SYSTEM_PACKAGES=1 pip install --user .; \
	fi
	@echo ""
	@echo "✓ aw-watcher-lid installed successfully!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Recommended: Add to aw-qt (ActivityWatch GUI) config"
	@echo "     Edit your aw-qt config to start this watcher automatically"
	@echo ""
	@echo "  2. Alternative: Run as systemd service"
	@echo "     make enable-service"
	@echo ""
	@echo "  3. Test manually:"
	@echo "     aw-watcher-lid --verbose"
	@echo ""

dev:  ## Install editable with dev dependencies and pre-commit hooks
	PIP_BREAK_SYSTEM_PACKAGES=1 pip install -e ".[dev]"
	pre-commit install --hook-type pre-commit --hook-type pre-push --hook-type commit-msg \
		--hook-type prepare-commit-msg --hook-type post-commit

install-all: install enable-service  ## Complete setup (install + enable service)
	@echo ""
	@echo "✓ Installation complete!"
	@echo "  The watcher is now installed and running as a systemd service."
	@echo ""
	@echo "Check status with: systemctl --user status aw-watcher-lid"
	@echo "View logs with:    journalctl --user -u aw-watcher-lid -f"

test:  ## Run tests
	python -m pytest -v

lint:  ## Run ruff linter and formatter check
	python -m ruff check .
	python -m ruff format --check .

format:  ## Auto-format code
	python -m ruff check --fix .
	python -m ruff format .

clean:  ## Remove build artifacts and caches
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf dist/ build/

install-service:  ## Install systemd user service
	@echo "Installing systemd user service..."
	mkdir -p ~/.config/systemd/user
	@# systemd does not search ~/.local/bin (where uv/pipx/pip --user put the
	@# script), so resolve the absolute path at install time.
	bin=$$(command -v aw-watcher-lid || echo "$$HOME/.local/bin/aw-watcher-lid"); \
		sed "s|^ExecStart=.*|ExecStart=$$bin|" misc/aw-watcher-lid.service \
		> ~/.config/systemd/user/aw-watcher-lid.service
	systemctl --user daemon-reload
	@echo "Service installed. Use 'make enable-service' to enable and start it."

uninstall-service:  ## Uninstall systemd user service
	@echo "Uninstalling systemd user service..."
	systemctl --user stop aw-watcher-lid 2>/dev/null || true
	systemctl --user disable aw-watcher-lid 2>/dev/null || true
	rm -f ~/.config/systemd/user/aw-watcher-lid.service
	systemctl --user daemon-reload
	@echo "Service uninstalled."

enable-service: install-service  ## Install, enable and start the service
	@echo "Enabling and starting service..."
	systemctl --user enable aw-watcher-lid
	systemctl --user start aw-watcher-lid
	@echo "Service status:"
	@systemctl --user status aw-watcher-lid --no-pager

disable-service:  ## Disable and stop the service
	@echo "Disabling and stopping service..."
	systemctl --user stop aw-watcher-lid
	systemctl --user disable aw-watcher-lid
	@echo "Service disabled."

uninstall:  ## Uninstall the package
	uv tool uninstall aw-watcher-lid 2>/dev/null || true
	pipx uninstall aw-watcher-lid 2>/dev/null || true
	PIP_BREAK_SYSTEM_PACKAGES=1 pip uninstall -y aw-watcher-lid 2>/dev/null || true
	@echo "Package uninstalled."
