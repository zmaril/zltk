import argparse
import os
import sqlite3
from PyPDF2 import PdfReader
from openai import OpenAI
from langdetect import detect
from dotenv import load_dotenv
import json
from pydantic import BaseModel
import nltk
from multiprocessing import Pool
nltk.download('punkt')
import reportlab

load_dotenv()

# add a sentence cache that saves to disk 

cache_file = "data/sentence_cache.json"


# Initialize OpenAI API (make sure to set your API key as an environment variable)
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
)

class GermanWordExplanation(BaseModel):
    word: str
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

    # check if the sentence is in the cache
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
        model="gpt-4o-2024-08-06",
        response_format=GermanSentenceExplanation,
    )

    results = chat_completion.choices[0].message.content
    # parse the results
    json_results = json.loads(results)
    # cache the results
    processed_sentence = GermanSentenceExplanation(**json_results)

    # save the results to the cache
    cache[located_sentence.sentence] = processed_sentence.model_dump_json()
    with open(cache_file, "w") as f:
        json.dump(cache, f)
    return (located_sentence, processed_sentence)


def generate_markdown(processed_sentences, title):
    markdown = f"# Explanation for \"{title}\"\n\n"
    # Make each page a section and each paragraph a sub-section
    page_number = -1 
    paragraph_number = 0

    print(processed_sentences)


    for (location, explanation) in processed_sentences:
       # every time there is a page number or paragraph number change, add a new section
        if location.page_number != page_number:
            page_number = location.page_number
            markdown += f"# Page {page_number} \n\n"
        if location.paragraph_number != paragraph_number:
            paragraph_number = location.paragraph_number
            markdown += f"## Paragraph {paragraph_number} \n\n"

        markdown += f"German: `{location.sentence}` \n\n"
        markdown += f"English: `{explanation.translation}` \n\n"
        markdown += f"{explanation.grammar_explanation}\n\n"
        for word_definition in explanation.word_definitions:
            markdown += f"Word: {word_definition.word}\n\n"
            markdown += f"Meaning: {word_definition.meaning}\n\n"
            markdown += f"Examples: {word_definition.examples}\n\n"
    return markdown

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

    markdown = generate_markdown(processed_sentences, title)
    
    if output_file is None:
        output_file = f"{input_file.split('.')[0]}_explained.md"

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(markdown)

    # run pandoc to convert the markdown to a pdf
    os.system(f"pandoc -t html {output_file} -o {output_file.split('.')[0]}.pdf")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ZLTK: Zack's Language Toolkit")
    parser.add_argument("input_file", help="Input PDF file")
    # optional argument, if not provided, the script will make something like `input_file_name_explained.pdf`
    parser.add_argument("-o", "--output_file", help="Output Markdown file")
    parser.add_argument("-n", "--number_of_pages", type=int, default=1, help="Number of pages to process")
    # add optional title argument
    parser.add_argument("-t", "--title", help="Title of the document")
    args = parser.parse_args()
    
    main(args.input_file, args.output_file, args.number_of_pages, args.title)