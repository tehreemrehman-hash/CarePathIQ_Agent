PYTHON ?= /workspaces/CarePathIQ_Agent/.venv/bin/python

.PHONY: test-all pycompile flows dot gemini

test-all: pycompile flows dot gemini
	@echo "✅ All test targets invoked"

pycompile:
	@echo "Running syntax check..."
	$(PYTHON) -m py_compile streamlit_app.py

flows:
	@echo "Running UI sanity checks (test_flows.py)..."
	$(PYTHON) test_flows.py

dot:
	@echo "Running Graphviz check (test_dot.py)..."
	$(PYTHON) test_dot.py

gemini:
	@echo "Running Gemini API smoke (requires GEMINI_API_KEY)..."
	@if [ -z "$$GEMINI_API_KEY" ]; then \
		echo "Skipping: set GEMINI_API_KEY to run this test."; \
	else \
		GEMINI_API_KEY="$$GEMINI_API_KEY" $(PYTHON) test_gemini_api.py; \
	fi
