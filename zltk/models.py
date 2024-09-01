from typing import Optional, List, Dict
from sqlmodel import Field, Session, SQLModel, create_engine

class VerbConjugation(SQLModel):
    infinitive: str = Field(..., description="The infinitive form of the verb.")
    present_tense: Dict[str, str] = Field(..., description="Present tense conjugation forms (e.g., ich, du, er/sie/es, etc.).")
    past_tense: Dict[str, str] = Field(..., description="Simple past tense conjugation forms (e.g., ich, du, er/sie/es, etc.).")
    perfect_tense: str = Field(..., description="Perfect tense form of the verb (e.g., 'hat gemacht').")
    future_tense: Dict[str, str] = Field(..., description="Future tense conjugation forms (e.g., ich, du, er/sie/es, etc.).")
    subjunctive: Dict[str, str] = Field(..., description="Subjunctive mood conjugation forms (e.g., ich würde, du würdest, etc.).")

class NounDeclension(SQLModel):
    singular: Dict[str, str] = Field(..., description="Singular forms of the noun in different cases (e.g., nominative, accusative, dative, genitive).")
    plural: Dict[str, str] = Field(..., description="Plural forms of the noun in different cases (e.g., nominative, accusative, dative, genitive).")

class AdjectiveDeclension(SQLModel):
    strong_declension: Dict[str, str] = Field(..., description="Strong declension of the adjective.")
    weak_declension: Dict[str, str] = Field(..., description="Weak declension of the adjective.")
    mixed_declension: Dict[str, str] = Field(..., description="Mixed declension of the adjective.")

class GermanWord(SQLModel, table=True):
    root_word: str = Field(..., description="The German word.", primary_key=True)
    meaning: str = Field(..., description="The meaning of the German word in English.")
    part_of_speech: str = Field(..., description="The part of speech of the word (e.g., noun, verb, adjective).")
    difficulty: str = Field(..., description="The CEFR difficulty level of the word (A1-C2).")
    gender: Optional[str] = Field(None, description="The gender of the word if it is a noun (e.g., der, die, das).")
    plural_form: Optional[str] = Field(None, description="The plural form of the word, if applicable.")
    #example_sentences: Optional[List[str]] = Field(None, description="Example sentences using the word.")
    # synonyms: Optional[List[str]] = Field(None, description="Synonyms of the word.")
    # antonyms: Optional[List[str]] = Field(None, description="Antonyms of the word.")
    # frequency: Optional[int] = Field(None, description="The frequency of the word's usage in common language.")
    # pronunciation: Optional[str] = Field(None, description="Pronunciation of the word, possibly in IPA notation.")
    
    # # New fields for conjugations and declensions
    # conjugation: Optional[VerbConjugation] = Field(None, description="Conjugation details if the word is a verb.")
    # declension: Optional[NounDeclension] = Field(None, description="Declension details if the word is a noun.")
    # adjective_declension: Optional[AdjectiveDeclension] = Field(None, description="Declension details if the word is an adjective.")

class GermanSentence(SQLModel, table=True):
    sentence: str = Field(..., description="The German sentence.", primary_key=True)
    meaning: str = Field(..., description="The meaning of the German sentence in English.")
    words: List[GermanWord] = Field(..., description="The words in the sentence.")
    grammar: Optional[str] = Field(None, description="The grammar of the sentence.")