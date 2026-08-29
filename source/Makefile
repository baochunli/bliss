IDML ?= ../indesign/Bliss Pages Final Edition.idml
ARTICLES ?= articles
PYTHON ?= python3
LATEXMK ?= latexmk

.PHONY: all convert test book verify clean

all: verify

convert:
	$(PYTHON) scripts/convert_idml.py \
		--idml "$(IDML)" \
		--articles "$(ARTICLES)" \
		--output content/book-content.tex \
		--manifest content/manifest.json

test:
	$(PYTHON) -m unittest discover -s tests -v

book: convert
	$(LATEXMK) -lualatex -interaction=nonstopmode -halt-on-error book.tex

verify: test book
	@test -f book.pdf
	@test "$$(pdfinfo book.pdf | awk '/^Pages:/ { print $$2 }')" -eq "440"
	@test "$$(pdfinfo book.pdf | awk '/^Page size:/ { print $$3 "x" $$5 }')" = "432x648"
	@qpdf --check book.pdf >/dev/null
	@! pdffonts book.pdf | tail -n +3 | rg -q ' no '
	@! rg -n -F \
		-e 'Missing character' \
		-e 'Underfull \hbox' \
		-e 'Underfull \vbox' \
		-e 'Overfull \hbox' \
		-e 'Overfull \vbox' \
		-e 'LaTeX Warning' \
		book.log
	@echo "Verified book.pdf: $$(pdfinfo book.pdf | awk '/^Pages:/ { print $$2 }') pages, 432 x 648 pt, clean LaTeX log"

clean:
	$(LATEXMK) -C book.tex
