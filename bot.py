import os
import asyncio
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ChatPermissions
from pyrogram.errors import UserNotParticipant

# Koyeb Configs (Environment Variables se read karega)
API_ID = int(os.environ.get("API_ID", "123456"))  # Apni API ID dalein
API_HASH = os.environ.get("API_HASH", "YOUR_API_HASH")  # Apni API Hash dalein
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN")  # Bot Father se mila Token
FSUB_CHANNEL = os.environ.get("FSUB_CHANNEL", "YourChannelUsername")  # Bina @ ke Channel Username

bot = Client("group_manager_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# User message count store karne ke liye
user_msg_count = {}

# Force Subscribe Check Function
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

@bot.on_message(filters.group & ~filters.service & ~filters.bot)
async def handle_messages(client, message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    username = message.from_user.username
    
    # Mention format (Username ho toh @username, nahi toh Naam)
    user_mention = f"@{username}" if username else message.from_user.mention

    # 1. Check Force Subscribe
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
            f"⚠️ {user_mention}, group me message karne ke liye aapko pehle humara channel join karna hoga!",
            reply_markup=fsub_button
        )
        await asyncio.sleep(10)
        await msg.delete()
        return

    # Group Share & Add Member Buttons
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🚀 Share Group", url=f"https://t.me/share/url?url=https://t.me/{message.chat.username if message.chat.username else ''}&text=Join%20this%20awesome%20group!"),
            InlineKeyboardButton("➕ Add Member", url=f"https://t.me/{message.chat.username if message.chat.username else ''}?startgroup=true")
        ]
    ])

    # 2. Count User Messages
    if user_id not in user_msg_count:
        user_msg_count[user_id] = 1
    else:
        user_msg_count[user_id] += 1

    # 3. Action on 5th Message
    if user_msg_count[user_id] >= 5:
        # Reset count
        user_msg_count[user_id] = 0

        # Mute User for 3 Hours
        until_time = datetime.now() + timedelta(hours=3)
        try:
            await client.restrict_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=until_time
            )

            # Warning Reply Message
            text = (
                f"🚨 {user_mention}, aapne 5 messages poore kar liye hain!\n\n"
                f"Pehle aap is group pe **3 member add karo** tabhi uske baad aap message kar sakte ho.\n\n"
                f"🚫 Aapko **3 ghante** ke liye mute kar diya gaya hai."
            )

            await message.reply_text(text, reply_markup=buttons)

        except Exception as e:
            print(f"Error while muting user: {e}")

print("Bot Start ho raha hai...")
bot.run()

