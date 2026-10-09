.PHONY: install test seed-demo bench lint clean secrets

secrets:
	@if command -v gitleaks >/dev/null; then gitleaks detect --source . --verbose; else echo "(gitleaks not installed — grep fallback)"; grep -rnE 'AKIA[0-9A-Z]{16}|sk-live|ghp_[A-Za-z0-9]{20,}|xox[bap]-' --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=specs --exclude-dir=.token-optimizer --exclude-dir=dist --exclude=package-lock.json --exclude=Makefile . && echo "LEAK?" || echo "secrets scan clean"; fi

install:
	cd vision && pip install -r requirements.txt
	cd agent && pip install -r requirements.txt
	cd web && npm install

test:
	cd vision && pytest tests/ -v
	cd agent && pytest tests/ -v

seed-demo:
	python scripts/seed_demo.py

bench:
	cd eval/bench && python bench.py

lint:
	flake8 vision/ agent/
	cd web && npx eslint src/

clean:
	find . -name __pycache__ -exec rm -rf {} +
	find . -name "*.pyc" -delete
