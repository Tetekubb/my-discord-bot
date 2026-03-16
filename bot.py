import discord
from discord.ext import commands, tasks
from discord import ui
import json
import os
import random
import asyncio
from datetime import datetime, timedelta
from collections import defaultdict

# --- 1. ตั้งค่าพื้นฐาน ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True 
intents.voice_states = True 
bot = commands.Bot(command_prefix='!', intents=intents)

DB_FILE = "bb_database.json"
PRICE_PER_PERSON = 300000 
ARMOR_COUNT = 5 
BANNER_URL = "https://img2.pic.in.th/pic/rainbow-color-1.gif"
TIKTOK_CHANNEL_ID = 1466125220434809166 

BANNED_WORDS = ["ควย", "เย็ด", "หี", "แตด", "มึง", "กู", "เหี้ย", "สัส", "ค.ว.ย", "เ-ย", "ส.ัส", "ตอแหล", "แหล", "สก๊อย", "ส้นตีน", "ควาย", "กุ", "เมิง", "ประสาท", "เขมร", "ลาว", "ขยะ"] 
user_messages = defaultdict(list)

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                default = {
                    "money_msg_id": None, "money_ch_id": None, 
                    "vault_msg_id": None, "vault_ch_id": None,
                    "members_money": {}, 
                    "warehouse": {"total_money": 0, "total_armor": 0, "total_ammo": 0},
                    "link_strikes": {}, "log_ch_id": None
                }
                default.update(data)
                return default
        except: pass
    return {"members_money": {}, "warehouse": {"total_money": 0, "total_armor": 0, "total_ammo": 0}, "link_strikes": {}, "log_ch_id": None}

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

db = load_db()

# --- 2. ระบบลงโทษ & Log ---

async def announce_punishment(member, action, reason):
    embed_pub = discord.Embed(title="🚫 ลงโทษคนทำผิด", description=f"{member.mention} โดนลงโทษเรียบร้อย\n**บทลงโทษ:** {action}\n**สาเหตุ:** {reason}", color=0xff0000)
    embed_pub.set_image(url=BANNER_URL)
    
    log_ch = bot.get_channel(db.get("log_ch_id"))
    if log_ch:
        embed_log = discord.Embed(title="🛡️ BB ANTI LOG", color=0xff0000, timestamp=datetime.now())
        embed_log.add_field(name="คนทำผิด", value=f"{member.mention}", inline=True)
        embed_log.add_field(name="สิ่งที่โดน", value=action, inline=True)
        embed_log.add_field(name="สาเหตุ", value=reason, inline=False)
        embed_log.set_footer(text=f"User ID: {member.id}")
        await log_ch.send(embed=embed_log)
    return embed_pub

# --- 3. ระบบรักษาความปลอดภัย ---

@bot.event
async def on_message(message):
    if message.author == bot.user: return
    
    if "⛓" in message.content or ":chains:" in message.content:
        try:
            await message.delete()
            await message.author.ban(reason="ส่งอีโมจิโซ่")
            pub_emb = await announce_punishment(message.author, "BAN (แบนถาวร)", "ส่งอีโมจิโซ่")
            await message.channel.send(embed=pub_emb)
            return
        except: pass

    is_whitelisted = any(role.name == "Bubble B Diwaa" for role in message.author.roles) or message.author.guild_permissions.administrator
    if not is_whitelisted:
        msg_content = message.content.lower().replace(" ", "").replace(".", "")
        
        now = datetime.now()
        user_id = message.author.id
        user_messages[user_id] = [t for t in user_messages[user_id] if (now - t).total_seconds() < 5]
        user_messages[user_id].append(now)
        if len(user_messages[user_id]) >= 5:
            await message.author.timeout(timedelta(hours=1), reason="สแปม")
            pub_emb = await announce_punishment(message.author, "TIMEOUT 1 ชม.", "สแปมข้อความ")
            await message.channel.send(embed=pub_emb)
            return

        if any(word in msg_content for word in BANNED_WORDS):
            await message.delete()
            await message.author.timeout(timedelta(minutes=30), reason="คำหยาบ")
            pub_emb = await announce_punishment(message.author, "TIMEOUT 30 นาที", f"คำหยาบ: `{message.content}`")
            await message.channel.send(embed=pub_emb)
            return 

        if "http" in msg_content or "discord.gg/" in msg_content:
            allow_link = (message.channel.id == TIKTOK_CHANNEL_ID and "vt.tiktok.com" in msg_content)
            if not allow_link:
                await message.delete()
                u_id = str(message.author.id)
                db["link_strikes"][u_id] = db["link_strikes"].get(u_id, 0) + 1
                save_db(db)
                if db["link_strikes"][u_id] >= 2:
                    await message.author.timeout(timedelta(days=1), reason="แปะลิงก์ซ้ำ")
                    pub_emb = await announce_punishment(message.author, "TIMEOUT 1 วัน", "แปะลิงก์ซ้ำ 2 ครั้ง")
                    await message.channel.send(embed=pub_emb)
                    db["link_strikes"][u_id] = 0; save_db(db)
                else:
                    await message.channel.send(f"⚠️ {message.author.mention} ห้ามแปะลิงก์!", delete_after=5)
                return

    await bot.process_commands(message)

@bot.event
async def on_message_delete(message):
    if message.author == bot.user: return
    msg_check = message.content.lower().replace(" ", "").replace(".", "")
    if any(word in msg_check for word in BANNED_WORDS): return
    log_ch = bot.get_channel(db.get("log_ch_id"))
    if log_ch:
        embed = discord.Embed(title="🗑️ ข้อความถูกลบ", color=0xffa500, timestamp=datetime.now())
        embed.add_field(name="เจ้าของ", value=message.author.mention, inline=True)
        embed.add_field(name="เนื้อหา", value=f"```\n{message.content or 'ไม่มีข้อความ'}\n```", inline=False)
        await log_ch.send(embed=embed)

@bot.event
async def on_voice_state_update(member, before, after):
    log_ch = bot.get_channel(db.get("log_ch_id"))
    if not log_ch: return
    if before.channel != after.channel:
        if not before.channel: txt = f"📥 เข้าห้อง: `{after.channel.name}`"
        elif not after.channel: txt = f"📤 ออกจากห้อง: `{before.channel.name}`"
        else: txt = f"🔄 ย้าย: `{before.channel.name}` -> `{after.channel.name}`"
        await log_ch.send(f"🔊 **{member.display_name}** {txt}")

# --- 4. ระบบการเงิน & คลัง (Vault) ---

async def refresh_money_embed():
    ch = bot.get_channel(db.get("money_ch_id"))
    if not ch: return
    p_list, up_list, count = "", "", 0
    for name, status in db["members_money"].items():
        if "จ่ายแล้ว" in status: p_list += f"🟢 `{name}`\n"; count += 1
        else: up_list += f"🔴 `{name}`\n"
    embed = discord.Embed(title="🏢 BB GANG FINANCIAL", color=0x2b2d31)
    embed.add_field(name="✅ จ่ายแล้ว", value=p_list or "➖", inline=True)
    embed.add_field(name="❌ ค้างจ่าย", value=up_list or "➖", inline=True)
    embed.add_field(name="📊 สรุปยอดสัปดาห์นี้", value=f"```fix\n💰 เงิน: {count*PRICE_PER_PERSON:,}\n🛡️ เกราะ: {count*ARMOR_COUNT} ตัว```", inline=False)
    embed.set_image(url=BANNER_URL)
    view = MoneyTicketView()
    try:
        msg = await ch.fetch_message(db["money_msg_id"]); await msg.edit(embed=embed, view=view)
    except:
        new_msg = await ch.send(embed=embed, view=view); db["money_msg_id"] = new_msg.id; save_db(db)

async def refresh_vault_embed():
    ch = bot.get_channel(db.get("vault_ch_id"))
    if not ch: return
    w = db["warehouse"]
    embed = discord.Embed(title="🏦 BB GANG VAULT ", color=0xf1c40f)
    embed.add_field(name="💰 เงินปัจจุบัน", value=f"```fix\n$ {w['total_money']:,} บาท\n```", inline=True)
    embed.add_field(name="🛡️ เกราะปัจจุบัน", value=f"```fix\n{w['total_armor']:,} ตัว\n```", inline=True)
    embed.add_field(name="🔫 กระสุนปัจจุบัน", value=f"```fix\n{w.get('total_ammo', 0):,} นัด\n```", inline=True)
    embed.set_image(url=BANNER_URL)
    try:
        msg = await ch.fetch_message(db["vault_msg_id"]); await msg.edit(embed=embed)
    except:
        new_msg = await ch.send(embed=embed); db["vault_msg_id"] = new_msg.id; save_db(db)

@bot.command()
async def pay(ctx, name: str, *, status: str):
    try: await ctx.message.delete()
    except: pass
    db["members_money"][name] = status; save_db(db); await refresh_money_embed()

@bot.command()
async def deposit(ctx):
    try: await ctx.message.delete()
    except: pass
    paid_names = [n for n, s in db["members_money"].items() if "จ่ายแล้ว" in s]
    if not paid_names: return await ctx.send("❌ ไม่มีใครจ่ายเลยดึงยอดไม่ได้", delete_after=5)
    db["warehouse"]["total_money"] += (len(paid_names) * PRICE_PER_PERSON)
    db["warehouse"]["total_armor"] += (len(paid_names) * ARMOR_COUNT)
    for name in db["members_money"]: db["members_money"][name] = "🔴 ค้างจ่าย"
    save_db(db); await refresh_money_embed(); await refresh_vault_embed()
    await ctx.send(f"📥 ดึงยอดเข้าหลังบ้านแล้ว", delete_after=5)

@bot.command()
async def add(ctx, type: str, amt: int):
    try: await ctx.message.delete()
    except: pass
    if type in ["money", "armor", "ammo"]:
        db["warehouse"][f"total_{type}"] += amt
        save_db(db); await refresh_vault_embed()

@bot.command()
async def sub(ctx, type: str, amt: int):
    try: await ctx.message.delete()
    except: pass
    if type in ["money", "armor", "ammo"]:
        db["warehouse"][f"total_{type}"] -= amt
        save_db(db); await refresh_vault_embed()

# --- 5. คำสั่งแอดมิน ---

@bot.command()
@commands.has_permissions(administrator=True)
async def setup(ctx, type: str):
    try: await ctx.message.delete()
    except: pass
    if type == "finance": db["money_ch_id"] = ctx.channel.id; await refresh_money_embed()
    elif type == "vault": db["vault_ch_id"] = ctx.channel.id; await refresh_vault_embed()
    save_db(db)

@bot.command()
@commands.has_permissions(administrator=True) # ตั้งให้เฉพาะแอดมินลบได้เพื่อความปลอดภัย
async def delpay(ctx, name: str):
    try: await ctx.message.delete()
    except: pass
    
    if name in db["members_money"]:
        del db["members_money"][name]
        save_db(db)
        await refresh_money_embed()
        await ctx.send(f"🗑️ ลบชื่อ `{name}` ออกจากรายการแล้ว", delete_after=5)
    else:
        await ctx.send(f"❌ ไม่พบชื่อ `{name}` ในรายการ", delete_after=5)

# --------------------------------------------------

@bot.command()
@commands.has_permissions(administrator=True)
async def set_log_room(ctx):
    try: await ctx.message.delete()
    except: pass
    db["log_ch_id"] = ctx.channel.id; save_db(db); await ctx.send(f"✅ ตั้งห้อง Log แล้ว", delete_after=5)

class MoneyTicketView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label='💳 แจ้งจ่ายเงิน', style=discord.ButtonStyle.primary, custom_id='pay_tkt')
    async def pay_btn(self, interaction, button):
        guild = interaction.guild
        ch = await guild.create_text_channel(f"pay-{interaction.user.name}")
        await ch.send(f"ห้องแจ้งจ่ายเงินของ {interaction.user.mention}", view=CloseTicketView())
        await interaction.response.send_message(f"✅ เปิดห้อง {ch.mention} แล้ว", ephemeral=True)

class CloseTicketView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label='🔒 ปิด', style=discord.ButtonStyle.danger)
    async def close(self, interaction, button): await interaction.channel.delete()

@bot.event
async def on_ready():
    print(f'✅ BB System Online!');
    bot.add_view(MoneyTicketView())

token = os.getenv('DISCORD_TOKEN')
bot.run(token)
