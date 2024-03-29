import os
from typing import Dict, Any, Optional, List
from pymongo import MongoClient
import re

from bot.model import Word, Guild, User
from bot.korean import initial_letter


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
        self.words = self.db['words']
        self.guilds = self.db['servers']
        self.users = self.db['users']
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        """
        Ensures the necessary indexes are created for efficient querying.
        """
        self.words.create_index([('word', 1), ('word_number', 1)], unique=True)
        self.guilds.create_index('server_id', unique=True)
        self.users.create_index('user_id', unique=True)
        self.users.create_index([('used_words.word', 1)])

    def get_user(self, user_id: int) -> User:
        result: Optional[Dict[str, Any]] = self.users.find_one({'user_id': user_id})
        if result:
            return User(result)
        else:
            # Assuming you want to automatically create a user if not found
            new_user_dict = {'user_id': user_id, 'used_words': {}, 'experience': 0}
            self.users.insert_one(new_user_dict)
            return User(new_user_dict)

    def add_user_word(self, user: User, word: str) -> None:
        self.users.update_one(
            {'user_id': user.user_id},
            {'$inc': {f'used_words.{word}': 1, 'total_words': 1}},
            upsert=True
        )

        # Update the local user object as well
        user.used_words[word] = user.used_words.get(word, 0) + 1
        user.total_words += 1

    def add_user_experience(self, user: User, experience: int) -> None:
        self.users.update_one(
            {'user_id': user.user_id},
            {'$inc': {'experience': experience}}
        )
        # Update the local user object as well
        user.experience += experience

    def get_favorite_words(self, user: User, count: int) -> list[dict]:
        pipeline = [
            {'$match': {'user_id': user.user_id}},
            {'$project': {'_id': 0, 'words': {'$objectToArray': '$used_words'}}},
            {'$unwind': '$words'},
            {'$sort': {'words.v': -1}},
            {'$limit': count},
            {'$project': {'word': '$words.k', 'count': '$words.v'}}
        ]
        result = self.users.aggregate(pipeline)
        return [{doc['word']: doc['count']} for doc in result]

    def add_guild(self, server_id: int) -> None:
        self.guilds.insert_one({'server_id': server_id})

    def get_guild(self, server_id: int) -> Guild:
        result: Optional[Dict[str, Any]] = self.guilds.find_one({'server_id': server_id})
        if result:
            return Guild(result)
        else:
            self.add_guild(server_id)
            return Guild({'server_id': server_id})

    def update_guild(self, guild: Guild) -> None:
        self.guilds.update_one({'server_id': guild.guild_id}, {'$set': guild.to_dict()})

    def autocomplete(self, prefix: str) -> List[str]:
        """
        Returns up to 15 unique words matching the prefix pattern.
        """
        regex_pattern = f'^{sanitize_input(prefix)}'

        pipeline = [
            {'$match': {'word': {'$regex': regex_pattern}}},
            {'$group': {'_id': '$word'}},
            {'$sort': {'_id': 1}},
            {'$limit': 15}
        ]

        results = self.words.aggregate(pipeline)

        return [doc['_id'] for doc in results]

    def linkable_words(self, link_char: str, cursor: str) -> List[str]:
        """
        Returns all words that start with the link_char and are not in the cursor list.
        """

        pipeline = [
            {'$match': {'word': {'$nin': cursor}}},
            {'$group': {'_id': '$word'}},
            {'$sort': {'_id': 1}},
            {'$match': {'_id': {'$regex': f'^{sanitize_input(link_char)}'}}},
        ]

        results = self.words.aggregate(pipeline)
        return [doc['_id'] for doc in results]

    def word_exists(self, word: str) -> bool:
        """
        Fastest way to check the membership of a word in the collection.
        """
        count = self.words.count_documents({'word': word})
        return count > 0

    def get_word(self, word: str) -> Dict[str, Any]:
        """
        Returns the word object from the collection.
        """
        return self.words.find_one({'word': word})

    def random_word(self) -> str:
        """
        Returns a random word from the collection.
        """
        pipeline = [
            {'$sample': {'size': 1}}
        ]

        results = self.words.aggregate(pipeline)
        return next(results)['word']

    def find_valid_starting_word(self) -> str:
        """
        Finds a valid starting word for the game that is longer than 2 characters
        and has at least 5 linkable words.
        """
        word = self.random_word()

        # Check if the word meets the criteria: longer than 2 chars and has at least 3 linkable words
        if len(word) > 2 and len(self.autocomplete(word)) >= 3:
            return word
        else:
            # Recursively try another word if the criteria are not met
            return self.find_valid_starting_word()

    def can_play(self, guild: Guild) -> bool:
        if not guild.word_chain:
            return False
        last_word = guild.get_last_word()
        if not last_word:
            return False

        def try_play(chain_char, excluded_words):
            linkable_words = self.linkable_words(chain_char, excluded_words)

            if linkable_words:
                return True  # If there are linkable words, the game can still be played.
            # Check with initial letter law (두음 법칙)
            alternate_char = initial_letter(chain_char)
            if alternate_char:
                linkable_words_alt = self.linkable_words(alternate_char, excluded_words)
                if linkable_words_alt:
                    return True  # Found playable words with alternate initial letter.
            return False  # No playable words found, game over.
        return try_play(last_word[-1], [word_dict['word'] for word_dict in guild.word_chain])

    def get_definitions(self, word: str) -> List[Word]:
        """
        Retrieves definitions of a word from the database and returns a list of Word objects.
        If no definitions are found, returns an empty list.
        This version assumes case-sensitive exact matches for efficiency.
        """
        documents = self.words.find({'word': word})
        return [Word(doc) for doc in documents]
