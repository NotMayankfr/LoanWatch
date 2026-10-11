SHELL := /bin/bash

.PHONY: setup feeds ingest-clean test-negative recon report test all

setup:
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements.txt

feeds:
	./scripts/make_feed.sh

ingest-clean:
	@for b in 20261005 20261006 20261007 20261008 20261009; do \
		./scripts/ingest.sh --batch-date $$b; \
	done

test-negative:
	./tests/test_corrupted_feeds.sh

recon:
	.venv/bin/python scripts/run_reconciliation.py

report:
	.venv/bin/python scripts/generate_mis_pack.py --batch-date 20261009
	.venv/bin/python scripts/render_dashboard_previews.py

test:
	.venv/bin/pytest tests/ -v

all: feeds ingest-clean test-negative recon report test
