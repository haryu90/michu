import discord
from discord.ext import commands
from discord import app_commands
import os
from datetime import datetime

TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# =========================
# 데이터 저장
# =========================
warnings = {}
cautions = {}
couples = {}

# =========================
# 역할 설정
# =========================
warnings_roles = {
    1: 1500908102915067919,
    2: 1500908102915067918,
    3: 1500908102915067917,
    4: 1500908102915067916,
}

ROLE_IDS = {
    "여자": 1500908102948622361,
    "남자": 1500908102948622360,
    "10대": 1500908102948622359,
    "20대": 1500908102948622358,
}

# =========================
# 경고/주의 역할 업데이트
# =========================
async def update_role(guild, member, count, type_):
    roles_map = warnings_roles if type_ == "경고" else cautions_roles

    role_id = roles_map.get(count)
    old_role_id = roles_map.get(count - 1)

    if old_role_id:
        old_role = guild.get_role(old_role_id)
        if old_role and old_role in member.roles:
            await member.remove_roles(old_role)

    if role_id:
        role = guild.get_role(role_id)
        if role and role not in member.roles:
            await member.add_roles(role)

# =========================
# 경고 시스템
# =========================

@tree.command(name="경고")
async def 경고(interaction: discord.Interaction, 횟수: int, 대상: discord.Member, 사유: str):
    gid = interaction.guild.id
    uid = 대상.id

    warnings.setdefault(gid, {})
    warnings[gid][uid] = warnings[gid].get(uid, 0) + 횟수

    await update_role(interaction.guild, 대상, warnings[gid][uid], "경고")

    embed = discord.Embed(title="경고 지급", color=discord.Color.red())
    embed.add_field(name="대상", value=대상.mention)
    embed.add_field(name="누적", value=f"{warnings[gid][uid]}회")
    embed.add_field(name="사유", value=사유, inline=False)

    await interaction.response.send_message(embed=embed)


@tree.command(name="경고조회")
async def 경고조회(interaction: discord.Interaction, 대상: discord.Member):
    gid = interaction.guild.id
    uid = 대상.id

    w = warnings.get(gid, {}).get(uid, 0)

    embed = discord.Embed(title="기록", color=discord.Color.blue())
    embed.add_field(name="경고", value=f"{w}회")

    await interaction.response.send_message(embed=embed)


# =========================
# 💖 커플 시스템
# =========================

class LoveView(discord.ui.View):
    def __init__(self, type_):
        super().__init__(timeout=None)
        self.type_ = type_

    @discord.ui.button(label="파기", style=discord.ButtonStyle.danger)
    async def break_up(self, interaction: discord.Interaction, button):
        msg = interaction.message
        gid = interaction.guild.id

        mentions = msg.mentions
        if len(mentions) >= 2:
            u1 = mentions[0].id
            u2 = mentions[1].id

            if gid in couples:
                couples[gid].pop(u1, None)
                couples[gid].pop(u2, None)

        today = datetime.now().strftime("%Y-%m-%d")

        await msg.edit(
            content=f"~~{msg.content}~~\n\n본 {self.type_}은 파기되었습니다.\n{today} ~ {today}",
            view=None
        )

        await interaction.response.send_message("💔 파기 완료", ephemeral=True)


class UserSelect(discord.ui.UserSelect):
    def __init__(self, type_):
        super().__init__(placeholder="상대를 선택하세요", min_values=1, max_values=1)
        self.type_ = type_

    async def callback(self, interaction: discord.Interaction):
        user = self.values[0]
        author = interaction.user
        gid = interaction.guild.id

        couples.setdefault(gid, {})

        if author.id in couples[gid]:
            await interaction.response.send_message("❗ 이미 커플입니다!", ephemeral=True)
            return

        if user.id in couples[gid]:
            await interaction.response.send_message("❗ 상대가 이미 커플입니다!", ephemeral=True)
            return

        couples[gid][author.id] = user.id
        couples[gid][user.id] = author.id

        today = datetime.now().strftime("%Y-%m-%d")

        msg = (
            f"{author.mention} ❤️ {user.mention}\n\n"
            f"{self.type_}이 성사되었습니다!\n"
            f"모두 축하해주세요!\n\n"
            f"{today}"
        )

        message = await interaction.channel.send(msg, view=LoveView(self.type_))
        await message.create_thread(name=f"{author.name}-{user.name} {self.type_}")

        await interaction.response.send_message("✅ 완료!", ephemeral=True)


class SelectUserView(discord.ui.View):
    def __init__(self, type_):
        super().__init__(timeout=60)
        self.add_item(UserSelect(type_))


class SelectView(discord.ui.View):
    @discord.ui.button(label="우결", style=discord.ButtonStyle.primary)
    async def marry(self, interaction: discord.Interaction, button):
        await interaction.response.send_message("상대 선택", view=SelectUserView("우결"), ephemeral=True)

    @discord.ui.button(label="커플", style=discord.ButtonStyle.success)
    async def couple(self, interaction: discord.Interaction, button):
        await interaction.response.send_message("상대 선택", view=SelectUserView("커플"), ephemeral=True)


@tree.command(name="연애")
async def 연애(interaction: discord.Interaction):
    await interaction.response.send_message("원하는 관계 선택", view=SelectView())


@tree.command(name="커플목록")
async def 커플목록(interaction: discord.Interaction):
    gid = interaction.guild.id

    if gid not in couples or not couples[gid]:
        await interaction.response.send_message("❗ 커플 없음")
        return

    checked = set()
    result = ""

    for u, p in couples[gid].items():
        if u in checked:
            continue

        user = interaction.guild.get_member(u)
        partner = interaction.guild.get_member(p)

        if user and partner:
            result += f"{user.mention} ❤️ {partner.mention}\n"

        checked.add(u)
        checked.add(p)

    embed = discord.Embed(title="💖 커플 목록", description=result, color=discord.Color.pink())
    await interaction.response.send_message(embed=embed)


# =========================
# 일반 명령어
# =========================

@bot.command()
async def 이름(ctx, member: discord.Member, *, new_name: str):
    await member.edit(nick=f"𑣲🌸：{new_name}˚₊꒷")
    await ctx.send("✅ 변경 완료")


@bot.command()
async def 역할지급(ctx, member: discord.Member, gender: str, birth: str, path: str):
    year = int("20"+birth) if len(birth)==2 else int(birth)
    age = "20대" if year <= 2007 else "10대"

    roles = [
        ctx.guild.get_role(ROLE_IDS[gender]),
        ctx.guild.get_role(ROLE_IDS[age])
    ]

    await member.add_roles(*roles)
    await ctx.send("✅ 역할 지급 완료")


# =========================

@bot.event
async def on_ready():
    print(f"✅ 로그인: {bot.user}")
    await tree.sync()

bot.run(TOKEN)
