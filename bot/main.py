from nextcord.ext import commands
from nextcord import SlashOption

from bot.logger import get_custom_logger
from bot.db import DB
from bot.enbeds import SimpleEmbed
from bot.model import Word

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
    await client.change_presence(activity=nextcord.Game(name='끝말'))

    # print startup message
    log.info('Bot is ready')
    log.info(f'======================================')
    log.info(f'Logged in as {client.user.name}#{client.user.discriminator} ({client.user.id})')
    log.info(f'Currenly running nextcord {nextcord.__version__} on python {platform.python_version()}')
    log.info('======================================')


@client.slash_command(name='핑', description='봇의 핑을 확인합니다.')
async def ping(ctx):
    await ctx.send(embed=embed.success(f'퐁! {round(client.latency * 1000)}ms'))


@client.slash_command(name='랜덤', description='랜덤한 단어를 추천합니다.')
async def random_word(ctx):
    await ctx.send(db.random_word())


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
    start_msg = await ctx.channel.send(embed=embed.success(f'게임 시작 단어: {start_word}'))
    guild_data.initialize_chain(start_word, start_msg.id)

    db.update_guild(guild_data)


@client.slash_command(name='사전', description='단어를 사전에서 검색합니다.')
async def search(ctx, word: str = SlashOption(name="단어", description="검색할 단어를 입력해 주세요.")):
    log.info(f'{ctx.user.name}({ctx.user.id}) searched: {word}')
    definitions = db.get_definitions(word)
    if len(definitions) == 0:
        await ctx.send(embed=embed.error(f'`{word}`에 대한 정의를 찾을 수 없습니다.'))
        return

    if len(definitions) > 1:
        view = WordDefinitionSelectView(definitions[:25])
        message = await ctx.send(embed=definitions[0].to_embed(), view=view)
        view.message = message  # Store the message reference in the view
    else:
        await ctx.send(embed=definitions[0].to_embed())


@search.on_autocomplete("word")
async def preview(ctx, word: str):
    if word:
        await ctx.response.send_autocomplete(db.autocomplete(word))
    else:
        await ctx.response.send_autocomplete([])


try:
    client.run(config['token'])
except nextcord.errors.LoginFailure:
    log.fatal('Authnetication to Discord failed.')
    exit()
