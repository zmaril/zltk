import argparse
import os
import sqlite3
from PyPDF2 import PdfReader
from openai import OpenAI
from langdetect import detect
from dotenv import load_dotenv
import json
from models import GermanWord, GermanSentence, VerbConjugation, NounConjugation, AdjectiveConjugation, AdverbConjugation

load_dotenv()

# Initialize OpenAI API (make sure to set your API key as an environment variable)
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
)

engine = create_engine("sqlite:///data/zltk_cache.db")
SQLModel.metadata.create_all(engine)

def get_word_info(word):
    print(f"Getting word info for {word}")
    with Session(engine, expire_on_commit=False) as session:    
        word_info = session.get(GermanWord, word)
        if word_info:
            return word_info
        else:
            # Call OpenAI API to get word info
            chat_completion = client.beta.chat.completions.parse(
                messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant for language learning."
                },
                {
                    "role": "user",
                    "content": f"Provide the definition for the German word '{word}'.",
                }
            ],
            model="gpt-4o-2024-08-06",
            response_format=GermanWord,
            )
            info = chat_completion.choices[0].message.content
            json_info = json.loads(info)
            info = GermanWord(**json_info)

            # Cache the result
            session.add(info)
            session.commit()
            session.expunge(info)
            # return json
            return info

def process_sentence(sentence):
    # Pass all the words in the sentence to openai and have it return a list of words with their meanings

    chat_completion = client.beta.chat.completions.parse(
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant for language learning."
            },
            {
                "role": "user",
                "content": f"Provide a definition for each of the German words in the following sentence: \n '{sentence}'.",
            }
        ],
        model="gpt-4o-2024-08-06",
        response_format=GermanSentence,
    )

    results = chat_completion.choices[0].message.content
    # parse the results
    json_results = json.loads(results)
    results = GermanSentence(**json_results)
    # cache the results
    with Session(engine, expire_on_commit=False) as session:
        session.add(results)
        session.commit()
        session.expunge(results)
    return results


def process_page(page_text):
    sentences = nltk.sent_tokenize(page_text)
    with Pool(processes=1) as pool:
        results = pool.map(process_sentence, sentences)
    return None # have it look up stuff later

def generate_markdown(reader, pages):
    # Go through page by page and get the words
    markdown = ""
    for i in range(pages):
        page = reader.pages[i]
        page_text = page.extract_text()
        # look up words directly 
        words = get_word_info(page_text)
        # then generate markdown per page
        markdown += f"# Page {page.page_number} Explanation \n\n"
        for difficulty in ["A1", "A2", "B1", "B2", "C1", "C2"]:
            markdown += f"## {difficulty} Words\n\n"
            for word, info in words.items():
                if info["difficulty"] == difficulty:
                    markdown += f"### {word}\n\n"
                    markdown += f"Meaning: {info['meaning']}\n\n"
                    markdown += "Examples:\n"
                for i, example in enumerate(info["examples"][:3], 1):
                    markdown += f"{i}. {example}\n"
                markdown += "\n"
    return markdown

def main(input_file, output_file, pages):
    reader = PdfReader(input_file)

    pages_to_process = min(pages, len(reader.pages))
    
    for i in range(pages_to_process):
        page = reader.pages[i]
        page_text = page.extract_text()
        process_page(page_text)
    
    markdown = generate_markdown(reader, pages_to_process)
    
    if output_file is None:
        output_file = f"{input_file.split('.')[0]}_explained.md"

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(markdown)

    # run pandoc to convert the markdown to a pdf
    os.system(f"pandoc -t html {output_file} -o {output_file.split('.')[0]}.pdf")
    
    conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ZLTK: Zack's Language Toolkit")
    parser.add_argument("input_file", help="Input PDF file")
    # optional argument, if not provided, the script will make something like `input_file_name_explained.pdf`
    parser.add_argument("-o", "--output_file", help="Output Markdown file")
    parser.add_argument("-n", "--number_of_pages", type=int, default=1, help="Number of pages to process")
    args = parser.parse_args()
    
    main(args.input_file, args.output_file, args.number_of_pages)