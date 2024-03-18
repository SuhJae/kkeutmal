from typing import Dict, Any
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
        :return: First 100 char of the first definition
        """
        return re.sub(pattern, '', self.definitions[0]['definition'])[:24]


class Server:
    def __init__(self, server_dict: Dict[str, Any]) -> None:
        self.server_id = server_dict.get('server_id')
        self.prefix = server_dict.get('prefix', '!')
        self.language = server_dict.get('language', 'ko')
        self.word_list = [Word(word_dict) for word_dict in server_dict.get('word_list', [])]
