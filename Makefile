.DEFAULT_GOAL := help

.PHONY: help
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.PHONY: clean
clean: clean_pyc ## Clean all PYC in the system

.PHONY: clean_pyc
clean_pyc: ## Cleans all *.pyc in the system
	find . -type f -name "*.pyc" -delete || true

.PHONY: clean_pyi
clean_pyi: ## Cleans all *.pyi in the system
	find . -type f -name "*.pyi" -delete || true

.PHONY: clean_pycache
clean_pycache: ## Removes the __pycaches__
	find . -type d -name "*__pycache__*" -delete

.PHONY: serve-docs
serve-docs: ## Runs the local docs
	mkdocs serve

.PHONY: build-docs
build-docs: ## Runs the local docs
	mkdocs build

.PHONY: test
test: ## Runs the tests
	LILYA_SETTINGS_MODULE='tests.settings.TestSettings' pytest $(TESTONLY) --disable-pytest-warnings -s -vv

.PHONY: requirements
requirements: ## Install requirements for development
	pip install -e .[all,dev,test,doc,cli,ipython,ptpython]

ifndef VERBOSE
.SILENT:
endif
