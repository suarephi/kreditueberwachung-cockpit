PY := .venv/bin/python
PIP := .venv/bin/pip

.PHONY: help venv install generate verify sample stress stress-all clean reset test dashboard

help:
	@echo "Targets:"
	@echo "  venv         Create .venv"
	@echo "  install      Install dependencies into .venv"
	@echo "  generate     Build the base SQLite DB and CSVs (~10 min for 100k)"
	@echo "  verify       Row counts, FK integrity, error-rate audit"
	@echo "  sample       Run sample queries against the DB"
	@echo "  stress       Run a single scenario, e.g.: make stress SC=combined_adverse"
	@echo "  stress-all   Run all scenarios (heavy)"
	@echo "  test         pytest"
	@echo "  clean        Remove output/"
	@echo "  reset        clean + drop the SQLite DB"

venv:
	python3 -m venv .venv

install: venv
	$(PIP) install --quiet --upgrade pip
	$(PIP) install --quiet -e .

generate:
	$(PY) scripts/generate.py

verify:
	$(PY) scripts/verify.py

sample:
	sqlite3 output/kreditueberwachung.db < scripts/sample_queries.sql

stress:
	$(PY) scripts/run_stress.py --scenario $(SC)

stress-all:
	$(PY) scripts/run_stress.py --scenario all

test:
	$(PY) -m pytest

dashboard:
	$(PY) -m streamlit run dashboard/app.py

clean:
	rm -rf output/csv output/*.md

reset: clean
	rm -f output/kreditueberwachung.db output/kreditueberwachung.db-*
