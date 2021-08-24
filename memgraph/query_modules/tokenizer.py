"""
Tokenizer: Runs tokenization and exports word lemmas along with the count
           of every word lemma

Installation:
    1. Run the following within your Memgraph Docker container
        python3 -m pip install -U pip setuptools wheel
        python3 -m pip install -U spacy
        python3 -m spacy download en_core_web_sm
    2. Restart the Memgraph process to be aware of the new python packages
    3. Copy the script `tokenizer.py` to `usr/lib/memgraph/query_modules`
    4. Refresh the query modules by connecting to Memgraph and running the query:
        CALL mg.load_all();

Usage:
    1. Use tokenizer by running the query:
        CALL tokenizer.tokenize("Hello world!") YIELD *;
"""

import mgp
import spacy
from collections import Counter

nlp = spacy.load("en_core_web_sm")

VALID_POS_TAGS = {'NOUN', 'VERB', 'PROPN', 'ADJ', 'ADV', 'INTJ'}

# Thanks to https://realpython.com/natural-language-processing-spacy-python/
def is_token_allowed(token) -> bool:
    return token \
        and not token.is_stop \
        and not token.is_punct \
        and token.pos_ in VALID_POS_TAGS \
        and token.is_alpha

def preprocess_token(token) -> str:
    return token.lemma_.strip().lower()

def tokenize_text(text: str) -> Counter:
    doc = nlp(text)
    words = (preprocess_token(token) for token in doc if is_token_allowed(token))
    return Counter(words)

@mgp.read_proc
def tokenize(context: mgp.ProcCtx, text: mgp.Nullable[str]) -> mgp.Record(word=str, count=int):
    counter = tokenize_text(text)
    return [mgp.Record(word=word, count=count) for word, count in counter.items()]
