from typing import Dict, Any, Optional
from korean import initial_letter
import nextcord
import re

superscript = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")
pattern = r'<[^>]+>.*?</[^>]+>'


class Word:
    def __init__(self, word_dict: Dict[str, Any]) -> None:
        self.word = word_dict.get('word')
        self.word_number = word_dict.get('word_number')
        self.pronunciations = word_dict.get('pronunciations', [])
        self.word_type = word_dict.get('word_type', 'Unknown')
        self.word_unit = word_dict.get('word_unit', 'Unknown')
        self.definitions = word_dict.get('definitions', [])
        self.related_words = word_dict.get('related_words', [])
        self.original_language_info = word_dict.get('original_language_info', [])

    def __str__(self) -> str:
        string_value = f'{self.word}({self.word_number}) [{self.pronunciations}] - {self.word_type} {self.word_unit}'
        for i, definition_info in enumerate(self.definitions):
            definition = definition_info['definition']
            examples = ' / '.join(definition_info['examples'])
            string_value += f'\n    {i + 1}. {definition}'
            if examples:
                string_value += f' (예: {examples})'
        return string_value

    def to_embed(self) -> nextcord.Embed:
        title_text = f'{self.word}'
        title_text += f'{str(self.word_number).translate(superscript)}' if self.word_number else ''

        description_text = f'[{self.pronunciations}]' if self.pronunciations else ''
        description_text += f' `{self.word_type}`' if self.word_type else ''
        description_text += f' `{self.word_unit}`' if self.word_unit else ''

        word_embed = nextcord.Embed(title=title_text, description=description_text, color=0x2B2D31)

        for i, definition_info in enumerate(self.definitions):
            definition = definition_info['definition']
            definition = re.sub(pattern, '', definition)

            example = ''
            for j, ex in enumerate(definition_info['examples']):
                example += f'> **예시 {j + 1}**) {ex}\n'

            word_embed.add_field(name=f'{i + 1}. {definition}', value=f'{example}', inline=False)

        return word_embed

    def quick_preview(self) -> str:
        """
        :return: First 25 characters of the first definition
        """
        return re.sub(pattern, '', self.definitions[0]['definition'])[:25]


class Guild:
    def __init__(self, server_dict: Dict[str, Any]) -> None:
        self.guild_id = server_dict.get('server_id')
        self.word_chain_channel = server_dict.get('word_chain_channel', None)
        self.word_chain = server_dict.get('word_chain', [])
        self.best_combo = server_dict.get('best_combo', 0)

    def get_last_word(self) -> str:
        return self.word_chain[-1]['word']

    def word_chain_channel_id(self) -> Optional[int]:
        return self.word_chain_channel

    def add_word(self, word: str, message_id: int) -> None:
        self.word_chain.append({'word': word, 'message_id': message_id})
        currnt_combo = len(self.word_chain)
        if currnt_combo > self.best_combo:
            self.best_combo = currnt_combo

    def to_dict(self) -> Dict[str, Any]:
        return {
            'server_id': self.guild_id,
            'word_chain_channel': self.word_chain_channel,
            'word_chain': self.word_chain,
            'best_combo': self.best_combo
        }

    def is_word_in_chain(self, word: str) -> bool:
        return word in [word['word'] for word in self.word_chain]

    def initialize_chain(self, word: str, message_id: int) -> None:
        self.word_chain = [{'word': word, 'message_id': message_id}]

    def get_last_character(self) -> tuple[str, Optional[str]]:
        return self.get_last_word()[-1], initial_letter(self.get_last_word()[-1])

    def get_word_message_url(self, word: str) -> Optional[str]:
        for chain in self.word_chain:
            if chain['word'] == word:
                return f'https://discord.com/channels/{self.guild_id}/{self.word_chain_channel}/{chain["message_id"]}'
        return None

    def get_linkable_char_str(self) -> str:
        last_char, alt_char = self.get_last_character()
        return f'{last_char}({alt_char})' if alt_char else last_char

    def is_word_chain_channel(self, channel_id: int) -> bool:
        return self.word_chain_channel == channel_id


class User:
    def __init__(self, user_dict: dict) -> None:
        self.user_id = user_dict.get('user_id')
        self.used_words = user_dict.get('used_words', {})
        self.experience = user_dict.get('experience', 0)
        self.total_words = user_dict.get('total_words', 0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'user_id': self.user_id,
            'used_words': self.used_words,
            'experience': self.experience
        }
