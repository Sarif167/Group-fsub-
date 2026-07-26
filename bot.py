import os
import asyncio
from datetime import datetime, timedelta
from aiohttp import web
from pyrogram import Client, filters, idle
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ChatPermissions
from pyrogram.errors import UserNotParticipant, FloodWait

# ================= CONFIGURATIONS =================
API_ID = int(os.environ.get("API_ID", "23621595"))
API_HASH = os.environ.get("API_HASH", "de904be2b4cd4efe2ea728ded17ca77d")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8367187334:AAF1i5BYITTT12OPLNtFoeYszMYdUwp1-qc")

# Force Subscribe Channel (Without @)
FSUB_CHANNEL = os.environ.get("FSUB_CHANNEL", "MovieSearchAutoGroup")

# Owner / Admin ID (Integer format me)
OWNER_ID = int(os.environ.get("OWNER_ID", "5506357900"))

# Main Channel & Developer Usernames (Without @)
MAIN_CHANNEL = os.environ.get("MAIN_CHANNEL", "MovieSearchAutoGroup")
DEVELOPER_USER = os.environ.get("DEVELOPER_USER", "botmaster55").replace("@", "")

# Payment Notification Channel (With or Without @)
LOG_CHANNEL = os.environ.get("LOG_CHANNEL", "-1001860172104")

# Start Image URL
START_IMAGE = os.environ.get("START_IMAGE", "https://iili.io/CO0XKVn.jpg")

# Port for Koyeb Health Check
PORT = int(os.environ.get("PORT", "8000"))
# ===================================================

# Memory Session use kar rahe hain taaki Koyeb par session lock ki problem na aaye
bot = Client(
    "group_manager_bot", 
    api_id=API_ID, 
    api_hash=API_HASH, 
    bot_token=BOT_TOKEN,
    in_memory=True
)

# Databases (In-Memory)
user_msg_count = {}
premium_groups = {} # {chat_id: expiry_datetime}

# Helper: Check Premium Status
def is_group_premium(chat_id):
    if chat_id in premium_groups:
        if datetime.now() < premium_groups[chat_id]:
            return True
        else:
            del premium_groups[chat_id]
    return False

# Force Subscribe Check
async def check_fsub(client, user_id):
    if not FSUB_CHANNEL:
        return True
    try:
        member = await client.get_chat_member(FSUB_CHANNEL, user_id)
        if member.status in ["kicked", "left"]:
            return False
        return True
    except UserNotParticipant:
        return False
    except Exception:
        return True

# ================= KOYEB WEB SERVER =================
routes = web.RouteTableDef()

@routes.get("/", allow_head=True)
async def root_route_handler(request):
    return web.json_response({"status": "running", "bot": "online"})

async def web_server():
    web_app = web.Application()
    web_app.add_routes(routes)
    return web_app

# ================= START COMMAND =================
@bot.on_message(filters.command(["start", "start@group_manager_bot"]))
async def start_command(client, message):
    if message.chat.type != "private":
        return

    try:
        bot_obj = await client.get_me()
        bot_username = bot_obj.username
    except Exception:
        bot_username = "bot"

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➕ Add Me To Your Group / Channel", url=f"https://t.me/{bot_username}?startgroup=true")
        ],
        [
            InlineKeyboardButton("📢 Main Channel", url=f"https://t.me/{MAIN_CHANNEL}"),
            InlineKeyboardButton("👨‍💻 Developer", url=f"https://t.me/{DEVELOPER_USER}")
        ],
        [
            InlineKeyboardButton("📖 Help & Plans", callback_data="help_cmd")
        ]
    ])
    
    caption_text = (
        f"👋 **Hello {message.from_user.mention if message.from_user else 'User'}!**\n\n"
        f"Welcome to Group Manager Bot! 🚀\n\n"
        f"Main aapke group me spam control kar sakta hoon aur automatic members add karwa sakta hoon.\n\n"
        f"💳 **Note:** Is bot ko group me use karne ke liye aapko **Premium Plan** lena hoga."
    )
    
    try:
        await message.reply_photo(
            photo=START_IMAGE,
            caption=caption_text,
            reply_markup=buttons
        )
    except Exception as e:
        print(f"Error sending photo, falling back to text: {e}")
        await message.reply_text(
            text=caption_text,
            reply_markup=buttons
        )

# Callback Queries for Help
@bot.on_callback_query(filters.regex("help_cmd"))
async def help_callback(client, callback_query):
    help_text = (
        "🛠 **Bot Help & Premium Plans**\n\n"
        "**Group Admin Instructions:**\n"
        "1. Bot ko apne group me admin banayein.\n"
        "2. Bot ko activate karne ke liye Group ID lekar Admin/Developer ko bhejein.\n\n"
        "💳 **Premium Plans Available:**\n"
        "• **7 Days Plan:** Limited Trial\n"
        "• **1 Month Plan:** Standard\n"
        "• **2 Months Plan:** Super Value\n"
        "• **3 Months Plan:** Best Saver\n\n"
        f"👨‍💻 Buy Premium contact Developer: @{DEVELOPER_USER}"
    )
    await callback_query.answer()
    await callback_query.message.edit_text(help_text)

# ================= ADMIN PANEL COMMANDS =================

@bot.on_message(filters.command("addgroup") & filters.user(OWNER_ID))
async def add_premium_group(client, message):
    try:
        args = message.text.split()
        if len(args) < 3:
            await message.reply_text("❌ **Usage:** `/addgroup <group_id> <7d|1m|2m|3m>`")
            return
        
        chat_id = int(args[1])
        plan = args[2].lower()
        
        days_map = {"7d": 7, "1m": 30, "2m": 60, "3m": 90}
        
        if plan not in days_map:
            await message.reply_text("❌ Valid plans: `7d`, `1m`, `2m`, `3m`")
            return
        
        days = days_map[plan]
        expiry_date = datetime.now() + timedelta(days=days)
        premium_groups[chat_id] = expiry_date
        
        await message.reply_text(f"✅ Group `{chat_id}` added to Premium for **{days} Days**!\nExpiry: {expiry_date.strftime('%Y-%m-%d %H:%M')}")
        
        if LOG_CHANNEL:
            try:
                log_target = int(LOG_CHANNEL) if LOG_CHANNEL.startswith("-100") or LOG_CHANNEL.lstrip("-").isdigit() else LOG_CHANNEL
                log_text = (
                    f"🎉 **NEW PREMIUM PURCHASED!**\n\n"
                    f"👤 **Approved By:** {message.from_user.mention}\n"
                    f"🆔 **Group ID:** `{chat_id}`\n"
                    f"⏳ **Plan Duration:** {plan.upper()} ({days} Days)\n"
                    f"📅 **Expires On:** {expiry_date.strftime('%Y-%m-%d %H:%M')}"
                )
                await client.send_message(chat_id=log_target, text=log_text)
            except Exception as e:
                print(f"Log Channel Error: {e}")

    except Exception as e:
        await message.reply_text(f"Error: {e}")

@bot.on_message(filters.command("remgroup") & filters.user(OWNER_ID))
async def remove_premium_group(client, message):
    try:
        args = message.text.split()
        if len(args) < 2:
            await message.reply_text("❌ **Usage:** `/remgroup <group_id>`")
            return
        
        chat_id = int(args[1])
        if chat_id in premium_groups:
            del premium_groups[chat_id]
            await message.reply_text(f"🚫 Group `{chat_id}` removed from Premium.")
        else:
            await message.reply_text("❌ Group Premium me nahi hai.")
    except Exception as e:
        await message.reply_text(f"Error: {e}")

# ================= GROUP MESSAGE HANDLER =================

@bot.on_message(filters.group & ~filters.service & ~filters.bot)
async def handle_group_messages(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    username = message.from_user.username
    user_mention = f"@{username}" if username else message.from_user.mention

    if not is_group_premium(chat_id):
        return

    is_subscribed = await check_fsub(client, user_id)
    if not is_subscribed:
        try:
            await message.delete()
        except Exception:
            pass
        
        fsub_button = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{FSUB_CHANNEL}")]
        ])
        msg = await message.reply_text(
            f"⚠️ {user_mention}, group me message karne ke liye pehle humara channel join karein!",
            reply_markup=fsub_button
        )
        await asyncio.sleep(10)
        await msg.delete()
        return

    group_username = message.chat.username if message.chat.username else ""
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🚀 Share Group", url=f"https://t.me/share/url?url=https://t.me/{group_username}&text=Join%20this%20awesome%20group!"),
            InlineKeyboardButton("➕ Add Member", url=f"https://t.me/{group_username}?startgroup=true")
        ]
    ])

    if user_id not in user_msg_count:
        user_msg_count[user_id] = 1
    else:
        user_msg_count[user_id] += 1

    if user_msg_count[user_id] >= 5:
        user_msg_count[user_id] = 0

        until_time = datetime.now() + timedelta(hours=3)
        try:
            await client.restrict_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=until_time
            )

            text = (
                f"🚨 {user_mention}, aapne 5 messages poore kar liye hain!\n\n"
                f"Pehle aap is group pe **3 member add karo** tabhi uske baad aap message kar sakte ho.\n\n"
                f"🚫 Aapko **3 ghante** ke liye mute kar diya gaya hai."
            )

            await message.reply_text(text, reply_markup=buttons)

        except Exception as e:
            print(f"Error Muting User: {e}")

# ================= MAIN RUNNER =================
async def start_app():
    # 1. Web Server Start
    app = web.AppRunner(await web_server())
    await app.setup()
    site = web.TCPSite(app, "0.0.0.0", PORT)
    await site.start()
    print(f"✅ Web Server running on Port: {PORT}")

    # 2. Pyrogram Client Start
    try:
        await bot.start()
        print("🤖 Pyrogram Bot Started Successfully!")
    except FloodWait as e:
        print(f"⚠️ Telegram FloodWait: Waiting for {e.value} seconds...")
        await asyncio.sleep(e.value)
        await bot.start()
        print("🤖 Pyrogram Bot Started After Wait!")

    # 3. Idle Keep-Alive
    await idle()
    await bot.stop()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_app())
    
