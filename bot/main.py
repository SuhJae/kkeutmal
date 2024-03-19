from nextcord.ext import commands
from nextcord import SlashOption

from bot.logger import get_custom_logger
from bot.db import DB
from bot.embeds import SimpleEmbed
from bot.model import Word
from bot.korean import eh_or_ehro, word_with_initial, el_or_rel

import nextcord
import platform
import json

log = get_custom_logger(__name__)
embed = SimpleEmbed()

with open('config.json', 'r') as file:
    config = json.load(file)

intents = nextcord.Intents.all()
client = commands.Bot(intents=intents)

db = DB()
log.info('Connected to the database')


class WordDefinitionSelect(nextcord.ui.Select):
    def __init__(self, definitions: list[Word]) -> None:
        self.definitions = definitions
        options = []
        for i, definition in enumerate(definitions):
            options.append(
                nextcord.SelectOption(label=f'정의 {i + 1}', value=str(definition.word_number),
                                      description=definition.quick_preview()))

            super().__init__(placeholder='정의를 선택하세요', options=options, max_values=1, min_values=1)

    async def callback(self, interaction: nextcord.Interaction):
        log.info(f'{interaction.user.name}({interaction.user.id}) selected: {interaction.data["values"][0]} in'
                 f' {interaction.message.id}')
        def_id = int(interaction.data['values'][0])
        definition = next((d for d in self.definitions if d.word_number == def_id), None)
        await interaction.message.edit(embed=definition.to_embed())

    def disable(self):
        self.disabled = True


class WordDefinitionSelectView(nextcord.ui.View):
    def __init__(self, definitions: list):
        super().__init__(timeout=300)
        self.select = WordDefinitionSelect(definitions)
        self.add_item(self.select)
        self.message = None

    async def on_timeout(self):
        self.select.disable()  # Disable the dropdown
        if self.message:
            await self.message.edit(view=self)  # Update the message to reflect the disabled state
        self.stop()


# Bot startup
@client.event
async def on_ready():
    # set status
    await client.change_presence(activity=nextcord.Game(name='/도움말 | 끝말잇기'))

    # print startup message
    log.info('Bot is ready')
    log.info('======================================')
    log.info(f'Logged in as {client.user.name}#{client.user.discriminator} ({client.user.id})')
    log.info(f'Currenly running nextcord {nextcord.__version__} on python {platform.python_version()}')
    log.info('======================================')


@client.event
async def on_message(message):
    if message.author.bot:
        return

    if message.content.startswith('> '):
        return

    guild_data = db.get_guild(message.guild.id)
    if guild_data.word_chain_channel_id() == message.channel.id:
        message_content = message.content.strip()
        await message.delete()

        if len(message_content) < 2:
            await message.channel.send(
                embed=embed.error(f'2글자 이상의 단어를 입력해주세요.', footer='팁: "> " 를 메세지 앞에 붙여 채팅메세지를 입력할 수 있습니다!'),
                delete_after=5)
            return

        last_char, altnative_char = guild_data.get_last_character()

        if message_content[0] != last_char and message_content[0] != altnative_char:
            linkable_char = guild_data.get_linkable_char_str()

            await message.channel.send(
                embed=embed.error(
                    text=f'단어의 첫 글자가 일치하지 않습니다.\n"**{linkable_char}**"{eh_or_ehro(last_char[0])} 시작하는 단어를 입력해주세요.',
                    footer=f'팁: "> " 를 메세지 앞에 붙여 채팅메세지를 입력할 수 있습니다!'), delete_after=5)
            return

        if guild_data.is_word_in_chain(message_content):
            await message.channel.send(
                embed=embed.error(f'이미 [여기서]({guild_data.get_word_message_url(message_content)}) 사용된 단어입니다.'),
                delete_after=5)
            return

        if not db.word_exists(message_content):
            await message.channel.send(
                embed=embed.error(f'존재하지 않는 단어입니다.', footer='팁: "> " 를 메세지 앞에 붙여 채팅메세지를 입력할 수 있습니다!'), delete_after=5)
            return

        prev_word = guild_data.get_last_word()
        next_word = db.get_definitions(message_content)[0]

        description_text = f'[{next_word.pronunciations}]' if next_word.pronunciations else ''
        description_text += f' `{next_word.word_type}`' if next_word.word_type else ''
        description_text += f' `{next_word.word_unit}`' if next_word.word_unit else ''

        next_embed = nextcord.Embed(title=f'{word_with_initial(prev_word)} → {word_with_initial(message_content)}',
                                    description=description_text, color=0x2B2D31)
        next_embed.add_field(name=f'뜻풀이', value=SimpleEmbed.format_def(next_word), inline=False)
        next_embed.set_author(name=message.author.display_name, icon_url=message.author.avatar.url)
        next_embed.set_footer(text=f'콤보: {len(guild_data.word_chain)} | 최고 콤보: {guild_data.best_combo}')
        message = await message.channel.send(embed=next_embed)

        guild_data.add_word(message_content, message.id)
        db.update_guild(guild_data)

        if not db.can_play(guild_data):
            game_over_embed = nextcord.Embed(title='게임 오버!',
                                             description=f'더이상 "**{word_with_initial(message_content)}**"'
                                                         f'{el_or_rel(message_content[-1])} 이을 수 있는 단어가 없습니다!',
                                             color=0xE74C3B)
            game_over_embed.set_footer(text=f'최종 콤보: {len(guild_data.word_chain)}')
            await message.channel.send(embed=game_over_embed)

            start_word = db.find_valid_starting_word()
            start_msg = await message.channel.send(embed=embed.game_start(db.get_definitions(start_word)[0]))
            guild_data.initialize_chain(start_word, start_msg.id)
            db.update_guild(guild_data)


@client.slash_command(name='핑', description='봇의 핑을 확인합니다.')
async def ping(ctx):
    is_word_chain_channel = db.get_guild(ctx.guild.id).is_word_chain_channel(ctx.channel.id)
    await ctx.send(embed=embed.success(f'퐁! {round(client.latency * 1000)}ms'), ephemeral=is_word_chain_channel)


@client.slash_command(name='설정', description='현재 명령어를 사용한 채널을 끝말잇기 채널로 설정합니다.', default_member_permissions=8)
async def set_channel(ctx):
    if not ctx.channel.permissions_for(ctx.guild.me).send_messages:
        await ctx.response.send_message(embed=embed.error("끝말잇기 채널로 설정할 수 없습니다. 봇이 메시지를 보낼 권한이 없습니다."), ephemeral=True)
        return
    if not ctx.channel.permissions_for(ctx.guild.me).manage_messages:
        await ctx.response.send_message(embed=embed.error("끝말잇기 채널로 설정할 수 없습니다. 봇이 메시지를 수정할 권한이 없습니다."), ephemeral=True)
        return

    guild_data = db.get_guild(ctx.guild.id)
    existing_channel = guild_data.word_chain_channel_id()
    guild_data.word_chain_channel = ctx.channel.id
    if existing_channel is None:
        await ctx.response.send_message(embed=embed.success(f'끝말잇기 채널이 {ctx.channel.mention}로 설정되었습니다.'),
                                        ephemeral=True)
    else:
        await ctx.response.send_message(
            embed=embed.success(f"끝말잇기 채널이 <#{existing_channel}>에서 현재 채널로 변경 되었습니다."),
            ephemeral=True)

    start_word = db.find_valid_starting_word()
    start_msg = await ctx.channel.send(embed=embed.game_start(db.get_definitions(start_word)[0]))
    guild_data.initialize_chain(start_word, start_msg.id)
    db.update_guild(guild_data)


@client.slash_command(name='재시작', description='끝말잇기 게임을 재시작합니다.')
async def restart(ctx):
    guild_data = db.get_guild(ctx.guild.id)
    start_word = db.find_valid_starting_word()
    await ctx.send(embed=embed.success('끝말잇기 게임이 재시작되었습니다.'))
    start_msg = await ctx.channel.send(embed=embed.game_start(db.get_definitions(start_word)[0]))
    guild_data.initialize_chain(start_word, start_msg.id)
    db.update_guild(guild_data)


@client.slash_command(name='뜻풀이', description='단어의 뜻을 확인합니다.')
async def search(ctx, word: str = SlashOption(name="단어", description="검색할 단어를 입력해 주세요.")):
    log.info(f'{ctx.user.name}({ctx.user.id}) searched: {word}')
    is_word_chain_channel = db.get_guild(ctx.guild.id).is_word_chain_channel(ctx.channel.id)

    if is_word_chain_channel:
        await ctx.response.send_message(embed=embed.error('끝말잇기 채널에서는 사용할 수 없는 명령어입니다.'), ephemeral=True)
        return

    definitions = db.get_definitions(word)
    if len(definitions) == 0:
        await ctx.send(embed=embed.error(f'`{word}`에 대한 뜻풀이를 찾을 수 없습니다.'), ephemeral=True)
        return

    if len(definitions) > 1:
        view = WordDefinitionSelectView(definitions[:25])
        message = await ctx.send(embed=definitions[0].to_embed(), view=view)
        view.message = message
    else:
        await ctx.send(embed=definitions[0].to_embed())


@search.on_autocomplete("word")
async def preview(ctx, word: str):
    if word:
        await ctx.response.send_autocomplete(db.autocomplete(word))
    else:
        await ctx.response.send_autocomplete([])


@client.slash_command(name='도움말', description='봇의 명령어 목록을 확인합니다.')
async def help_menu(ctx):
    is_word_chain_channel = db.get_guild(ctx.guild.id).is_word_chain_channel(ctx.channel.id)

    help_embed = nextcord.Embed(title='도움말', description='끝말잇기 봇의 명령어 목록입니다.', color=0x2B2D31)
    help_embed.add_field(name='`/핑`', value='봇의 핑을 확인합니다.', inline=False)
    help_embed.add_field(name='`/설정`', value='현재 명령어를 사용한 채널을 끝말잇기 채널로 설정합니다.', inline=False)
    help_embed.add_field(name='`/재시작`', value='끝말잇기 게임을 재시작합니다.', inline=False)
    help_embed.add_field(name='`/뜻풀이`', value='단어의 뜻을 확인합니다.', inline=False)
    help_embed.add_field(name='`/도움말`', value='봇의 명령어 목록을 확인합니다.', inline=False)
    await ctx.send(embed=help_embed, ephemeral=is_word_chain_channel)


try:
    client.run(config['token'])
except nextcord.errors.LoginFailure:
    log.fatal('Authnetication to Discord failed.')
    exit()
