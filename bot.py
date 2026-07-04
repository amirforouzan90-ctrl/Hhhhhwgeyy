# ═══════════════════════════════════════════════════════════════════
# 🎵 ربات آهنگ‌یاب تلگرام — نسخه حرفه‌ای ۳.۰
# ═══════════════════════════════════════════════════════════════════
# سازنده: امیر علی فروزان اصل
# نسخه: 3.0.0
# قابلیت‌ها: جستجوی واقعی آهنگ از یوتیوب، دانلود صوتی، ویدیو، ویس
# موتور جستجو: yt-dlp (واقعی و کار کردن)
# ═══════════════════════════════════════════════════════════════════

import os
import sys
import json
import logging
import tempfile
import requests
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, List, Dict

import telebot
from telebot import types
from telebot.handler_backends import State, StatesGroup

# ─── yt-dlp برای دانلود واقعی از یوتیوب ──────────────────────────
import yt_dlp

# ─── پیکربندی لاگ‌گیری حرفه‌ای ───────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler('music_bot.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("MusicBot")
# silence yt-dlp noise
logging.getLogger("yt_dlp").setLevel(logging.WARNING)

# ─── بارگذاری تنظیمات از محیط ───────────────────────────────────
API_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
MAX_RESULTS = 8
DOWNLOAD_TIMEOUT = 120

if API_TOKEN == "YOUR_BOT_TOKEN":
    logger.error("❌ توکن ربات تنظیم نشده! متغیر BOT_TOKEN را تنظیم کنید.")
    sys.exit(1)

# ─── مقداردهی ربات ───────────────────────────────────────────────
bot = telebot.TeleBot(API_TOKEN, parse_mode="HTML")

# ─── مدیریت وضعیت کاربران ───────────────────────────────────────
class SearchStates(StatesGroup):
    waiting_query = State()
    waiting_selection = State()

user_cache: Dict[int, List[dict]] = {}
user_modes: Dict[int, str] = {}
stats = {"searches": 0, "downloads": 0, "users": set()}


@dataclass
class Track:
    title: str
    artist: str
    duration: int = 0
    url: str = ""
    webpage_url: str = ""
    thumbnail: str = ""

    @property
    def formatted(self) -> str:
        mins, secs = divmod(self.duration, 60)
        return f"🎵 <b>{self.title}</b>\n👤 {self.artist} | ⏱ {mins:02d}:{secs:02d}"


# ─── جستجوی واقعی از یوتیوب با yt-dlp ───────────────────────────
def search_youtube(query: str, max_results: int = MAX_RESULTS) -> List[Track]:
    """جستجوی واقعی در یوتیوب و برگرداندن لیست آهنگ‌ها."""
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "default_search": f"ytsearch{max_results}",
        "skip_download": True,
    }
    tracks = []
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
            for entry in result.get("entries", []):
                if not entry:
                    continue
                tracks.append(Track(
                    title=entry.get("title", "نامشخص"),
                    artist=entry.get("uploader", entry.get("channel", "نامشخص")),
                    duration=entry.get("duration", 0) or 0,
                    url=entry.get("url", ""),
                    webpage_url=entry.get("webpage_url", entry.get("url", "")),
                    thumbnail=entry.get("thumbnail", ""),
                ))
    except Exception as e:
        logger.error(f"خطا در جستجوی یوتیوب: {e}")
    return tracks


# ─── دانلود واقعی آهنگ از یوتیوب ─────────────────────────────────
def download_audio(webpage_url: str, as_voice: bool = False) -> Optional[str]:
    """دانلود صوتی واقعی از یوتیوب و بازگشت مسیر فایل."""
    tmp_dir = tempfile.mkdtemp()
    fmt = "bestaudio[ext=m4a]/bestaudio" if not as_voice else "bestaudio[ext=mp3]/bestaudio"
    outtmpl = os.path.join(tmp_dir, "%(title)s.%(ext)s")
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "format": fmt,
        "outtmpl": outtmpl,
        "socket_timeout": 30,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([webpage_url])
        # پیدا کردن فایل دانلود شده
        files = list(Path(tmp_dir).glob("*"))
        if files:
            return str(files[0])
    except Exception as e:
        logger.error(f"خطا در دانلود صوتی: {e}")
    return None


def download_video(webpage_url: str) -> Optional[str]:
    """دانلود ویدیو واقعی از یوتیوب."""
    tmp_dir = tempfile.mkdtemp()
    outtmpl = os.path.join(tmp_dir, "%(title)s.%(ext)s")
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "format": "best[ext=mp4][filesize<50M]/best",
        "outtmpl": outtmpl,
        "socket_timeout": 30,
        "max_filesize": 50 * 1024 * 1024,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([webpage_url])
        files = list(Path(tmp_dir).glob("*"))
        if files:
            return str(files[0])
    except Exception as e:
        logger.error(f"خطا در دانلود ویدیو: {e}")
    return None


# ─── دریافت متن آهنگ از API واقعی ────────────────────────────────
def fetch_lyrics(artist: str, title: str) -> str:
    """دریافت متن آهنگ از lyrics.ovh (API واقعی و رایگان)."""
    try:
        clean_title = title.split("(")[0].split("[")[0].strip()
        clean_artist = artist.split(" - ")[0].strip()
        url = f"https://api.lyrics.ovh/v1/{clean_artist}/{clean_title}"
        response = requests.get(url, timeout=15)
        data = response.json()
        lyrics = data.get("lyrics", "")
        if lyrics:
            return lyrics.strip()
        return "❌ متن این آهنگ پیدا نشد. نام دقیق‌تری بنویسید."
    except Exception as e:
        logger.error(f"خطا در دریافت متن: {e}")
        return "❌ متاسفانه متن آهنگ دریافت نشد."


# ─── کیبورد اصلی ─────────────────────────────────────────────────
def main_keyboard() -> types.ReplyKeyboardMarkup:
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("🎵 جستجوی آهنگ"),
        types.KeyboardButton("📝 متن آهنگ"),
        types.KeyboardButton("🎤 ویس آهنگ"),
        types.KeyboardButton("🎬 ویدیو آهنگ"),
        types.KeyboardButton("📊 آمار ربات"),
        types.KeyboardButton("👤 درباره سازنده"),
    )
    return markup


# ─── هندلر /start ────────────────────────────────────────────────
@bot.message_handler(commands=["start"])
def cmd_start(message):
    user = message.from_user
    stats["users"].add(user.id)
    logger.info(f"کاربر جدید: {user.id} - {user.full_name}")
    welcome = (
        f"🎶 سلام <b>{user.first_name}</b> عزیز!\n\n"
        "به ربات <b>آهنگ‌یاب حرفه‌ای</b> خوش آمدید. 🎧\n\n"
        "🔍 نام آهنگ یا خواننده رو بفرستید تا براتون پیدا کنم.\n"
        "📝 متن آهنگ، 🎤 ویس و 🎬 ویدیو هم در دسترس شماست.\n\n"
        "⚡ <i>سازنده: امیر علی فروزان اصل</i>"
    )
    bot.send_message(message.chat.id, welcome, reply_markup=main_keyboard())


@bot.message_handler(commands=["help"])
def cmd_help(message):
    bot.send_message(
        message.chat.id,
        "📖 <b>راهنمای ربات آهنگ‌یاب</b>\n\n"
        "🎵 <b>جستجوی آهنگ</b> — نام آهنگ بفرستید، دانلود کنید\n"
        "📝 <b>متن آهنگ</b> — متن کامل ترانه\n"
        "🎤 <b>ویس آهنگ</b> — فایل صوتی به صورت ویس\n"
        "🎬 <b>ویدیو آهنگ</b> — موزیک‌ویدیو\n"
        "📊 <b>آمار ربات</b> — آمار استفاده\n\n"
        "⚡ <i>سازنده: امیر علی فروزان اصل</i>"
    )


@bot.message_handler(func=lambda m: m.text == "👤 درباره سازنده")
def cmd_about(message):
    bot.send_message(
        message.chat.id,
        "👤 <b>درباره سازنده</b>\n\n"
        "🧑‍💻 <b>امیر علی فروزان اصل</b>\n"
        "🔧 نسخه: <code>3.0.0</code>\n"
        "🐍 Python 3.11+\n"
        "📚 کتابخانه‌ها: pyTelegramBotAPI, yt-dlp, requests\n\n"
        "📧 ارتباط: @amirforozanasl"
        "⭐ <i>ساخته شده با عشق</i>"
    )


# ─── هندلرهای دکمه‌ها ────────────────────────────────────────────
@bot.message_handler(func=lambda m: m.text == "🎵 جستجوی آهنگ")
def handle_search_track(message):
    user_modes[message.chat.id] = "track"
    bot.send_message(message.chat.id, "🔍 نام آهنگ یا خواننده رو بفرستید:")
    bot.set_state(message.from_user.id, SearchStates.waiting_query, message.chat.id)


@bot.message_handler(func=lambda m: m.text == "🎤 ویس آهنگ")
def handle_search_voice(message):
    user_modes[message.chat.id] = "voice"
    bot.send_message(message.chat.id, "🎤 نام آهنگ رو بفرستید تا ویسش رو بفرستم:")
    bot.set_state(message.from_user.id, SearchStates.waiting_query, message.chat.id)


@bot.message_handler(func=lambda m: m.text == "🎬 ویدیو آهنگ")
def handle_search_video(message):
    user_modes[message.chat.id] = "video"
    bot.send_message(message.chat.id, "🎬 نام آهنگ رو بفرستید تا ویدیوش رو بفرستم:")
    bot.set_state(message.from_user.id, SearchStates.waiting_query, message.chat.id)


@bot.message_handler(func=lambda m: m.text == "📝 متن آهنگ")
def handle_search_lyrics(message):
    user_modes[message.chat.id] = "lyrics"
    bot.send_message(message.chat.id, "📝 نام آهنگ و خواننده رو بفرستید (مثلا: Eminem Lose Yourself):")
    bot.set_state(message.from_user.id, SearchStates.waiting_query, message.chat.id)


# ─── پردازش جستجو (واقعی) ────────────────────────────────────────
@bot.message_handler(state=SearchStates.waiting_query)
def process_search(message):
    query = message.text.strip()
    if not query or len(query) < 2:
        bot.send_message(message.chat.id, "❌ لطفاً نام معتبر بفرستید.")
        return

    chat_id = message.chat.id
    mode = user_modes.get(chat_id, "track")
    bot.delete_state(message.from_user.id, chat_id)

    bot.send_chat_action(chat_id, "typing")
    bot.send_message(chat_id, f"🔎 در حال جستجوی <b>{query}</b>...")

    stats["searches"] += 1
    logger.info(f"جستجو [{mode}]: '{query}' توسط {message.from_user.id}")

    tracks = search_youtube(query)

    if not tracks:
        bot.send_message(chat_id, "❌ نتیجه‌ای پیدا نشد. دوباره تلاش کنید.")
        return

    user_cache[chat_id] = [t.__dict__ for t in tracks]

    # حالت متن آهنگ — مستقیم از API بگیر
    if mode == "lyrics":
        bot.send_chat_action(chat_id, "typing")
        first = tracks[0]
        lyrics = fetch_lyrics(first.artist, first.title)
        bot.send_message(
            chat_id,
            f"📝 <b>{first.title}</b> — {first.artist}\n\n{lyrics[:3500]}"
        )
        return

    # نمایش نتایج برای انتخاب
    text = f"🔎 نتایج جستجو برای: <b>{query}</b>\n\n"
    for i, track in enumerate(tracks[:MAX_RESULTS], 1):
        text += f"{i}. {track.formatted}\n"
    text += "\n📌 شماره آهنگ رو بفرستید تا دانلود کنم."
    bot.send_message(chat_id, text)
    bot.set_state(message.from_user.id, SearchStates.waiting_selection, chat_id)


# ─── دانلود و ارسال (واقعی) ─────────────────────────────────────
@bot.message_handler(state=SearchStates.waiting_selection)
def download_selected(message):
    chat_id = message.chat.id
    bot.delete_state(message.from_user.id, chat_id)

    try:
        idx = int(message.text.strip()) - 1
    except ValueError:
        bot.send_message(chat_id, "❌ لطفاً فقط شماره بفرستید.")
        return

    tracks = user_cache.get(chat_id, [])
    if not (0 <= idx < len(tracks)):
        bot.send_message(chat_id, "❌ شماره نامعتبر!")
        return

    track = tracks[idx]
    mode = user_modes.get(chat_id, "track")
    webpage_url = track.get("webpage_url") or track.get("url")
    title = track.get("title", "آهنگ")
    artist = track.get("artist", "نامشخص")
    caption = f"🎵 <b>{title}</b>\n👤 {artist}\n\n⚡ سازنده: امیر علی فروزان اصل"

    bot.send_message(chat_id, f"⏳ در حال دانلود <b>{title}</b>... لطفاً صبر کنید.")

    try:
        if mode == "voice":
            bot.send_chat_action(chat_id, "record_audio")
            file_path = download_audio(webpage_url, as_voice=True)
            if file_path and os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    bot.send_voice(chat_id, f, caption=caption)
                os.remove(file_path)
            else:
                bot.send_message(chat_id, "❌ دانلود ناموفق بود. دوباره تلاش کنید.")

        elif mode == "video":
            bot.send_chat_action(chat_id, "upload_video")
            file_path = download_video(webpage_url)
            if file_path and os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    bot.send_video(chat_id, f, caption=caption)
                os.remove(file_path)
            else:
                bot.send_message(chat_id, "❌ دانلود ویدیو ناموفق بود (احتمالاً حجم زیاد).")

        else:  # track — فایل صوتی کامل
            bot.send_chat_action(chat_id, "upload_audio")
            file_path = download_audio(webpage_url)
            if file_path and os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    bot.send_audio(
                        chat_id, f,
                        title=title, performer=artist, caption=caption
                    )
                os.remove(file_path)
            else:
                bot.send_message(chat_id, "❌ دانلود ناموفق بود. دوباره تلاش کنید.")

        stats["downloads"] += 1
        logger.info(f"ارسال موفق [{mode}]: {title}")

    except Exception as e:
        logger.error(f"خطا در ارسال: {e}")
        bot.send_message(chat_id, f"⚠️ خطا در ارسال: {str(e)[:100]}")


# ─── آمار ربات ──────────────────────────────────────────────────
@bot.message_handler(func=lambda m: m.text == "📊 آمار ربات")
def cmd_stats(message):
    bot.send_message(
        message.chat.id,
        "📊 <b>آمار ربات آهنگ‌یاب</b>\n\n"
        f"👥 کاربران منحصر به فرد: <b>{len(stats['users'])}</b>\n"
        f"🔍 تعداد جستجوها: <b>{stats['searches']}</b>\n"
        f"📥 تعداد دانلودها: <b>{stats['downloads']}</b>\n"
        f"🕐 زمان سرور: <code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</code>\n\n"
        f"⚡ <i>سازنده: امیر علی فروزان اصل</i>"
    )


# ─── جستجوی سریع (هر متنی = جستجوی آهنگ) ────────────────────────
@bot.message_handler(func=lambda m: True, content_types=["text"])
def quick_search(message):
    user_modes[message.chat.id] = "track"
    bot.set_state(message.from_user.id, SearchStates.waiting_query, message.chat.id)
    process_search(message)


# ─── اجرای ربات ─────────────────────────────────────────────────
def main():
    logger.info("🎵 ربات آهنگ‌یاب نسخه 3.0.0 آماده کار است")
    logger.info("⚡ سازنده: امیر علی فروزان اصل")
    logger.info("📡 موتور: yt-dlp (دانلود واقعی از یوتیوب)")
    try:
        bot.infinity_polling(skip_pending=True, timeout=30, long_polling_timeout=25)
    except KeyboardInterrupt:
        logger.info("توقف ربات توسط کاربر")
    except Exception as e:
        logger.critical(f"خطای بحرانی: {e}")
    finally:
        logger.info("ربات متوقف شد")


if __name__ == "__main__":
    main()
