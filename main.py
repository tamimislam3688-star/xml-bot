
import logging
import uuid

from pyrogram import Client, filters
from pyrogram.enums import ChatMemberStatus
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message

# ==========================================
# CONFIGURATION — ORIGINAL INFORMATION
# ==========================================

API_ID = 32494859
API_HASH = "2395e3ac90481ffdb91c39d3d6dbb9d"
BOT_TOKEN = "8951755165:AAEn_m2EDfOm-yn7Iwy4ybjIZGXU9B9GGV9E"

BOT_USERNAME = "xmlzonebot"

OWNER_ID = 5470083113
ADMIN_USERNAMES = ["tamim1090"]

CHANNEL_ID = -1004499337783
CHANNEL_USERNAME = "@tamim1x"

# ==========================================
# LOGGING
# ==========================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# ==========================================
# BOT CLIENT
# ==========================================

app = Client(
    "alight_motion_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

admins = {OWNER_ID}
admin_steps = {}
post_data = {}

# RAM storage: data resets if bot restarts
xml_storage = {}
lyrics_storage = {}


# ==========================================
# ADMIN CHECK
# ==========================================

def is_admin(user):
    if not user:
        return False

    if user.id in admins:
        return True

    return bool(
        user.username
        and user.username.lower() in [
            name.lstrip("@").lower()
            for name in ADMIN_USERNAMES
        ]
    )


# ==========================================
# RESOLVE CHANNEL
# ==========================================

async def resolve_channel(client):
    """
    Resolve the public channel username first.
    Confirm that it matches the configured channel ID.
    """
    chat = await client.get_chat(CHANNEL_USERNAME)

    if chat.id != CHANNEL_ID:
        raise RuntimeError(
            f"Channel ID mismatch: configured={CHANNEL_ID}, "
            f"resolved={chat.id}"
        )

    return chat


# ==========================================
# START COMMAND
# ==========================================

@app.on_message(filters.command("start") & filters.private)
async def start(client, message: Message):
    user = message.from_user
    args = (message.text or "").split(maxsplit=1)

    if len(args) > 1:
        param = args[1]

        if param.startswith("get_xml_"):
            data_type = "get_xml"
            unique_key = param[len("get_xml_"):]

        elif param.startswith("get_lyrics_"):
            data_type = "get_lyrics"
            unique_key = param[len("get_lyrics_"):]

        else:
            data_type = None
            unique_key = None

        if data_type and unique_key:
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "📢 🚀 Join Channel 🔗",
                        url="https://t.me/tamim1x"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "📌 🔄 Verify Now ⚡",
                        callback_data=f"verify:{data_type}:{unique_key}"
                    )
                ]
            ])

            await message.reply_text(
                "🔒 **ফাইলটি আনলক করতে প্রথমে নিচের চ্যানেলে "
                "জয়েন করুন এবং Verify বাটনে চাপ দিন।**",
                reply_markup=keyboard
            )
            return

    if is_admin(user):
        admin_steps[user.id] = "waiting_for_video"

        await message.reply_text(
            "👋 স্বাগতম এডমিন তামিম!\n\n"
            "পোস্ট তৈরি করতে প্রথমে আপনার ভিডিওটি পাঠান।"
        )
    else:
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "📢 🚀 Join Channel 🔗",
                    url="https://t.me/tamim1x"
                )
            ]
        ])

        await message.reply_text(
            "✨ Welcome to XML ZONE! ✨\n\n"
            "আমাদের চ্যানেল থেকে XML ফাইল সংগ্রহ করতে "
            "নিচের চ্যানেলে জয়েন করুন।",
            reply_markup=keyboard
        )


# ==========================================
# ADD ADMIN COMMAND
# ==========================================

@app.on_message(filters.command("addadmin") & filters.private)
async def add_admin(client, message: Message):
    if not is_admin(message.from_user):
        return

    if len(message.command) < 2:
        await message.reply_text(
            "ব্যবহার:\n/addadmin tamim1090\n/addadmin 5470083113"
        )
        return

    new_admin = message.command[1].lstrip("@")

    if new_admin.isdigit():
        admins.add(int(new_admin))
    elif new_admin.lower() not in [
        name.lstrip("@").lower()
        for name in ADMIN_USERNAMES
    ]:
        ADMIN_USERNAMES.append(new_admin)

    await message.reply_text(
        f"✅ সফলভাবে নতুন অ্যাডমিন যুক্ত হয়েছে: {new_admin}"
    )


# ==========================================
# BOT / CHANNEL DIAGNOSTICS
# ==========================================

@app.on_message(filters.command("checkbot") & filters.private)
async def check_bot(client, message: Message):
    if not is_admin(message.from_user):
        return

    try:
        me = await client.get_me()
        chat = await resolve_channel(client)
        member = await client.get_chat_member(chat.id, me.id)

        can_post = None

        if member.status == ChatMemberStatus.OWNER:
            can_post = True

        elif member.status == ChatMemberStatus.ADMINISTRATOR:
            privileges = member.privileges
            can_post = (
                privileges.can_post_messages
                if privileges else False
            )

        await message.reply_text(
            "✅ **Channel Diagnostic Report**\n\n"
            f"Bot: @{me.username}\n"
            f"Channel: {chat.title}\n"
            f"Channel ID: `{chat.id}`\n"
            f"Bot status: `{member.status}`\n"
            f"Can post messages: `{can_post}`"
        )

    except Exception as e:
        logging.exception("Channel diagnostic failed")

        await message.reply_text(
            "❌ **Diagnostic Failed**\n\n"
            f"Error: `{type(e).__name__}`\n"
            f"Details: `{str(e)[:800]}`"
        )


# ==========================================
# VIDEO, XML AND LYRICS HANDLER
# ==========================================

@app.on_message(
    filters.private & (filters.video | filters.document | filters.text)
)
async def handle_admin_steps(client, message: Message):
    user = message.from_user

    if not is_admin(user):
        return

    step = admin_steps.get(user.id)

    # Step 1: Receive video
    if step == "waiting_for_video":
        if not message.video:
            await message.reply_text(
                "⚠️ দয়া করে একটি ভিডিও পাঠান।"
            )
            return

        post_data[user.id] = {
            "video": message.video.file_id
        }

        admin_steps[user.id] = "waiting_for_xml"

        await message.reply_text(
            "✅ ভিডিও পাওয়া গেছে!\n"
            "এখন XML ফাইলটি Document হিসেবে পাঠান।"
        )
        return

    # Step 2: Receive XML document
    if step == "waiting_for_xml":
        if not message.document:
            await message.reply_text(
                "⚠️ XML ফাইলটি Document হিসেবে পাঠান।"
            )
            return

        filename = message.document.file_name or ""

        if not filename.lower().endswith(".xml"):
            await message.reply_text(
                "⚠️ দয়া করে .xml এক্সটেনশনের ফাইল পাঠান।"
            )
            return

        post_data[user.id]["xml"] = message.document.file_id
        admin_steps[user.id] = "waiting_for_lyrics"

        await message.reply_text(
            "✅ XML ফাইল পাওয়া গেছে!\n"
            "এখন Lyrics Song Line বা টেক্সট পাঠান।"
        )
        return

    # Step 3: Receive lyrics and publish
    if step == "waiting_for_lyrics":
        if not message.text:
            await message.reply_text(
                "⚠️ দয়া করে Lyrics-এর টেক্সট পাঠান।"
            )
            return

        data = post_data.get(user.id)

        if not data or "video" not in data or "xml" not in data:
            admin_steps.pop(user.id, None)
            post_data.pop(user.id, None)

            await message.reply_text(
                "⚠️ পোস্টের তথ্য অসম্পূর্ণ। /start দিয়ে আবার শুরু করুন।"
            )
            return

        data["lyrics"] = message.text
        unique_key = uuid.uuid4().hex

        xml_storage[unique_key] = data["xml"]
        lyrics_storage[unique_key] = data["lyrics"]

        bot_xml_url = (
            f"https://t.me/{BOT_USERNAME}?start=get_xml_{unique_key}"
        )
        bot_lyrics_url = (
            f"https://t.me/{BOT_USERNAME}?start=get_lyrics_{unique_key}"
        )

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "✨ 📂 Xml File 📥",
                    url=bot_xml_url
                )
            ],
            [
                InlineKeyboardButton(
                    "🥺 🎵 Lyrics Song Line 🎶",
                    url=bot_lyrics_url
                )
            ]
        ])

        caption = (
            "New Xml Video.. ✨💖\n\n"
            "- XML File Unlock 👧✨\n"
            "- Click The Button Below 🔗💎🐼"
        )

        try:
            # Resolve username and validate configured ID
            chat = await resolve_channel(client)

            # Check bot membership and posting permission
            me = await client.get_me()
            member = await client.get_chat_member(chat.id, me.id)

            if member.status not in (
                ChatMemberStatus.OWNER,
                ChatMemberStatus.ADMINISTRATOR
            ):
                raise RuntimeError(
                    f"Bot is not channel admin: {member.status}"
                )

            if member.status == ChatMemberStatus.ADMINISTRATOR:
                privileges = member.privileges

                if not privileges or not privileges.can_post_messages:
                    raise RuntimeError(
                        "Bot lacks can_post_messages permission"
                    )

            await client.send_video(
                chat_id=chat.id,
                video=data["video"],
                caption=caption,
                reply_markup=keyboard
            )

            await message.reply_text(
                "🎉 পোস্টটি সফলভাবে চ্যানেলে অটো-পোস্ট হয়েছে!"
            )

        except Exception as e:
            logging.exception("Channel posting failed")

            xml_storage.pop(unique_key, None)
            lyrics_storage.pop(unique_key, None)

            await message.reply_text(
                "❌ চ্যানেলে পোস্ট করা যায়নি!\n\n"
                f"Error: `{type(e).__name__}`\n"
                f"Details: `{str(e)[:900]}`\n\n"
                "আরও তথ্যের জন্য /checkbot পাঠান।"
            )

        finally:
            admin_steps.pop(user.id, None)
            post_data.pop(user.id, None)


# ==========================================
# JOIN MEMBERSHIP VERIFICATION
# ==========================================

@app.on_callback_query(filters.regex(r"^verify:"))
async def verify_membership(client, callback_query):
    user_id = callback_query.from_user.id

    try:
        _, data_type, unique_key = callback_query.data.split(":", 2)

        # Resolve channel from its username first
        chat = await resolve_channel(client)

        member = await client.get_chat_member(
            chat.id,
            user_id
        )

        is_member = member.status in (
            ChatMemberStatus.OWNER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.MEMBER
        )

    except Exception as e:
        logging.exception("Membership verification failed")

        await callback_query.answer(
            f"⚠️ Verify error: {type(e).__name__}: {str(e)[:150]}",
            show_alert=True
        )
        return

    if not is_member:
        await callback_query.answer(
            "❌ আপনি এখনো @tamim1x চ্যানেলে Join করেননি!",
            show_alert=True
        )
        return

    if data_type == "get_xml":
        file_id = xml_storage.get(unique_key)

        if not file_id:
            await callback_query.answer(
                "⚠️ XML ফাইল পাওয়া যায়নি। বট রিস্টার্ট হলে ডেটা হারিয়ে যেতে পারে।",
                show_alert=True
            )
            return

        try:
            await client.send_document(
                chat_id=user_id,
                document=file_id,
                caption="এই নিন আপনার কাঙ্ক্ষিত XML ফাইল! 🌸"
            )

            await callback_query.answer(
                "✅ ভেরিফিকেশন সফল হয়েছে!"
            )

        except Exception as e:
            logging.exception("XML delivery failed")
            await callback_query.answer(
                f"❌ XML পাঠানো যায়নি: {type(e).__name__}",
                show_alert=True
            )

    elif data_type == "get_lyrics":
        lyrics_text = lyrics_storage.get(unique_key)

        if not lyrics_text:
            await callback_query.answer(
                "⚠️ Lyrics পাওয়া যায়নি।",
                show_alert=True
            )
            return

        try:
            await client.send_message(
                chat_id=user_id,
                text=f"🎵 **Lyrics Song Line:**\n\n{lyrics_text}"
            )

            await callback_query.answer(
                "✅ ভেরিফিকেশন সফল হয়েছে!"
            )

        except Exception as e:
            logging.exception("Lyrics delivery failed")
            await callback_query.answer(
                f"❌ Lyrics পাঠানো যায়নি: {type(e).__name__}",
                show_alert=True
            )

    else:
        await callback_query.answer(
            "❌ Invalid verification request!",
            show_alert=True
        )


# ==========================================
# RUN BOT
# ==========================================

if __name__ == "__main__":
    print("XML ZONE Bot is running...")
    app.run()
