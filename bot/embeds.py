import nextcord
from bot.model import Word
import re

pattern = r'<[^>]+>.*?</[^>]+>'


class SimpleEmbed:
    @staticmethod
    def success(text: str) -> nextcord.Embed:
        return nextcord.Embed(title='', description='✅ ' + text, color=0x2B2D31)

    @staticmethod
    def error(text, footer: str = None) -> nextcord.Embed:
        embed = nextcord.Embed(title='', description='❌ ' + text, color=0x2B2D31)
        if footer:
            embed.set_footer(text=footer)
        return embed

    @staticmethod
    def game_start(word: Word, footer: str = None) -> nextcord.Embed:
        description_text = f'첫 단어는 "**{word.word}**" 입니다.'
        embed = nextcord.Embed(title='끝말잇기 시작!', description=description_text, color=0x3598DA)
        embed.add_field(name=f'뜻풀이', value=SimpleEmbed.format_def(word), inline=False)

        if footer:
            embed.set_footer(text=footer)
        return embed

    @staticmethod
    def format_def(word: Word) -> str:
        def_text = ''
        for i, definition_info in enumerate(word.definitions):
            definition = definition_info['definition']
            definition = re.sub(pattern, '', definition)

            def_text += f'`「{i + 1}」` {definition}\n'

        return def_text
