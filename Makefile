.PHONY: run test seed

run:
	python3 run.py

test:
	python3 -m unittest discover -s tests -v

seed:
	python3 -c "from app.store import Store; from app.seed import seed; s=Store('data/school.db'); seed(s); print('seeded')"
