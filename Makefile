.PHONY: install test seed-demo bench lint clean

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
