# Makefile for grepctl package management

.PHONY: help clean build check test publish publish-test install install-dev

help:
	@echo "grepctl Package Management"
	@echo "========================="
	@echo ""
	@echo "Available commands:"
	@echo "  make clean         - Remove build artifacts"
	@echo "  make build         - Build package distributions"
	@echo "  make check         - Check package with twine"
	@echo "  make test          - Run tests (if available)"
	@echo "  make publish-test  - Upload to TestPyPI"
	@echo "  make publish       - Upload to PyPI (production)"
	@echo "  make install       - Install package locally"
	@echo "  make install-dev   - Install in development mode"
	@echo ""
	@echo "Quick publish workflow:"
	@echo "  make clean build publish-test"
	@echo "  make publish"

clean:
	@echo "🧹 Cleaning build artifacts..."
	rm -rf dist/ build/ *.egg-info src/*.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "✅ Clean complete"

build: clean
	@echo "📦 Building package..."
	python -m pip install --upgrade build
	python -m build
	@echo "✅ Build complete"
	@ls -lh dist/

check: build
	@echo "🔍 Checking package..."
	python -m pip install --upgrade twine
	python -m twine check dist/*
	@echo "✅ Package check complete"

test:
	@echo "🧪 Running tests..."
	@if [ -d "tests" ]; then \
		python -m pytest tests/ -v; \
	else \
		echo "⚠️  No tests directory found"; \
	fi

publish-test: check
	@echo "📤 Publishing to TestPyPI..."
	@if [ -f .env ]; then \
		export $$(cat .env | grep -v '^#' | xargs) && \
		python -m twine upload --repository testpypi dist/*; \
	else \
		echo "❌ .env file not found. Create it with:"; \
		echo "   TWINE_USERNAME=__token__"; \
		echo "   TWINE_PASSWORD=pypi-YOUR-TOKEN"; \
		exit 1; \
	fi
	@echo "✅ Published to TestPyPI"
	@echo "📥 Install with:"
	@echo "   pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ grepctl"

publish: check
	@echo "📤 Publishing to PyPI..."
	@if [ -f .env ]; then \
		export $$(cat .env | grep -v '^#' | xargs) && \
		python -m twine upload dist/*; \
	else \
		echo "❌ .env file not found. Create it with:"; \
		echo "   TWINE_USERNAME=__token__"; \
		echo "   TWINE_PASSWORD=pypi-YOUR-TOKEN"; \
		exit 1; \
	fi
	@echo "✅ Published to PyPI"
	@echo "📥 Install with:"
	@echo "   pip install grepctl"

install:
	@echo "📦 Installing package locally..."
	pip install dist/*.whl
	@echo "✅ Installation complete"
	@echo "Test with: grepctl --help"

install-dev:
	@echo "🔧 Installing in development mode..."
	pip install -e .
	@echo "✅ Development installation complete"

# Convenience targets
quick-test: clean build publish-test
quick-publish: clean build publish

.DEFAULT_GOAL := help