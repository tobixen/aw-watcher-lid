.PHONY: help install install-dev install-all test lint format clean uninstall install-service uninstall-service enable-service disable-service

help:
	@echo "Available targets:"
	@echo "  install-all       - Complete setup (install + enable service)"
	@echo "  install           - Install the package using poetry"
	@echo "  install-dev       - Install with development dependencies"
	@echo "  test              - Run tests"
	@echo "  lint              - Run linting (ruff check)"
	@echo "  format            - Format code (ruff format)"
	@echo "  clean             - Remove build artifacts and cache"
	@echo "  install-service   - Install systemd user service"
	@echo "  uninstall-service - Uninstall systemd user service"
	@echo "  enable-service    - Install and enable the service"
	@echo "  disable-service   - Disable and stop the service"
	@echo "  uninstall         - Uninstall the package"

install:
	poetry install

install-dev:
	poetry install --with dev

install-all: install enable-service
	@echo ""
	@echo "✓ Installation complete!"
	@echo "  The watcher is now installed and running as a systemd service."
	@echo ""
	@echo "Check status with: systemctl --user status aw-watcher-lid"
	@echo "View logs with:    journalctl --user -u aw-watcher-lid -f"

test:
	poetry run pytest tests/ -v

lint:
	poetry run ruff check .

format:
	poetry run ruff format .

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf dist/ build/

install-service:
	@echo "Installing systemd user service..."
	mkdir -p ~/.config/systemd/user
	cp misc/aw-watcher-lid.service ~/.config/systemd/user/
	systemctl --user daemon-reload
	@echo "Service installed. Use 'make enable-service' to enable and start it."

uninstall-service:
	@echo "Uninstalling systemd user service..."
	systemctl --user stop aw-watcher-lid 2>/dev/null || true
	systemctl --user disable aw-watcher-lid 2>/dev/null || true
	rm -f ~/.config/systemd/user/aw-watcher-lid.service
	systemctl --user daemon-reload
	@echo "Service uninstalled."

enable-service: install-service
	@echo "Enabling and starting service..."
	systemctl --user enable aw-watcher-lid
	systemctl --user start aw-watcher-lid
	@echo "Service status:"
	@systemctl --user status aw-watcher-lid --no-pager

disable-service:
	@echo "Disabling and stopping service..."
	systemctl --user stop aw-watcher-lid
	systemctl --user disable aw-watcher-lid
	@echo "Service disabled."

uninstall:
	poetry env remove --all 2>/dev/null || true
	pip uninstall -y aw-watcher-lid 2>/dev/null || true
	@echo "Package uninstalled."
