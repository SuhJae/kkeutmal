from typing import Dict, Any


class Word:
    def __init__(self, word_dict: Dict[str, Any]) -> None:
        self.word = word_dict.get('word')
        self.word_number = word_dict.get('word_number')
        self.pronunciations = word_dict.get('pronunciations', [])
        self.word_type = word_dict.get('word_type', "Unknown")
        self.word_unit = word_dict.get('word_unit', "Unknown")
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
