import argparse
import os
import sqlite3
from PyPDF2 import PdfReader
import openai
from langdetect import detect
from dotenv import load_dotenv
import json
from pydantic import BaseModel, Field 
from enum import Enum
import nltk
from multiprocessing import Pool
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration

nltk.download('punkt')

load_dotenv()

# Initialize cache file
cache_file = "data/sentence_cache.json"

# Initialize OpenAI API
client = openai.OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
)

class PartOfSpeech(str, Enum):
    noun = "noun"
    verb = "verb"
    adj = "adjective"
    pron = "pronoun"
    prep = "preposition"
    conj = "conjunction"
    interj = "interjection"
    art = "article"
    num = "numeral"
    punct = "punctuation"
    other = "other"

class GermanWordExplanation(BaseModel):
    word: str
    part_of_speech: PartOfSpeech
    meaning: str
    examples: list[str]

class GermanSentenceExplanation(BaseModel):
    translation: str
    grammar_explanation: str
    word_definitions: list[GermanWordExplanation]

class Location(BaseModel):
    page_number: int
    paragraph_number: int
    sentence_number: int
    sentence: str

def process_sentence(located_sentence):
    # Check if the sentence is in the cache
    if os.path.exists(cache_file):
        with open(cache_file, "r") as f:
            cache = json.load(f)
    else:
        cache = {}
    
    if located_sentence.sentence in cache:
        j = json.loads(cache[located_sentence.sentence])
        return (located_sentence, GermanSentenceExplanation(**j))

    print(f"Processing sentence {located_sentence.sentence_number} on page {located_sentence.page_number}: {located_sentence.sentence}")
    chat_completion = client.beta.chat.completions.parse(
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant for language learning."
            },
            {
                "role": "user",
                "content": f"Provide the an explanation, in English, for the following sentence. In your explanation, provide a translation of the sentence, then explain the grammar used, and then provide a definition for each word used. For the definition of the word, include anything that a person might need to know about the word to understand it grammatically, so frequency of use, gender for nouns, tense for verbs, etc.  \n '{located_sentence.sentence}'.",
            }
        ],
        model="gpt-4o-mini",
        response_format=GermanSentenceExplanation
    )

    results = chat_completion.choices[0].message.content
    json_results = json.loads(results)
    processed_sentence = GermanSentenceExplanation(**json_results)

    # Save the results to the cache
    cache[located_sentence.sentence] = processed_sentence.model_dump_json()
    with open(cache_file, "w") as f:
        json.dump(cache, f)
    return (located_sentence, processed_sentence)

def generate_pdf(output_file, processed_sentences, title):
    # Set up Jinja2 environment
    env = Environment(loader=FileSystemLoader('.'))
    template = env.get_template('zltk/pdf_template.html')

    # Render the template with our data
    html_out = template.render(title=title, processed_sentences=processed_sentences)

    # Save the HTML to a file
    with open('data/output.html', 'w') as f:
        f.write(html_out)

    # Generate PDF
    HTML(string=html_out).write_pdf(output_file)
    print(f"Generated PDF at {output_file}")

def main(input_file, output_file, pages, title):
    if title is None:
        title = input_file.split('.')[0]
    reader = PdfReader(input_file)

    pages_to_process = min(pages, len(reader.pages))
    
    located_sentences = []
    for i in range(pages_to_process):
        page = reader.pages[i]
        paragraphs = page.extract_text().split("\n\n")
        for j in range(len(paragraphs)):
            sentences = nltk.sent_tokenize(paragraphs[j])
            for k in range(len(sentences)):
                located_sentences.append(Location(page_number=i, paragraph_number=j, sentence_number=k, sentence=sentences[k]))
    
    processed_sentences = list(map(process_sentence, located_sentences))
    if output_file is None:
        output_file = f"{input_file.split('.')[0]}_explained.pdf"
    
    generate_pdf(output_file, processed_sentences, title)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ZLTK: Zack's Language Toolkit")
    parser.add_argument("input_file", help="Input PDF file")
    parser.add_argument("-o", "--output_file", help="Output PDF file")
    parser.add_argument("-n", "--number_of_pages", type=int, default=1, help="Number of pages to process")
    parser.add_argument("-t", "--title", help="Title of the document")
    args = parser.parse_args()
    
    main(args.input_file, args.output_file, args.number_of_pages, args.title)