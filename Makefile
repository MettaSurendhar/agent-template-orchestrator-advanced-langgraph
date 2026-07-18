.PHONY: install run test clean

install:
	pip install -r requirements.txt

run:
	cd src && python app.py

test:
	pytest -v

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
