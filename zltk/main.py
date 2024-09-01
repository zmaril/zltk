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
from reportlab.platypus import SimpleDocTemplate, Paragraph, PageBreak, Spacer
from reportlab.lib.styles import getSampleStyleSheet, PropertySet
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import black, white
from reportlab.lib.enums import TA_LEFT

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


class GermanTextParagraphStyle(PropertySet):
    defaults = {
        'fontName':"Helvetica",
        'fontSize':10,
        'leading':12,
        'leftIndent':0,
        'rightIndent':0,
        'firstLineIndent':0,
        'alignment':TA_LEFT,
        'spaceBefore':0,
        'spaceAfter':0,
        'bulletFontName':"Helvetica",
        'bulletFontSize':10,
        'bulletIndent':0,
        'textColor': black,
        'backColor':None,
        'wordWrap':None,
        'borderWidth': 0,
        'borderPadding': 0,
        'borderColor': None,
        'borderRadius': None,
        'allowWidows': 1,
        'allowOrphans': 0,
        'textTransform':None,
        'endDots':None,
        'splitLongWords':1,
        'underlineWidth': 1,
        'bulletAnchor': 'start',
        'justifyLastLine': 0,
        'justifyBreaks': 0,
        'spaceShrinkage': 0.05,
        'strikeWidth': 1,    #stroke width
        'underlineOffset': -0.125,    #fraction of fontsize to offset underlines
        'underlineGap': 1,      #gap for double/triple underline
        'strikeOffset': 0.25,  #fraction of fontsize to offset strikethrough
        'strikeGap': 1,        #gap for double/triple strike
        'linkUnderline': 0,
        #'underlineColor':  None,
        #'strikeColor': None,
        'hyphenationLang': 'en_GB',
        'uriWasteReduce': 0.3,
        'embeddedHyphenation': 1,
        }

def generate_pdf(output_file, processed_sentences, title):
    doc = SimpleDocTemplate(output_file, pagesize=letter)
    styles = getSampleStyleSheet()

    flowables = []

    title_s = f"Explanation for \"{title}\"\n\n"
    title_p = Paragraph(title_s, styles["Title"])

    flowables.append(title_p)

    # Make each page a section and each paragraph a sub-section
    page_number = -1 
    paragraph_number = -1

    for (location, explanation) in processed_sentences:
       # every time there is a page number or paragraph number change, add a new section
        if location.page_number != page_number:
            # add a new page 
            flowables.append(PageBreak())
            page_number = location.page_number
            flowables.append(Paragraph(f"Page {page_number + 1} \n\n", styles["Heading1"]))
            
        if location.paragraph_number != paragraph_number:
            paragraph_number = location.paragraph_number
            flowables.append(Paragraph(f"Paragraph {paragraph_number + 1} of {page_number + 1} \n\n", styles["Heading2"]))

        flowables.append(Paragraph(f"{location.sentence} \n\n", GermanTextParagraphStyle(name="Helvetica")))
        flowables.append(Paragraph(f"{explanation.translation} \n\n", styles["Normal"]))
        # add a new line
        flowables.append(Paragraph(f"\n\n", styles["Normal"]))
        flowables.append(Paragraph(f"{explanation.grammar_explanation}\n\n", styles["Normal"]))
        for word_definition in explanation.word_definitions:
            flowables.append(Paragraph(f"Word: {word_definition.word}\n\n", styles["Normal"]))
            flowables.append(Paragraph(f"Meaning: {word_definition.meaning}\n\n", styles["Normal"]))
            flowables.append(Paragraph(f"Examples: {word_definition.examples}\n\n", styles["Normal"]))
    doc.build(flowables)
    # save the pdf
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
    # optional argument, if not provided, the script will make something like `input_file_name_explained.pdf`
    parser.add_argument("-o", "--output_file", help="Output Markdown file")
    parser.add_argument("-n", "--number_of_pages", type=int, default=1, help="Number of pages to process")
    # add optional title argument
    parser.add_argument("-t", "--title", help="Title of the document")
    args = parser.parse_args()
    
    main(args.input_file, args.output_file, args.number_of_pages, args.title)