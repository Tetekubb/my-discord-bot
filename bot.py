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
PRICE_PER_PERSON = 400000 
ARMOR_COUNT = 5
BANNER_URL = "https://img2.pic.in.th/pic/rainbow-color-1.gif"
WHEEL_GIF = "https://i.gifer.com/Vp3R.gif"
TIKTOK_CHANNEL_ID = 1466125220434809166

# รายชื่อคำหยาบ (รวมคำหลบ) 
BANNED_WORDS = ["ควย", "เย็ด", "หี", "แตด", "มึง", "กู", "เหี้ย", "สัส", "ค.ว.ย", "เ-ย", "ส.ัส", "ตอแหล", "แหล", "สก๊อย", "ส้นตีน", "ควาย", "กุ", "เมิง", "ประสาท", "เงี่ยน", "จู๋", "เขมร", "ลาบ", "ลาว", "กระจอก", "กาก", "ควE"] 

# สำหรับระบบกันสแปม
user_messages = defaultdict(list)

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                default = {
                    "money_msg_id": None, "money_ch_id": None, "members_money": {},
                    "vault_msg_id": None, "vault_ch_id": None,
                    "warehouse": {"total_money": 0, "total_armor": 0, "total_ammo": 0},
                    "profile_msg_id": None, "profile_ch_id": None, "profiles": {},
                    "auto_ann_ch_id": None, "ticket_category_id": None,
                    "land_members": [], "airdrop_members": [], "story_members": [], "leave_airdrop": [],
                    "land_list_id": None, "land_ch_id": None,
                    "airdrop_list_id": None, "airdrop_ch_id": None,
                    "story_list_id": None, "story_ch_id": None,
                    "leave_list_id": None, "leave_ch_id": None,
                    "link_strikes": {},
                    "log_ch_id": None
                }
                default.update(data)
                return default
        except: pass
    return {
        "members_money": {}, "profiles": {},
        "warehouse": {"total_money": 0, "total_armor": 0, "total_ammo": 0},
        "land_members": [], "airdrop_members": [], "story_members": [], "leave_airdrop": [],
        "link_strikes": {}, "log_ch_id": None
    }

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

db = load_db()

# ฟังก์ชันส่ง Log การลงโทษ
async def send_punish_log(member, action, reason):
    log_ch = bot.get_channel(db.get("log_ch_id"))
    if log_ch:
        embed = discord.Embed(title="🛡️ ระบบลงโทษอัตโนมัติ", color=0xff0000, timestamp=datetime.now())
        embed.add_field(name="ผู้กระทำผิด", value=member.mention, inline=True)
        embed.add_field(name="บทลงโทษ", value=action, inline=True)
        embed.add_field(name="สาเหตุ", value=reason, inline=False)
        embed.set_footer(text=f"ID: {member.id}")
        await log_ch.send(embed=embed)

# --- 2. ระบบ Anti-Link, Badwords, Anti-Spam, Anti-Emoji ---
@bot.event
async def on_message(message):
    if message.author == bot.user: return
    
    # 🚫 ระบบดักจับอีโมจิโซ่ (⛓) - แบนทันที
    if "⛓" in message.content or ":chains:" in message.content:
        try:
            await message.author.ban(reason="ส่งมาทำไมอันนี้ กูแบน")
            await send_punish_log(message.author, "BAN (แบนถาวร)", "ส่งอีโมจิโซ่ (⛓️)")
            await message.delete()
            return
        except Exception as e:
            print(f"Error Banning: {e}")

    # ตรวจสอบข้อยกเว้นสำหรับยศ Member หรือ Admin
    is_whitelisted = any(role.name == "ִ ࣪ ˖ ࣪membergang24 ! ᰔ ִ" for role in message.author.roles) or message.author.guild_permissions.administrator

    if not is_whitelisted:
        msg_content = message.content.lower().replace(" ", "").replace(".", "").replace("-", "")
        
        # 🚫 กันสแปม: 5 ข้อความใน 5 วินาที
        now = datetime.now()
        user_id = message.author.id
        user_messages[user_id] = [msg_time for msg_time in user_messages[user_id] if (now - msg_time).total_seconds() < 5]
        user_messages[user_id].append(now)
        
        if len(user_messages[user_id]) >= 5:
            try:
                until_spam = discord.utils.utcnow() + timedelta(hours=1)
                await message.author.timeout(until_spam, reason="สแปมข้อความ (5 ข้อความใน 5 วินาที)")
                await message.channel.send(f"🚫 {message.author.mention} หมดเวลาชิวไปอีก **1 ชั่วโมง** เนื่องจากสแปมข้อความ!")
                await send_punish_log(message.author, "TIMEOUT (1 ชม.)", "สแปมข้อความ")
                return
            except: pass

        # 🚫 ตรวจสอบคำหยาบ
        if any(word in msg_content for word in BANNED_WORDS):
            try:
                await message.delete()
                until = discord.utils.utcnow() + timedelta(minutes=30)
                await message.author.timeout(until, reason="งดใช้คำหยาบนะไอ่อ้วนน")
                embed = discord.Embed(
                    title="🚫 ลงโทษคนทำผิด",
                    description=f"{message.author.mention} โดนหมดเวลาไปชิวๆ **30 นาที**\n**สาเหตุ:** พิมพ์คำหยาบ",
                    color=0xff0000
                )
                await message.channel.send(embed=embed)
                await send_punish_log(message.author, "TIMEOUT (30 นาที)", f"พิมพ์คำหยาบ: {message.content}")
                return 
            except Exception as e:
                print(f"Error Badword Timeout: {e}")

        # 🚫 ตรวจสอบลิงก์ (ยกเว้น TikTok ในห้องที่กำหนด)
        if "http" in msg_content or "discord.gg/" in msg_content:
            allow_link = (message.channel.id == TIKTOK_CHANNEL_ID and "vt.tiktok.com" in msg_content)
            if not allow_link:
                try: await message.delete()
                except: pass
                u_id = str(message.author.id)
                db["link_strikes"][u_id] = db["link_strikes"].get(u_id, 0) + 1
                save_db(db)
                if db["link_strikes"][u_id] >= 2:
                    try:
                        until_link = discord.utils.utcnow() + timedelta(days=1)
                        await message.author.timeout(until_link, reason="แปะลิงก์ซ้ำ (ครบ 2 ครั้ง)")
                        await message.channel.send(f"🚫 {message.author.mention} ถูกพักการใช้งาน 1 วันเนื่องจากแปะลิงก์เกินกำหนด!")
                        await send_punish_log(message.author, "TIMEOUT (1 วัน)", "แปะลิงก์ซ้ำครบ 2 ครั้ง")
                        db["link_strikes"][u_id] = 0 
                        save_db(db)
                    except Exception as e: print(f"Error timeout: {e}")
                else:
                    await message.channel.send(f"⚠️ {message.author.mention} ห้ามแปะลิงก์ในที่นี้!")
                    await send_punish_log(message.author, "WARNING (เตือน)", "พยายามแปะลิงก์ครั้งที่ 1")
                return
                
    await bot.process_commands(message)

# --- 3. ระบบ Log (ลบข้อความ & Voice) ---

@bot.event
async def on_message_delete(message):
    if message.author == bot.user: return
    msg_check = message.content.lower().replace(" ", "").replace(".", "")
    if any(word in msg_check for word in BANNED_WORDS): return
    log_ch = bot.get_channel(db.get("log_ch_id"))
    if log_ch:
        embed = discord.Embed(title="🗑️ ข้อความถูกลบ", color=0xffa500, timestamp=datetime.now())
        embed.add_field(name="คนลบ/เจ้าของข้อความ", value=message.author.mention, inline=True)
        embed.add_field(name="ห้อง", value=message.channel.mention, inline=True)
        embed.add_field(name="เนื้อหาที่ถูกลบ", value=f"```\n{message.content or 'ไม่มีเนื้อหา (อาจเป็นรูปภาพหรือไฟล์)'}\n```", inline=False)
        await log_ch.send(embed=embed)

@bot.event
async def on_voice_state_update(member, before, after):
    log_ch = bot.get_channel(db.get("log_ch_id"))
    if not log_ch: return
    if before.channel is None and after.channel is not None:
        await log_ch.send(f"🔊 **{member.display_name}** เข้าห้องเสียง: `{after.channel.name}`")
    elif before.channel is not None and after.channel is None:
        await log_ch.send(f"🔇 **{member.display_name}** ออกจากห้องเสียง: `{before.channel.name}`")
    elif before.channel is not None and after.channel is not None and before.channel != after.channel:
        await log_ch.send(f"🔄 **{member.display_name}** ย้ายห้อง: `{before.channel.name}` ➡️ `{after.channel.name}`")

# --- 4. ระบบการเงิน & คลัง (Vault) ---

async def refresh_money_embed():
    if not (channel := bot.get_channel(db.get("money_ch_id"))): return
    total, paid_c, p_list, up_list = 0, 0, "", ""
    for name, status in db["members_money"].items():
        if "จ่ายแล้ว" in status: p_list += f"🟢 `{name}`\n"; total += PRICE_PER_PERSON; paid_c += 1
        else: up_list += f"🔴 `{name}`\n"
    embed = discord.Embed(title="🏢 24 GANG FINANCIAL", color=0x2b2d31)
    embed.add_field(name="✅ จ่ายแล้ว", value=p_list or "➖", inline=True)
    embed.add_field(name="❌ ค้างจ่าย", value=up_list or "➖", inline=True)
    embed.add_field(name="📊 สรุปของแก๊งค์", value=f"```fix\n💰 เงินตอนนี้: {total:,} | ✅ {paid_c} | ❌ {len(db['members_money'])-paid_c}\n🛡️ เกราะตอนนี้: {paid_c * ARMOR_COUNT} ตัว```", inline=False)
    embed.set_image(url=BANNER_URL)
    view = MoneyTicketView()
    try: msg = await channel.fetch_message(db["money_msg_id"]); await msg.edit(embed=embed, view=view)
    except: new_msg = await channel.send(embed=embed, view=view); db["money_msg_id"] = new_msg.id; save_db(db)

async def refresh_vault_embed():
    ch = bot.get_channel(db.get("vault_ch_id"))
    if not ch: return
    w = db["warehouse"]
    embed = discord.Embed(title="🏦 24 GANG VAULT", color=0xf1c40f)
    embed.add_field(name="💰 เงินปัจจุบัน", value=f"```fix\n$ {w['total_money']:,} บาท\n```", inline=True)
    embed.add_field(name="🛡️ เกราะปัจจุบัน", value=f"```fix\n{w['total_armor']:,} ตัว\n```", inline=True)
    embed.add_field(name="🔫 กระสุนปัจจุบัน", value=f"```fix\n{w.get('total_ammo', 0):,} นัด\n```", inline=True)
    embed.set_image(url=BANNER_URL)
    try:
        msg = await ch.fetch_message(db["vault_msg_id"]); await msg.edit(embed=embed)
    except:
        new_msg = await ch.send(embed=embed); db["vault_msg_id"] = new_msg.id; save_db(db)

# ดึงยอดเงิน+เกราะของคนที่จ่ายแล้วเข้าคลัง แล้วรีเซ็ตทุกคนเป็นค้างจ่าย
@bot.command()
@commands.has_permissions(administrator=True)
async def deposit(ctx):
    try: await ctx.message.delete()
    except: pass
    paid_names = [n for n, s in db["members_money"].items() if "จ่ายแล้ว" in s]
    if not paid_names: return await ctx.send("❌ ไม่มีใครจ่ายเลยดึงยอดไม่ได้", delete_after=5)
    db["warehouse"]["total_money"] += (len(paid_names) * PRICE_PER_PERSON)
    db["warehouse"]["total_armor"] += (len(paid_names) * ARMOR_COUNT)
    for name in db["members_money"]: db["members_money"][name] = "🔴 ค้างจ่าย"
    save_db(db)
    await refresh_money_embed()
    await refresh_vault_embed()
    await ctx.send(f"📥 ดึงยอดเข้าคลังแล้ว | เงิน +{len(paid_names)*PRICE_PER_PERSON:,} | เกราะ +{len(paid_names)*ARMOR_COUNT} ตัว", delete_after=5)

# เพิ่มของเข้าคลัง: !add [money/armor/ammo] [จำนวน]
@bot.command()
@commands.has_permissions(administrator=True)
async def add(ctx, type: str, amt: int):
    try: await ctx.message.delete()
    except: pass
    if type in ["money", "armor", "ammo"]:
        db["warehouse"][f"total_{type}"] += amt
        save_db(db)
        await refresh_vault_embed()
        await ctx.send(f"✅ เพิ่ม {type} +{amt:,} เข้าคลังแล้ว", delete_after=5)
    else:
        await ctx.send("❌ ประเภทไม่ถูกต้อง ใช้ได้: `money`, `armor`, `ammo`", delete_after=5)

# ลดของออกจากคลัง: !sub [money/armor/ammo] [จำนวน]
@bot.command()
@commands.has_permissions(administrator=True)
async def sub(ctx, type: str, amt: int):
    try: await ctx.message.delete()
    except: pass
    if type in ["money", "armor", "ammo"]:
        db["warehouse"][f"total_{type}"] -= amt
        save_db(db)
        await refresh_vault_embed()
        await ctx.send(f"✅ หัก {type} -{amt:,} จากคลังแล้ว", delete_after=5)
    else:
        await ctx.send("❌ ประเภทไม่ถูกต้อง ใช้ได้: `money`, `armor`, `ammo`", delete_after=5)

# --- 5. ระบบแจ้งเตือนค้างจ่าย ---

@tasks.loop(seconds=60)
async def midnight_debt_announcer():
    now = datetime.now()
    if now.hour == 0 and now.minute == 0:
        target_ch_id = 1486304886307033099 
        channel = bot.get_channel(target_ch_id)
        if not channel: return
        unpaid_list = [name for name, status in db["members_money"].items() if "จ่ายแล้ว" not in status]
        if unpaid_list:
            names_text = "\n".join([f"• {name}" for name in unpaid_list])
            embed = discord.Embed(title="📢 แจ้งเตือนคนค้างจ่ายเงินและเกราะ!", description=f"เที่ยงคืนแล้วนะจ๊ะ คนที่ยังไม่จ่าย:\n```\n{names_text}\n```\nจ่ายเงิน {PRICE_PER_PERSON:,} + เกราะ {ARMOR_COUNT} ตัว ด้วยน้าา!", color=0xffa500)
            embed.set_image(url=BANNER_URL)
            await channel.send(embed=embed)

async def send_test_debt_announcement(interaction: discord.Interaction):
    target_ch_id = 1486304886307033099 
    channel = bot.get_channel(target_ch_id)
    if not channel: return await interaction.response.send_message("❌ หาห้องแจ้งเตือนไม่เจอ!", ephemeral=True)
    unpaid_list = [name for name, status in db["members_money"].items() if "จ่ายแล้ว" not in status]
    if unpaid_list:
        names_text = "\n".join([f"• {name}" for name in unpaid_list])
        embed = discord.Embed(title="📢 แจ้งเตือนคนยังไม่ได้จ่ายเงินแก๊งค์!", description=f"รายชื่อคนยังไม่จ่ายเงินแก๊งค์:\n```\n{names_text}\n```\nรีบมาจ่ายเงิน {PRICE_PER_PERSON:,} และเกราะ {ARMOR_COUNT} ตัว ด้วยนะ! ✅", color=0xffa500)
        embed.set_image(url=BANNER_URL)
        await channel.send(embed=embed)
        await interaction.response.send_message("✅ ส่งประกาศทดสอบไปที่ห้องแจ้งเตือนแล้ว!", ephemeral=True)
    else: await interaction.response.send_message("✅ เอาดีย์จ่ายครบหมดแล้วหรอเนี่ยย!", ephemeral=True)

@bot.command()
@commands.has_permissions(administrator=True)
async def test_debt(ctx):
    try: await ctx.message.delete()
    except: pass
    target_ch_id = 1486304886307033099
    channel = bot.get_channel(target_ch_id)
    if not channel: return await ctx.send(f"❌ หาห้อง ID {target_ch_id} ไม่เจอ!", delete_after=5)
    unpaid_list = [name for name, status in db["members_money"].items() if "จ่ายแล้ว" not in status]
    if unpaid_list:
        names_text = "\n".join([f"• {name}" for name in unpaid_list])
        embed = discord.Embed(title="📢 แจ้งเตือนคนที่ยังไม่ได้จ่ายเงินแก๊งค์!", description=f"รายชื่อคนไม่ยังไม่ได้จ่ายเงิน:\n```\n{names_text}\n```\nรีบมาจ่ายเงิน {PRICE_PER_PERSON:,} และเกราะ {ARMOR_COUNT} ตัว ด้วยนะ! ✅", color=0xffa500)
        embed.set_image(url=BANNER_URL)
        await channel.send(embed=embed)
        await ctx.send("✅ ส่งประกาศทดสอบไปที่ห้องแจ้งเตือนแล้ว!", delete_after=5)
    else: await ctx.send("✅ เอาดีจ่ายตรบหมดแล้วหรอเนี่ยย!", delete_after=5)

# --- 6. UI Classes ---

class MoneyTicketView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label='💳 แจ้งจ่ายเงิน', style=discord.ButtonStyle.primary, custom_id='btn_pay_slip_ticket')
    async def pay_ticket(self, interaction: discord.Interaction, button: ui.Button):
        guild = interaction.guild; cat_id = db.get("ticket_category_id")
        category = discord.utils.get(guild.categories, id=cat_id) if cat_id else None
        accountant_role = discord.utils.get(guild.roles, name="꒰˚𝑻𝒉𝒆 𝒃𝒐𝒔𝒔!")
        overwrites = {guild.default_role: discord.PermissionOverwrite(read_messages=False), interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True), guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)}
        if accountant_role: overwrites[accountant_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        ticket_ch = await guild.create_text_channel(name=f"pay-{interaction.user.name}", category=category, overwrites=overwrites)
        embed = discord.Embed(title="💳 บริการแจ้งจ่ายเงิน", description=f"สวัสดีคุณ {interaction.user.mention}\nรอฝ่ายบัญชีตอบเพื่อชำระเงิน\n\n**ยอดที่ต้องชำระ:** `{PRICE_PER_PERSON:,}` + **เกราะ {ARMOR_COUNT} ตัว**\n**รายละเอียด:** ถ้าฝ่ายบัญชีไม่ตอบแท็กเรียกได้เลย", color=0x3498db)
        embed.set_image(url=BANNER_URL)
        mention_text = accountant_role.mention if accountant_role else ""
        await ticket_ch.send(content=mention_text, embed=embed, view=CloseTicketView())
        await interaction.response.send_message(f"✅ สร้างช่องแจ้งจ่ายเงินแล้วที่ {ticket_ch.mention}", ephemeral=True)

async def refresh_profile_embed():
    if not (channel := bot.get_channel(db.get("profile_ch_id"))): return
    txt = "".join([f"👤 **ชื่อ:** `{n}` | **อายุ:** `{a}` ปี\n" for n, a in db["profiles"].items()])
    embed = discord.Embed(title="📋 รายชื่อสมาชิกแก๊งค์ 24", description=txt or "➖ ไม่มีข้อมูล", color=0x3498db)
    embed.set_image(url=BANNER_URL)
    try: msg = await channel.fetch_message(db["profile_msg_id"]); await msg.edit(embed=embed)
    except: new_msg = await channel.send(embed=embed); db["profile_msg_id"] = new_msg.id; save_db(db)

async def refresh_specific_list(mode):
    ch_id = db.get(f"{mode}_ch_id"); msg_id = db.get(f"{mode}_list_id")
    if not ch_id or not (channel := bot.get_channel(ch_id)): return
    titles = {'land': '🏰 รายชื่อเล่นแลนด์', 'airdrop': '📦 รายชื่อแอร์ดรอป', 'story': '🎬 รายชื่อเล่นสตอรี่', 'leave': '💤 รายชื่อลาแอร์ดรอป'}
    colors = {'land': 0x3498db, 'airdrop': 0x2ecc71, 'story': 0xe74c3c, 'leave': 0x95a5a6}
    members = db.get(f"{mode}_members" if mode != 'leave' else "leave_airdrop", [])
    list_text = "\n".join([f"{i+1}. {n}" for i, n in enumerate(members)]) or "➖ ยังไม่มีข้อมูล"
    embed = discord.Embed(title=titles[mode], description=f"```\n{list_text}\n```", color=colors[mode])
    embed.set_image(url=BANNER_URL); embed.set_footer(text=f"อัปเดตล่าสุด: {datetime.now().strftime('%H:%M:%S')}")
    try: msg = await channel.fetch_message(msg_id); await msg.edit(embed=embed)
    except: new_msg = await channel.send(embed=embed); db[f"{mode}_list_id"] = new_msg.id; save_db(db)

class LeaveModal(ui.Modal, title='📝 แจ้งลาแอร์ดรอป'):
    name = ui.TextInput(label='ชื่อเล่น', placeholder='ระบุชื่อ...', min_length=2)
    age = ui.TextInput(label='อายุ', placeholder='ระบุอายุ...', max_length=2)
    reason = ui.TextInput(label='เหตุผลที่ลา', style=discord.TextStyle.paragraph, placeholder='ระบุเหตุผลการลา...')
    async def on_submit(self, interaction: discord.Interaction):
        info = f"👤 {self.name.value} ({self.age.value} ปี) - {self.reason.value}"
        db["leave_airdrop"].append(info); save_db(db); await refresh_specific_list('leave')
        await interaction.response.send_message("✅ บันทึกข้อมูลการลาเรียบร้อย", ephemeral=True)

class NameInputModal(ui.Modal):
    def __init__(self, mode):
        self.mode = mode
        titles = {'land': 'ลงชื่อเล่นแลนด์', 'airdrop': 'ลงชื่อแอร์ดรอป', 'story': 'ลงชื่อเล่นสตอรี่'}
        super().__init__(title=titles.get(mode))
    name = ui.TextInput(label='กรอกชื่อผู้ลงสมัคร', placeholder='กรอกชื่อเล่นตัวเอง....', min_length=2)
    async def on_submit(self, interaction: discord.Interaction):
        user_name = self.name.value; list_key = f"{self.mode}_members"
        if user_name not in db[list_key]:
            db[list_key].append(user_name); save_db(db); await refresh_specific_list(self.mode)
            await interaction.response.send_message(f"✅ บันทึกชื่อ `{user_name}` ลง log เรียบร้อย", ephemeral=True)
        else: await interaction.response.send_message(f"❌ ชื่อนี้มีอยู่แล้วในรายการ", ephemeral=True)

class ActivitySignupView(ui.View):
    def __init__(self, mode):
        super().__init__(timeout=None); self.mode = mode
        if mode == 'leave':
            btn = ui.Button(label="📝 กดเพื่อแจ้งลา", style=discord.ButtonStyle.secondary, custom_id="btn_leave_act")
            btn.callback = self.leave_callback
        else:
            style = discord.ButtonStyle.primary if mode == 'land' else discord.ButtonStyle.success if mode == 'airdrop' else discord.ButtonStyle.danger
            label = "🏰 ลงชื่อเล่นแลนด์" if mode == 'land' else "📦 ลงชื่อแอร์ดรอป" if mode == 'airdrop' else "🎬 ลงชื่อเล่นสตอรี่"
            btn = ui.Button(label=label, style=style, custom_id=f"btn_signup_{mode}"); btn.callback = self.signup_callback
        self.add_item(btn)
    async def signup_callback(self, interaction: discord.Interaction): await interaction.response.send_modal(NameInputModal(self.mode))
    async def leave_callback(self, interaction: discord.Interaction): await interaction.response.send_modal(LeaveModal())

class AdminClearView(ui.View):
    def __init__(self, mode):
        super().__init__(timeout=None); self.mode = mode
        btn = ui.Button(label="🧹 ล้างรายชื่อ", style=discord.ButtonStyle.secondary, custom_id=f"clear_btn_{mode}")
        btn.callback = self.clear_callback; self.add_item(btn)
    async def clear_callback(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator: return await interaction.response.send_message("❌ เฉพาะ Admin", ephemeral=True)
        db[f"{self.mode}_members" if self.mode != 'leave' else "leave_airdrop"] = []; save_db(db); await refresh_specific_list(self.mode)
        await interaction.response.send_message(f"🧹 ล้างรายชื่อ {self.mode} แล้ว", ephemeral=True)

class WheelActionView(ui.View):
    def __init__(self, contestants, title_name):
        super().__init__(timeout=None); self.contestants = contestants; self.title_name = title_name
    @ui.button(label='🎡 เริ่มสุ่มวงล้อ', style=discord.ButtonStyle.success, custom_id='btn_start_spin_final')
    async def start_spin(self, interaction: discord.Interaction, button: ui.Button):
        if not interaction.user.guild_permissions.administrator: return await interaction.response.send_message("❌ เฉพาะแอดมินเท่านั้นที่สุ่มได้!", ephemeral=True)
        await interaction.response.send_message(f"🌀 กำลังสุ่ม: **{self.title_name}**", ephemeral=True)
        embed = discord.Embed(title=f"🎡 {self.title_name}", description="วงล้อกำลังหมุน... ใครจะเป็นผู้โชคดี?!", color=0xffaa00); embed.set_image(url=WHEEL_GIF); spin_msg = await interaction.channel.send(embed=embed)
        await asyncio.sleep(5); winner = random.choice(self.contestants); win_embed = discord.Embed(title=f"🎉 สุ่มเสร็จสิ้น: {self.title_name}", description=f"ยินดีด้วยกับคุณ: **{winner}**", color=0x00ff00); win_embed.set_image(url=BANNER_URL); win_embed.set_footer(text=f"สุ่มโดย: {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
        await spin_msg.edit(content=f"🔔 ผลการสุ่ม: **{self.title_name}**", embed=win_embed)

class WheelSetupModal(ui.Modal, title='🎡 ตั้งค่าการสุ่มวงล้อ'):
    channel_id = ui.TextInput(label='Channel ID ห้องที่จะส่งระบบสุ่ม', placeholder='ไอดีห้อง...', min_length=15, required=True)
    wheel_title = ui.TextInput(label='หัวข้อการสุ่ม', placeholder='ระบุหัวข้อที่นี่...', required=True)
    names = ui.TextInput(label='รายชื่อผู้มีสิทธิ์ (แยกบรรทัดใหม่)', style=discord.TextStyle.paragraph, placeholder='ชื่อ A\nชื่อ B...', required=True)
    async def on_submit(self, interaction: discord.Interaction):
        try:
            target_channel = bot.get_channel(int(self.channel_id.value)); list_names = [n.strip() for n in self.names.value.split('\n') if n.strip()]
            if not target_channel or not list_names: raise Exception()
            display_names = "\n".join([f"• {n}" for n in list_names])
            embed = discord.Embed(title=f"🎡 ระบบสุ่ม: {self.wheel_title.value}", description=f"**รายชื่อผู้มีสิทธิ์:**\n```\n{display_names}\n```\n*กดปุ่มด้านล่างเพื่อเริ่มสุ่ม*", color=0xffaa00); embed.set_image(url=BANNER_URL)
            await target_channel.send(embed=embed, view=WheelActionView(list_names, self.wheel_title.value))
            await interaction.response.send_message(f"✅ ส่งระบบสุ่มหัวข้อ **{self.wheel_title.value}** แล้ว!", ephemeral=True)
        except: await interaction.response.send_message("❌ Error: ID ห้องผิดพลาด!", ephemeral=True)

class VoteView(ui.View):
    def __init__(self, title, options):
        super().__init__(timeout=None); self.title = title; self.options = options; self.votes = {opt: [] for opt in options}
        for opt in options:
            btn = ui.Button(label=opt, style=discord.ButtonStyle.secondary, custom_id=f"vote_{opt}"); btn.callback = self.make_callback(opt); self.add_item(btn)
    def make_callback(self, opt):
        async def callback(interaction: discord.Interaction):
            user_id = interaction.user.id
            for key in self.votes:
                if user_id in self.votes[key]: self.votes[key].remove(user_id)
            self.votes[opt].append(user_id); await interaction.response.edit_message(embed=self.create_embed(), view=self)
        return callback
    def create_embed(self):
        desc = ""
        for opt, users in self.votes.items():
            count = len(users); desc += f"**{opt}**\n┣ 🗳️ {count} คะแนน\n┗ 👥 {', '.join([f'<@{u}>' for u in users[:5]])}{' ...' if count > 5 else ''}\n\n"
        embed = discord.Embed(title=f"📊 โหวต: {self.title}", description=desc or "ไม่มีข้อมูล", color=0x3498db); embed.set_image(url=BANNER_URL); embed.set_footer(text="คลิกปุ่มด้านล่างเพื่อเลือกโหวต (เปลี่ยนใจได้)"); return embed

class VoteSetupModal(ui.Modal, title='📊 ตั้งค่าการโหวต'):
    channel_id = ui.TextInput(label='Channel ID ห้องที่จะส่งโหวต', placeholder='ไอดีห้อง...', min_length=15, required=True)
    vote_title = ui.TextInput(label='หัวข้อการโหวต', placeholder='เช่น เลือกกิจกรรมคืนนี้...', required=True)
    options = ui.TextInput(label='ตัวเลือกการโหวต (แยกบรรทัดใหม่)', style=discord.TextStyle.paragraph, placeholder='ตัวเลือก 1\nตัวเลือก 2...', required=True)
    async def on_submit(self, interaction: discord.Interaction):
        try:
            target_channel = bot.get_channel(int(self.channel_id.value)); list_opts = [o.strip() for o in self.options.value.split('\n') if o.strip()][:5]
            if not target_channel or not list_opts: raise Exception()
            view = VoteView(self.vote_title.value, list_opts); await target_channel.send(embed=view.create_embed(), view=view)
            await interaction.response.send_message(f"✅ ส่งระบบโหวต **{self.vote_title.value}** แล้ว!", ephemeral=True)
        except: await interaction.response.send_message("❌ Error: ID ห้องผิดพลาด หรือข้อมูลไม่ครบ!", ephemeral=True)

class AnnounceModal(ui.Modal, title='📢 สร้างประกาศใหม่'):
    channel_id = ui.TextInput(label='Channel ID', placeholder='ไอดีห้อง...', min_length=15)
    ann_title = ui.TextInput(label='หัวข้อประกาศ', placeholder='พิมพ์หัวข้อ...')
    ann_desc = ui.TextInput(label='รายละเอียด', style=discord.TextStyle.paragraph)
    async def on_submit(self, interaction: discord.Interaction):
        try:
            target_channel = bot.get_channel(int(self.channel_id.value))
            embed = discord.Embed(title=f"📢 {self.ann_title.value}", description=self.ann_desc.value, color=0xffd700); embed.set_image(url=BANNER_URL); embed.set_footer(text=f"ประกาศโดย: {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
            await target_channel.send(embed=embed); await interaction.response.send_message("✅ ส่งประกาศแล้ว!", ephemeral=True)
        except: await interaction.response.send_message("❌ Error!", ephemeral=True)

class AnnounceView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label='📢 สร้างประกาศ', style=discord.ButtonStyle.primary, custom_id='btn_ann')
    async def ann_btn(self, interaction: discord.Interaction, button: ui.Button): await interaction.response.send_modal(AnnounceModal())
    @ui.button(label='🎡 สุ่มวงล้อ', style=discord.ButtonStyle.success, custom_id='btn_wheel_spin')
    async def wheel_btn(self, interaction: discord.Interaction, button: ui.Button): await interaction.response.send_modal(WheelSetupModal())
    @ui.button(label='📊 สร้างโหวต', style=discord.ButtonStyle.secondary, custom_id='btn_vote_setup')
    async def vote_btn(self, interaction: discord.Interaction, button: ui.Button): await interaction.response.send_modal(VoteSetupModal())
    @ui.button(label='🧪 เทสประกาศค้างจ่าย', style=discord.ButtonStyle.danger, custom_id='btn_test_debt_ann')
    async def test_debt_btn(self, interaction: discord.Interaction, button: ui.Button): await send_test_debt_announcement(interaction)

class CloseTicketView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label='🔒 ปิด Ticket', style=discord.ButtonStyle.danger, custom_id='close_ticket_btn')
    async def close_btn(self, interaction: discord.Interaction, button: ui.Button): await interaction.channel.delete()

class TicketView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label='📩 เปิด Ticket สมัครเข้าแก๊งค์', style=discord.ButtonStyle.success, custom_id='open_ticket_btn')
    async def open_ticket(self, interaction: discord.Interaction, button: ui.Button):
        guild = interaction.guild; cat_id = db.get("ticket_category_id")
        category = discord.utils.get(guild.categories, id=cat_id) if cat_id else None
        overwrites = {guild.default_role: discord.PermissionOverwrite(read_messages=False), interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True), guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)}
        ticket_ch = await guild.create_text_channel(name=f"ticket-{interaction.user.name}", category=category, overwrites=overwrites)
        form_text = """**กรุณากรอกข้อมูลสมัคร:**
• ชื่อ IC/OC :
• อายุ IC/OC :
• เพศ :
• Username Roblox :
• มีอาวุธอะไรบ้าง :
• เหตุผลที่อยากเข้าแก๊ง :
• มีไฟในการเล่นมั้ย :
• เคยอยู่แก๊งค์มาก่อนมั้ย :
• รับแรงกดดันได้มั้ย :
• มีหัวผู้เล่นใหม่มั้ย :
• เคยอยู่หน่วยงานมาก่อนมั้ย :
• เล่นใน MB หรือ PC :"""
        await ticket_ch.send(embed=discord.Embed(title="🎫 24 Ticket Support", description=f"สวัสดีคุณ {interaction.user.mention}\n{form_text}", color=0x2ecc71).set_image(url=BANNER_URL), view=CloseTicketView())
        await interaction.response.send_message(f"✅ เปิดแล้วที่ {ticket_ch.mention}", ephemeral=True)

# --- 7. Task Loop ประกาศกิจกรรมอัตโนมัติ ---

@tasks.loop(seconds=60)
async def auto_announce():
    now = datetime.now(); now_h_m = now.strftime("%H:%M")
    if not (ch_id := db.get("auto_ann_ch_id")) or not (channel := bot.get_channel(ch_id)): return
    target_role = discord.utils.get(channel.guild.roles, name="Member")
    tag = target_role.mention if target_role else "@everyone"
    reset_times = [0, 6, 12, 18]; check_hour = (now.hour + 1) % 24
    if check_hour in reset_times and now.minute == 55:
        await channel.send(content=tag, embed=discord.Embed(title="⚠️ เซิฟเวอร์กำลังจะรีเซ็ต!", description="เซิฟเวอร์จะรีเซ็ตในอีก **5 นาที** กรุณาเตรียมตัวให้พร้อม!", color=0xffcc00).set_image(url=BANNER_URL))
    if now.hour in reset_times and now.minute == 0:
        await channel.send(content=tag, embed=discord.Embed(title="✅ เซิฟเวอร์รีเซ็ตเรียบร้อย!", description="ระบบรีเซิฟเวอร์แล้ว เข้าเกมได้เลย!", color=0x2ecc71).set_image(url=BANNER_URL))
    activities = {"01:00": "ชิงธง 🚩", "01:30": "แย่งชิงกล่องงานดำ 📦", "02:00": "ปากัวหรรษา 🚶", "03:00": "แย่งชิงทรัพยากร 📦", "04:00": "ปากัวหรรษาสุดโหด 🚶🔥", "07:00": "ปากัวหรรษาสุดโหด 🚶🔥", "09:00": "ชิงธง 🚩", "09:30": "แย่งชิงกล่องงานดำ 📦", "10:00": "ปากัวหรรษา 🚶", "11:00": "แย่งชิงทรัพยากร 📦", "11:30": "แย่งชิงกล่องงานดำ 📦", "12:30": "แย่งชิงกล่องงานดำ 📦", "13:00": "AirDrop ประชาชน 📦", "13:30": "แย่งชิงกล่องงานดำ 📦", "14:00": "AirDrop หน่วยงาน 👮‍♂️", "14:30": "แย่งชิงกล่องงานดำ 📦", "15:00": "AirDrop แก๊งค์ 🔫", "15:30": "แย่งชิงกล่องงานดำ 📦", "16:00": "ชิงธง 🚩", "16:30": "ปากัวหรรษาสุดโหด 🚶🔥", "17:00": "ปากัวหรรษา 🚶", "17:30": "แย่งชิงทรัพยากร 📦", "19:00": "AirDrop ประชาชน 📦", "19:30": "ชิงธง 🚩", "20:00": "AirDrop หน่วยงาน 👮‍♂️", "20:30": "ปากัวหรรษา 🚶", "21:00": "AirDrop แก๊งค์ 🔫", "21:30": "ปากัวหรรษาสุดโหด 🚶🔥", "22:00": "แย่งชิงทรัพยากร 📦", "23:30": "แย่งชิงกล่องงานดำ 📦", "00:30": "แย่งชิงกล่องงานดำ 📦"}
    for t_time, name in activities.items():
        t_dt = datetime.strptime(t_time, "%H:%M").replace(year=now.year, month=now.month, day=now.day)
        if t_dt < now and now_h_m != t_time: t_dt += timedelta(days=1)
        diff = int((t_dt - now).total_seconds() / 60)
        if diff == 10: await channel.send(content=tag, embed=discord.Embed(title="⏳ เตรียมตัว! กิจกรรมในอีก 10 นาที", description=f"**{name}** เริ่มเวลา {t_time}", color=0x3498db).set_image(url=BANNER_URL))
        elif 1 <= diff <= 3: await channel.send(content=tag, embed=discord.Embed(title="🚨 ใกล้เริ่มแล้ว!", description=f"**{name}** ในอีก {diff} นาทีเท่านั้น!", color=0xe67e22).set_image(url=BANNER_URL))
    if now_h_m in activities: await channel.send(content=tag, embed=discord.Embed(title="⏰ เริ่มแล้ว!", description=f"**{activities[now_h_m]}** มาเลยๆ!", color=0xff4500).set_image(url=BANNER_URL))

# --- 8. Admin Commands ---

@bot.command()
@commands.has_permissions(administrator=True)
async def setup_leave_btn(ctx):
    try: await ctx.message.delete()
    except: pass
    await ctx.send(embed=discord.Embed(title="💤 ระบบแจ้งลาแอร์ดรอป", description="กดปุ่มเพื่อแจ้งลาแอร์ดรอป", color=0x95a5a6), view=ActivitySignupView('leave'))

@bot.command()
@commands.has_permissions(administrator=True)
async def setup_leave_list(ctx):
    try: await ctx.message.delete()
    except: pass
    db["leave_ch_id"] = ctx.channel.id; db["leave_list_id"] = None; save_db(db); await refresh_specific_list('leave')
    await ctx.send("⚙️ *ปุ่มล้างรายชื่อลา:*", view=AdminClearView('leave'))

@bot.command()
@commands.has_permissions(administrator=True)
async def setup_all(ctx):
    try: await ctx.message.delete()
    except: pass
    await ctx.send(embed=discord.Embed(title="🛠 แผงควบคุมระบบ", description="สร้างประกาศ / สุ่มวงล้อ / สร้างโหวต / เทสประกาศค้างจ่าย", color=0x2b2d31), view=AnnounceView())

@bot.command()
@commands.has_permissions(administrator=True)
async def delpay(ctx, name: str):
    try: await ctx.message.delete()
    except: pass
    if name in db["members_money"]: del db["members_money"][name]; save_db(db); await refresh_money_embed(); await ctx.send(f"🗑️ ลบชื่อ `{name}` ออกจากตารางการเงินแล้ว", delete_after=5)
    else: await ctx.send(f"❌ ไม่พบชื่อ `{name}` ในรายการ", delete_after=5)

@bot.command()
@commands.has_permissions(administrator=True)
async def delreg(ctx, name: str):
    try: await ctx.message.delete()
    except: pass
    if name in db["profiles"]: del db["profiles"][name]; save_db(db); await refresh_profile_embed(); await ctx.send(f"🗑️ ลบรายชื่อ `{name}` ออกจากระบบสมาชิกแล้ว", delete_after=5)

@bot.command()
@commands.has_permissions(administrator=True)
async def ticket_setup(ctx, cat_id: int = None):
    try: await ctx.message.delete()
    except: pass
    if cat_id: db["ticket_category_id"] = cat_id; save_db(db)
    form_text = """**กรุณากรอกข้อมูลสมัคร:**\n• ชื่อ IC/OC :\n• อายุ IC/OC :\n• เพศ :\n• Username Roblox :\n• มีอาวุธอะไรบ้าง :\n• เหตุผลที่อยากเข้าแก๊ง :\n• มีไฟในการเล่นมั้ย :\n• เคยอยู่แก๊งค์มาก่อนมั้ย :\n• รับแรงกดดันได้มั้ย :\n• มีหัวผู้เล่นใหม่มั้ย :\n• เคยอยู่หน่วยงานมาก่อนมั้ย :\n• เล่นใน MB หรือ PC :"""
    await ctx.send(embed=discord.Embed(title="📝 สมัครเข้าแก๊งค์ 24", description=form_text, color=0x3498db).set_image(url=BANNER_URL), view=TicketView())

@bot.command()
@commands.has_permissions(administrator=True)
async def setup_land_btn(ctx):
    try: await ctx.message.delete()
    except: pass
    await ctx.send(embed=discord.Embed(title="🏰 ระบบลงชื่อเล่นแลนด์", description="กดปุ่มเพื่อลงชื่อ", color=0x3498db), view=ActivitySignupView('land'))

@bot.command()
@commands.has_permissions(administrator=True)
async def setup_land_list(ctx):
    try: await ctx.message.delete()
    except: pass
    db["land_ch_id"] = ctx.channel.id; db["land_list_id"] = None; save_db(db); await refresh_specific_list('land')
    await ctx.send("⚙️ *ปุ่มล้างรายชื่อ:*", view=AdminClearView('land'))

@bot.command()
@commands.has_permissions(administrator=True)
async def setup_airdrop_btn(ctx):
    try: await ctx.message.delete()
    except: pass
    await ctx.send(embed=discord.Embed(title="📦 ระบบลงชื่อเล่นแอร์ดรอป", description="กดปุ่มเพื่อลงชื่อ", color=0x2ecc71), view=ActivitySignupView('airdrop'))

@bot.command()
@commands.has_permissions(administrator=True)
async def setup_airdrop_list(ctx):
    try: await ctx.message.delete()
    except: pass
    db["airdrop_ch_id"] = ctx.channel.id; db["airdrop_list_id"] = None; save_db(db); await refresh_specific_list('airdrop')
    await ctx.send("⚙️ *ปุ่มล้างรายชื่อ:*", view=AdminClearView('airdrop'))

@bot.command()
@commands.has_permissions(administrator=True)
async def setup_story_btn(ctx):
    try: await ctx.message.delete()
    except: pass
    await ctx.send(embed=discord.Embed(title="🎬 ระบบลงชื่อเล่นสตอรี่", description="กดปุ่มเพื่อลงชื่อ", color=0xe74c3c), view=ActivitySignupView('story'))

@bot.command()
@commands.has_permissions(administrator=True)
async def setup_story_list(ctx):
    try: await ctx.message.delete()
    except: pass
    db["story_ch_id"] = ctx.channel.id; db["story_list_id"] = None; save_db(db); await refresh_specific_list('story')
    await ctx.send("⚙️ *ปุ่มล้างรายชื่อ:*", view=AdminClearView('story'))

@bot.command()
async def reg(ctx, name: str, age: str):
    try: await ctx.message.delete()
    except: pass
    db["profiles"][name] = age; save_db(db); await refresh_profile_embed()

@bot.command()
async def pay(ctx, name: str, *, status: str):
    try: await ctx.message.delete()
    except: pass
    db["members_money"][name] = status; save_db(db); await refresh_money_embed()

@bot.command()
@commands.has_permissions(administrator=True)
async def setup(ctx, type: str = "finance"):
    try: await ctx.message.delete()
    except: pass
    if type == "finance":
        db["money_ch_id"] = ctx.channel.id; db["money_msg_id"] = None; save_db(db); await refresh_money_embed()
    elif type == "vault":
        db["vault_ch_id"] = ctx.channel.id; db["vault_msg_id"] = None; save_db(db); await refresh_vault_embed()
    else:
        await ctx.send("❌ ใช้ `!setup finance` หรือ `!setup vault`", delete_after=5)

@bot.command()
@commands.has_permissions(administrator=True)
async def member_setup(ctx):
    try: await ctx.message.delete()
    except: pass
    db["profile_ch_id"] = ctx.channel.id; db["profile_msg_id"] = None; save_db(db); await refresh_profile_embed()

@bot.command()
@commands.has_permissions(administrator=True)
async def set_auto_room(ctx):
    try: await ctx.message.delete()
    except: pass
    db["auto_ann_ch_id"] = ctx.channel.id; save_db(db); await ctx.send("✅ ตั้งห้องแล้ว", delete_after=5)

@bot.command()
@commands.has_permissions(administrator=True)
async def set_log_room(ctx):
    try: await ctx.message.delete()
    except: pass
    db["log_ch_id"] = ctx.channel.id
    save_db(db)
    await ctx.send(f"✅ ตั้งห้อง {ctx.channel.mention} เป็นห้องแจ้งเตือน Log เรียบร้อย!", delete_after=5)

# --- 9. Bot Start ---
@bot.event
async def on_ready():
    print(f'✅ 24 System Online!')
    if not auto_announce.is_running(): auto_announce.start()
    if not midnight_debt_announcer.is_running(): midnight_debt_announcer.start()
    bot.add_view(AnnounceView()); bot.add_view(TicketView()); bot.add_view(CloseTicketView())
    bot.add_view(MoneyTicketView()); bot.add_view(WheelActionView([], "ไม่ระบุ"))
    for m in ['land', 'airdrop', 'story', 'leave']:
        bot.add_view(ActivitySignupView(m)); bot.add_view(AdminClearView(m))

bot.run(os.getenv('TOKEN'))
