import discord
import asyncio
import datetime
import random
import time

import json

from discord import app_commands
from PapagoLib import Translator
from PandasCsv import pdCsv as pc

with open("./keys.json", 'r') as f:
    cfg = json.load(f)

MY_GUILD = discord.Object(id=cfg['GUILD_ID'])


TR_Cliend_Id = cfg['PapagoTranslator']['TR_Cliend_Id']
TR_Cliend_Secret = cfg['PapagoTranslator']['TR_Cliend_Secret']

LD_Cliend_Id = cfg['PapagoLanguageDetector']['LD_Cliend_Id']
LD_Cliend_Secret = cfg['PapagoLanguageDetector']['LD_Cliend_Secret']

Translator(TR_Cliend_Id, TR_Cliend_Secret, LD_Cliend_Id, LD_Cliend_Secret)

#region Bot initialize
class MyClient(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        #self.tree.copy_global_to(guild=MY_GUILD)
        await self.tree.sync()

client = MyClient()


@client.event
async def on_ready():
    print(f'Logged in as {client.user} (ID: {client.user.id})')
    print('------')
#endregion

# Get result with random blanks
@client.tree.command()
@app_commands.describe(query='변환할 한국어 문자열')
async def kd(
    interaction: discord.Interaction,
    query: app_commands.Range[str, 0, 30]
):
    """한국어 문자열을 무작위 공백을 포함한 번역투 문장으로 변환"""

    if(not Translator.LangDect(query)):
        print(query + ' not')
        await interaction.response.send_message('입력된 문자열이 한국어가 아닙니다.', ephemeral=True)
    else:
        output = Translator.getRes(query)
        await interaction.response.send_message(output, ephemeral=True)

# Get result without random blanks
@client.tree.command()
@app_commands.describe(query='변환할 한국어 문자열')
async def kdnorm(
    interaction: discord.Interaction,
    query: app_commands.Range[str, 0, 30]
):
    """한국어 문자열을 추가적 공백 삽입 없는 번역투 문장으로 변환"""
    output = Translator.getRes(query, False)
    await interaction.response.send_message(output, ephemeral=True)

# Button class
class Entry(discord.ui.View):
    def __init__(self, ebdInteraction):
        super().__init__()
        self.value = None
        self.ebdIntr = ebdInteraction
        self.entryList = []
    
    # Entry a draw
    @discord.ui.button(label="줄 서기", style=discord.ButtonStyle.green, custom_id='entry')
    async def doEntry(self, btnInteraction: discord.Interaction, button: discord.ui.Button):
        if(self.ebdIntr.user.id != btnInteraction.user.id):
            # Append user info to entryList in Tuple
            if((btnInteraction.user.display_name, btnInteraction.user.id) not in self.entryList):
                self.entryList.append((btnInteraction.user.display_name, btnInteraction.user.id))
                await btnInteraction.response.send_message("줄 서기 완료!", ephemeral=True)
            else:
                await btnInteraction.response.send_message("이미 줄 스신거 같은데...", ephemeral=True)
        else:
            await btnInteraction.response.send_message("줄 세운 사람이 줄 스면 어쩌나?", ephemeral=True)


    # Print entryList
    @discord.ui.button(label="참가자 확인", style=discord.ButtonStyle.grey, custom_id='checkEntry')
    async def printEntry(self, btnInteraction: discord.Interaction, button: discord.ui.Button):
        tmpList = []

        if(len(self.entryList) != 0):
            for tmp in self.entryList:
                # Get each user's display name
                tmpList.append(tmp[0])

            tmpStr = '\n'.join(tmpList)

            # Print users' display name
            await btnInteraction.response.send_message(tmpStr, ephemeral=True)
        else:
            await btnInteraction.response.send_message("참가자가 없어요.", ephemeral=True)

# Async function that check the deadline is reached
async def checkOver(endTime):
        while True:
            if(int(time.time()) >= endTime):
                break
            # Check evrey minute.
            await asyncio.sleep(1.0)        
    
        return True

@client.tree.command()
@app_commands.describe(prize='품목', hour='시간', min='분', sec='초')
async def line(interaction: discord.Interaction, prize: str, hour: int, min: int, sec: int):
    """줄을 세운다...!"""

    # Get csv
    pc.load_csv(interaction.guild_id)
    lastIdx = pc.load_csv(interaction.guild_id) + 1
    
    # Get deadline from user
    total_time = 3600 * hour + 60 * min + sec
    start_time = int(time.time())
    ts = start_time + total_time
    
    # Create countdown Task
    task = asyncio.create_task(checkOver(ts))

    # Create button View
    view = Entry(interaction)

    # Initial Embed
    embed = discord.Embed(title=f'"줄 #{lastIdx}"', timestamp=datetime.datetime.now(), colour=discord.Colour.random())
    embed.add_field(name='상품', value=prize, inline=True)
    embed.add_field(name='마감까지 남은 시간', value=f"<t:{ts}:R>", inline=False)
    embed.add_field(name='줄 세운 사람', value=f'<@{interaction.user.id}>')
    
    # Create Thread under channel where command input
    thrd = await interaction.channel.create_thread(name=interaction.user.display_name + '의 ' + prize + '줄', reason='"줄"', type=discord.ChannelType.public_thread)
    thrdMsg = await thrd.send(embed=embed, view=view)

    # Feedback to user
    await interaction.response.send_message('줄 생성 완료! 생성된 스레드를 확인하세요.')

    # Wait for task ends
    isTaskEnd = await task

    if (isTaskEnd):
        if (len(view.entryList) == 0):

            # Temp Data
            dictTemp = {
                    '#': [lastIdx],
                    '품목': [prize],
                    '시작 시간': [datetime.datetime.fromtimestamp(start_time)],
                    '마감 시간': [datetime.datetime.fromtimestamp(ts)],
                    '줄 세운 사람': [f'({interaction.user.id} / {interaction.user.display_name})'],
                    '주작 결과': ['No Entry']
                }

            pc.save_csv(dictTemp)

            # Feedback to Thread and remove view from embed
            embed.clear_fields()
            
            embed.add_field(name='상품', value=prize, inline=True)
            embed.add_field(name='마감 시간', value=f"<t:{ts}:F>", inline=False)
            embed.add_field(name='줄 세운 사람', value=f'<@{interaction.user.id}>')
            embed.add_field(name='"주작 결과"', value='참가자가 없었어요.', inline=False)
            await thrdMsg.edit(embed=embed, view=None)
        else:
                        
            # Get winner and edit embed
            winner = random.choice(view.entryList)

            # Temp Data
            dictTemp = {
                    '#': [lastIdx],
                    '품목': [prize],
                    '시작 시간': [datetime.datetime.fromtimestamp(start_time)],
                    '마감 시간': [datetime.datetime.fromtimestamp(ts)],
                    '줄 세운 사람': [f'{interaction.user.id} / {interaction.user.display_name}'],
                    '주작 결과': [f'{winner[1]} / {winner[0]}']
                }

            pc.save_csv(dictTemp)

            # Feedback to Thread and remove view from embed
            embed.clear_fields()
            
            embed.add_field(name='상품', value=prize, inline=True)
            embed.add_field(name='마감 시간', value=f"<t:{ts}:F>", inline=False)
            embed.add_field(name='줄 세운 사람', value=f'<@{interaction.user.id}>')
            embed.add_field(name='"주작 결과"',
                            value=f'<@{winner[1]}>',
                            inline=False)
            await thrdMsg.edit(embed=embed, view=None)

client.run(cfg['BotToken'])