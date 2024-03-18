import os
from typing import Dict, Any, Optional, List
from pymongo import MongoClient
import time
import re

from bot.model import Word


def sanitize_input(input_str: str) -> str:
    """
    Sanitizes input string to prevent regex injection or other malicious strings for MongoDB queries.
    """
    return re.sub(r'[^\w\s]', '', input_str)


class DB:
    def __init__(self, mongo_client_param: Optional[MongoClient] = None) -> None:
        if mongo_client_param is None:
            mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
            self.mongo_client = MongoClient(mongo_uri)
        else:
            self.mongo_client = mongo_client_param
        self.db = self.mongo_client['kkeutmal']
        self.collection = self.db['words']
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        """
        Ensures the necessary indexes are created for efficient querying.
        """
        self.collection.create_index([('word', 1), ('word_number', 1)], unique=True)

    def autocomplete(self, prefix: str) -> List[str]:
        """
        Returns up to 15 unique words matching the prefix pattern.
        """
        # Assuming the prefix is directly usable after sanitization
        regex_pattern = f'^{sanitize_input(prefix)}'

        pipeline = [
            {'$match': {'word': {'$regex': regex_pattern}}},
            {'$group': {'_id': '$word'}},
            {'$sort': {'_id': 1}},
            {'$limit': 15}
        ]

        results = self.collection.aggregate(pipeline)

        return [doc['_id'] for doc in results]

    def word_exists(self, word: str) -> bool:
        """
        Fastest way to check the membership of a word in the collection.
        """
        count = self.collection.count_documents({'word': word})
        return count > 0

    def get_word(self, word: str) -> Dict[str, Any]:
        """
        Returns the word object from the collection.
        """
        return self.collection.find_one({'word': word})

    def get_definitions(self, word: str) -> List[Word]:
        """
        Retrieves definitions of a word from the database and returns a list of Word objects.
        If no definitions are found, returns an empty list.
        This version assumes case-sensitive exact matches for efficiency.
        """
        documents = self.collection.find({'word': word})
        return [Word(doc) for doc in documents]


# Example usage
if __name__ == '__main__':
    db_manager = DB()
    word_to_check = '한국'
    start_time = time.time()
    exists = db_manager.word_exists(word_to_check)

    print(f'\'{word_to_check}\' exists: {exists} ({(time.time() - start_time) * 1000:.2f} ms)')

    start_time = time.time()

    for words in db_manager.get_definitions(word_to_check):
        print(words)
        print('-' * 40)

    print(f'Retrieved definitions for \'{word_to_check}\' in {(time.time() - start_time) * 1000:.2f} ms')
