.PHONY: test run seed clean

test:
	python3 -m unittest discover -s tests -v

run:
	python3 run.py

seed:
	python3 -m app.seed schoolms.db

clean:
	rm -f schoolms.db
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +
