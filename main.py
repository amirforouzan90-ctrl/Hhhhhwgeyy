# ============================================
# 🎵 ربات آهنگ یاب تلگرام
# 👨‍💻 سازنده: امیرعلی فروزان اصل
# 📌 پلتفرم: Replit
# ============================================

import os
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
from io import BytesIO

# ─── تنظیمات لاگ ───
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ─── توکن ربات ───
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

CREATOR = "امیرعلی فروزان اصل"

# ════════════════════════════════════════
#  توابع API
# ════════════════════════════════════════

def search_song(query):
    """جستجوی آهنگ با Deezer API (رایگان)"""
    url = "https://api.deezer.com/search"
    params = {"q": query, "limit": 5}
    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        if "data" in data and data["data"]:
            return data["data"]
    except Exception as e:
        logger.error(f"Search error: {e}")
    return []


def get_lyrics(artist, title):
    """دریافت متن آهنگ"""
    url = f"https://api.lyrics.ovh/v1/{artist}/{title}"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        if "lyrics" in data:
            return data["lyrics"]
    except Exception as e:
        logger.error(f"Lyrics error: {e}")
    return None


def search_by_lyrics(lyrics_text):
    """جستجوی آهنگ با متن"""
    url = "https://api.deezer.com/search"
    params = {"q": lyrics_text[:100], "limit": 5}
    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        if "data" in data and data["data"]:
            return data["data"]
    except Exception as e:
        logger.error(f"Lyrics search error: {e}")
    return []


def get_song_preview(preview_url):
    """دانلود پیش‌نمایش آهنگ"""
    try:
        resp = requests.get(preview_url, timeout=15)
        if resp.status_code == 200:
            return BytesIO(resp.content)
    except Exception as e:
        logger.error(f"Download error: {e}")
    return None


# ════════════════════════════════════════
#  هندلرهای ربات
# ════════════════════════════════════════

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /start"""
    user = update.effective_user
    welcome_text = f"""
🎵 *به ربات آهنگ یاب خوش آمدید!*

سلام *{user.first_name}* عزیز! 👋

من می‌توانم برای شما آهنگ پیدا کنم! 🎶

━━━━━━━━━━━━━━━━━━━━
🔍 *قابلیت‌های من:*

🎤 نام آهنگ یا خواننده بفرستید
📝 متن آهنگ بفرستید تا پیدا کنم
🎧 آهنگ را برایتان ارسال می‌کنم
📋 متن کامل آهنگ را نمایش می‌دهم
━━━━━━━━━━━━━━━━━━━━

💡 *راهنما:*
فقط کافیه اسم آهنگ، خواننده یا حتی
یک تکه از متن آهنگ رو بفرستی! 🎯

👨‍💻 *سازنده:* {CREATOR}
"""

    keyboard = [
        [
            InlineKeyboardButton("🔍 جستجوی آهنگ", callback_data="help_search"),
            InlineKeyboardButton("📝 جستجو با متن", callback_data="help_lyrics"),
        ],
        [
            InlineKeyboardButton("ℹ️ راهنما", callback_data="help"),
            InlineKeyboardButton("👨‍💻 سازنده", callback_data="creator"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        welcome_text,
        parse_mode="Markdown",
        reply_markup=reply_markup,
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /help"""
    help_text = f"""
📖 *راهنمای کامل ربات آهنگ یاب*

━━━━━━━━━━━━━━━━━━━━

1️⃣ *جستجو با نام آهنگ:*
   فقط اسم آهنگ رو بفرست

2️⃣ *جستجو با نام خواننده:*
   اسم خواننده رو بفرست

3️⃣ *جستجو با متن آهنگ:*
   یک تکه از متن آهنگ رو بفرست

4️⃣ *دستورات:*
   /start - شروع ربات
   /help - راهنما
   /creator - اطلاعات سازنده

━━━━━━━━━━━━━━━━━━━━
👨‍💻 *سازنده:* {CREATOR}
"""
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def creator_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /creator"""
    text = f"""
👨‍💻 *اطلاعات سازنده*

━━━━━━━━━━━━━━━━━━━━
👤 *نام:* {CREATOR}
🤖 *ربات:* آهنگ یاب حرفه‌ای
🛠 *پلتفرم:* Replit
📌 *نسخه:* 2.0
━━━━━━━━━━━━━━━━━━━━

⭐️ این ربات با ❤️ ساخته شده است
"""
    await update.message.reply_text(text, parse_mode="Markdown")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پردازش پیام‌های متنی - جستجوی آهنگ"""
    query = update.message.text.strip()
    if not query:
        return

    searching_msg = await update.message.reply_text(
        "🔍 *در حال جستجو...*\n\n⏳ لطفاً صبر کنید...",
        parse_mode="Markdown",
    )

    results = search_song(query)

    if not results:
        results = search_by_lyrics(query)

    if not results:
        await searching_msg.edit_text(
            "❌ *متأسفانه آهنگی پیدا نشد!*\n\n"
            "💡 لطفاً دوباره با کلمات دیگر جستجو کنید.",
            parse_mode="Markdown",
        )
        return

    context.user_data["results"] = results

    text = "🎵 *نتایج جستجو:*\n━━━━━━━━━━━━━━━━━━━━\n\n"

    keyboard = []
    for i, track in enumerate(results):
        title = track.get("title", "نامشخص")
        artist = track.get("artist", {}).get("name", "نامشخص")
        duration = track.get("duration", 0)
        minutes = duration // 60
        seconds = duration % 60

        text += f"*{i+1}.* 🎤 {artist}\n"
        text += f"    🎵 {title}\n"
        text += f"    ⏱ {minutes}:{seconds:02d}\n\n"

        keyboard.append([
            InlineKeyboardButton(
                f"🎧 {title[:25]} - {artist[:15]}",
                callback_data=f"song_{i}",
            ),
        ])

    keyboard.append(
        [InlineKeyboardButton("🔍 جستجوی جدید", callback_data="new_search")]
    )

    text += f"\n👨‍💻 *سازنده:* {CREATOR}"
    reply_markup = InlineKeyboardMarkup(keyboard)

    await searching_msg.edit_text(
        text, parse_mode="Markdown", reply_markup=reply_markup
    )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پردازش دکمه‌های اینلاین"""
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "help":
        help_text = f"""
📖 *راهنمای ربات*

🔍 اسم آهنگ یا خواننده بفرستید
📝 متن آهنگ بفرستید
🎧 آهنگ دانلود و ارسال می‌شود

👨‍💻 *سازنده:* {CREATOR}
"""
        await query.edit_message_text(help_text, parse_mode="Markdown")

    elif data == "creator":
        text = f"""
👨‍💻 *سازنده:* {CREATOR}
⭐️ ربات آهنگ یاب حرفه‌ای
🛠 ساخته شده با ❤️
"""
        await query.edit_message_text(text, parse_mode="Markdown")

    elif data == "help_search":
        text = "🔍 *جستجوی آهنگ*\n\nکافیه اسم آهنگ یا خواننده رو بفرستی!"
        await query.edit_message_text(text, parse_mode="Markdown")

    elif data == "help_lyrics":
        text = "📝 *جستجو با متن*\n\nیک تکه از متن آهنگ رو بفرست تا پیداش کنم!"
        await query.edit_message_text(text, parse_mode="Markdown")

    elif data == "new_search":
        text = "🔍 *اسم آهنگ یا خواننده رو بفرستید:*"
        await query.edit_message_text(text, parse_mode="Markdown")

    elif data.startswith("song_"):
        index = int(data.split("_")[1])
        results = context.user_data.get("results", [])

        if index >= len(results):
            await query.edit_message_text("❌ خطا! لطفاً دوباره جستجو کنید.")
            return

        track = results[index]
        title = track.get("title", "نامشخص")
        artist_name = track.get("artist", {}).get("name", "نامشخص")
        album = track.get("album", {}).get("title", "نامشخص")
        duration = track.get("duration", 0)
        preview_url = track.get("preview", "")
        link = track.get("link", "")
        cover = track.get("album", {}).get("cover_big", "")

        minutes = duration // 60
        seconds = duration % 60

        lyrics = get_lyrics(artist_name, title)

        info_text = f"""
🎵 *{title}*

━━━━━━━━━━━━━━━━━━━━
🎤 *خواننده:* {artist_name}
💿 *آلبوم:* {album}
⏱ *مدت:* {minutes}:{seconds:02d}
━━━━━━━━━━━━━━━━━━━━
"""
        if lyrics:
            if len(lyrics) > 2000:
                lyrics = lyrics[:2000] + "\n\n... (ادامه متن)"
            info_text += f"\n📝 *متن آهنگ:*\n\n{lyrics}\n"

        info_text += f"\n━━━━━━━━━━━━━━━━━━━━\n👨‍💻 *سازنده:* {CREATOR}"

        keyboard = []
        if link:
            keyboard.append([InlineKeyboardButton("🔗 لینک آهنگ", url=link)])
        keyboard.append([
            InlineKeyboardButton("🎧 دانلود پیش‌نمایش", callback_data=f"dl_{index}"),
            InlineKeyboardButton("📝 متن کامل", callback_data=f"lyrics_{index}"),
        ])
        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="new_search")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        if cover:
            try:
                await query.message.reply_photo(
                    photo=cover,
                    caption=info_text,
                    parse_mode="Markdown",
                    reply_markup=reply_markup,
                )
                await query.message.delete()
            except:
                await query.edit_message_text(
                    info_text,
                    parse_mode="Markdown",
                    reply_markup=reply_markup,
                )
        else:
            await query.edit_message_text(
                info_text,
                parse_mode="Markdown",
                reply_markup=reply_markup,
            )

    elif data.startswith("dl_"):
        index = int(data.split("_")[1])
        results = context.user_data.get("results", [])

        if index >= len(results):
            await query.answer("❌ خطا!", show_alert=True)
            return

        track = results[index]
        preview_url = track.get("preview", "")
        title = track.get("title", "نامشخص")
        artist_name = track.get("artist", {}).get("name", "نامشخص")

        if not preview_url:
            await query.answer("❌ پیش‌نمایش موجود نیست!", show_alert=True)
            return

        await query.answer("⏳ در حال دانلود...")

        audio_data = get_song_preview(preview_url)
        if audio_data:
            await query.message.reply_audio(
                audio=audio_data,
                title=title,
                performer=artist_name,
                filename=f"{artist_name} - {title}.mp3",
                caption=f"🎵 {title}\n🎤 {artist_name}\n\n👨‍💻 سازنده: {CREATOR}",
            )
        else:
            await query.answer("❌ خطا در دانلود!", show_alert=True)

    elif data.startswith("lyrics_"):
        index = int(data.split("_")[1])
        results = context.user_data.get("results", [])

        if index >= len(results):
            await query.answer("❌ خطا!", show_alert=True)
            return

        track = results[index]
        title = track.get("title", "نامشخص")
        artist_name = track.get("artist", {}).get("name", "نامشخص")

        lyrics = get_lyrics(artist_name, title)

        if lyrics:
            chunks = [lyrics[i:i+3500] for i in range(0, len(lyrics), 3500)]
            for i, chunk in enumerate(chunks):
                text = f"📝 *متن آهنگ: {title}*\n🎤 *{artist_name}*\n\n"
                if len(chunks) > 1:
                    text += f"(بخش {i+1} از {len(chunks)})\n\n"
                text += chunk
                text += f"\n\n👨‍💻 *سازنده:* {CREATOR}"
                await query.message.reply_text(text, parse_mode="Markdown")
        else:
            await query.answer("❌ متن آهنگ پیدا نشد!", show_alert=True)


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت خطاها"""
    logger.error(f"Error: {context.error}")


# ════════════════════════════════════════
#  اجرای ربات
# ════════════════════════════════════════

def main():
    """اجرای اصلی ربات"""
    print(f"🎵 ربات آهنگ یاب شروع شد!")
    print(f"👨‍💻 سازنده: {CREATOR}")
    print("━" * 40)

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("creator", creator_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_error_handler(error_handler)

    print("✅ ربات فعال شد! در حال دریافت پیام...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
