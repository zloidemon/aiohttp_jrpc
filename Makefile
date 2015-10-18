flake:
	pep8 aiohttp_jrpc tests/test_jrpc_service.py
	pyflakes aiohttp_jrpc tests

test: flake
	py.test -s -q ./tests/

vtest: flake
	py.test -s ./tests/

cov cover coverage: flake
	py.test -s ./tests/ --cov=aiohttp_jrpc --cov=tests --cov-report=html --cov-report=term
	@echo "open file://`pwd`/coverage/index.html"

clean:
	rm -rf `find . -name __pycache__`
	rm -f `find . -type f -name '*.py[co]' `
	rm -f `find . -type f -name '*~' `
	rm -f `find . -type f -name '.*~' `
	rm -f `find . -type f -name '@*' `
	rm -f `find . -type f -name '#*#' `
	rm -f `find . -type f -name '*.orig' `
	rm -f `find . -type f -name '*.rej' `
	rm -f .coverage
	rm -rf coverage
	rm -rf build
	rm -rf cover
	python setup.py clean

.PHONY: all build venv flake test vtest testloop cov clean
