PYTHON ?= python3
ENV    := env
PY     := $(ENV)/bin/python

.PHONY: dev_install dev_run

# Create env/ with $(PYTHON) (recreated if it was built with a different Python), then install deps.
dev_install:
	@$(PYTHON) -c 'import sys; assert sys.version_info >= (3, 10), "need Python 3.10+"'
	@if [ ! -x $(PY) ] || [ "$$($(PY) -V)" != "$$($(PYTHON) -V)" ]; then \
		echo "creating $(ENV)/ with $$($(PYTHON) -V)"; \
		rm -rf $(ENV) && $(PYTHON) -m venv $(ENV); \
	fi
	$(PY) -m pip install -q -r requirements.txt
	@echo "ready: $$($(PY) -V) in $(ENV)/"

# Run both examples against LM Studio (server must be running with clef-flash loaded).
dev_run:
	$(PY) main.py
	$(PY) example1.py
