

```
brew install pandoc 
git clone https://github.com/zmaril/zltk.git
cd zltk
poetry run python -m spacy download de_core_news_lg
poetry install
poetry run python -m zltk -i yourpdf_in_german.pdf -o explainerpdf_in_english.pdf
```