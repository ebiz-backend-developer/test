test -e .venv/bin/activate && . .venv/bin/activate; true
test:
	python3 -m unittest discover -s tests -v

run:
	python3 run.py

seed:
	python3 run.py --seed-only
