import os
import json
import re
from typing import Union, Optional, List, Dict, Any
from pymongo import MongoClient, ASCENDING, UpdateOne

def exist_or_none(dictionary: Dict[str, Any], key: str) -> Optional[Union[str, int, List[Any]]]:
    """
    Safely extracts a value from a dictionary or returns None if the key is not present.
    """
    return dictionary.get(key)


class Word:
    def __init__(self, word_dict: Dict[str, Any]) -> None:
        # Parsing the word with potential numeric suffix
        raw_word = word_dict['word']
        match = re.search(r'(\d+)$', raw_word)
        if match:
            self.word = raw_word[:match.start()]
            self.word_number = int(match.group())
        else:
            self.word = raw_word
            self.word_number = None

        self.word = self.word.replace('-', '').replace('^', '').replace(' ', '').strip()
        # remove () parentheses and their contents
        self.word = re.sub(r'\([^)]*\)', '', self.word)
        # remove [] parentheses and their contents
        self.word = re.sub(r'\[[^)]*]', '', self.word)

        # More robust handling of pronunciations
        pronunciations = word_dict.get('pronunciation_info', [])
        if isinstance(pronunciations, list):
            self.pronunciations = [p.get('pronunciation', '') for p in pronunciations if 'pronunciation' in p]
        else:
            self.pronunciations = [pronunciations.get('pronunciation', '')] if 'pronunciation' in pronunciations else []

        self.word_type = word_dict.get('word_type', "Unknown")
        self.word_unit = word_dict.get('word_unit', "Unknown")

        # Parsing multiple definitions, examples, and additional lexical information
        self.definitions = []
        pos_info = word_dict.get('pos_info', [])
        for pos in pos_info:
            comm_pattern_info = pos.get('comm_pattern_info', [])
            for comm_pattern in comm_pattern_info:
                sense_info = comm_pattern.get('sense_info', [])
                for sense in sense_info:
                    definition = sense.get('definition', "No definition")
                    examples = [example['example'] for example in sense.get('example_info', []) if 'example' in example]
                    self.definitions.append({'definition': definition, 'examples': examples})

        self.related_words = word_dict.get('relation_info', [])
        self.original_language_info = word_dict.get('original_language_info', [])

    @staticmethod
    def _format_examples(examples: List[Dict[str, Any]]) -> str:
        """
        Safely format the example sentences, ensuring all examples are properly handled as strings.
        """
        if not examples:
            return ""
        return ' / '.join([example['example'] for example in examples if 'example' in example])

    def __str__(self) -> str:
        pronunciations = ', '.join(self.pronunciations)
        string_value = f'{self.word}({self.word_number}) [{pronunciations}]  - {self.word_type} {self.word_unit}'
        for i, definition_info in enumerate(self.definitions):
            definition = definition_info['definition']
            examples = definition_info['examples']
            string_value += f'\n    {i + 1}. {definition}'
            if examples:
                string_value += f' (예: {examples})'

        return string_value


def save_to_mongodb(data, collection):
    """
    Saves processed word data to MongoDB using bulk operations for efficiency.
    Using 'word' and 'word_number' as a compound index for uniqueness.
    """
    operations = []  # Accumulate operations in a list

    for word_entry in data:
        word_info = Word(word_entry['word_info'])
        # Prepare the data for MongoDB insertion
        document = word_info.__dict__
        document['pronunciations'] = ', '.join(document['pronunciations'])  # Convert list to string
        document['word_number'] = document.get('word_number', None)  # Ensure compatibility

        # Prepare an upsert operation for each document
        operations.append(UpdateOne(
            {"word": document["word"], "word_number": document["word_number"]},
            {"$set": document},
            upsert=True
        ))

        # Execute the bulk operation in batches for efficiency
        if len(operations) >= 500:  # Adjust the batch size to your needs
            collection.bulk_write(operations, ordered=False)
            operations.clear()  # Clear the list for the next batch

    # Execute any remaining operations in the final batch
    if operations:
        collection.bulk_write(operations, ordered=False)


# Connection to MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client['kkeutmal']  # Use your database name
collection = db['words']  # Use your collection name

# Ensure a compound index on 'word' and 'word_number' for rapid membership checks and uniqueness
collection.create_index([("word", ASCENDING), ("word_number", ASCENDING)], unique=True)

files = [f for f in os.listdir('parser/dict') if f.endswith('.json')]

count = 0

for test_file in files:
    with open(f'parser/dict/{test_file}', 'r', encoding='utf-8') as f:
        data = json.load(f)
        data = data['channel']['item']

        # Save processed data to MongoDB
        save_to_mongodb(data, collection)
        count += len(data)

        if count % 1000 == 0:
            print(f"Processed {count} words")
