# ═══════════════════════════════════════════════════════════════════
# 🎵 ربات آهنگ‌یاب تلگرام — نسخه حرفه‌ای
# ═══════════════════════════════════════════════════════════════════
# سازنده: امیر علی فروزان اصل
# نسخه: 2.0.0
# قابلیت‌ها: جستجوی آهنگ، متن آهنگ، ویس، ویدیو، فایل صوتی
# ═══════════════════════════════════════════════════════════════════

import os
import sys
import json
import logging
import asyncio
import requests
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, List, Dict

import telebot
from telebot import types
from telebot.handler_backends import State, StatesGroup

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

# ─── بارگذاری تنظیمات از محیط ───────────────────────────────────
API_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
API_BASE = "https://api.music.example.com/v1"
SEARCH_TIMEOUT = 15
MAX_RESULTS = 10

if API_TOKEN == "YOUR_BOT_TOKEN":
    logger.error("❌ توکن ربات تنظیم نشده! متغیر BOT_TOKEN را تنظیم کنید.")
    sys.exit(1)

# ─── مقداردهی ربات ───────────────────────────────────────────────
bot = telebot.TeleBot(API_TOKEN, parse_mode="HTML")

# ─── مدیریت وضعیت کاربران ───────────────────────────────────────
class SearchStates(StatesGroup):
    waiting_query = State()
    waiting_selection = State()

# ذخیره موقت نتایج جستجو برای هر کاربر
user_cache: Dict[int, List[dict]] = {}
user_modes: Dict[int, str] = {}  # track | voice | video | lyrics


@dataclass
class Track:
    """مدل داده‌ای یک آهنگ."""
    title: str
    artist: str
    duration: int = 0
    audio_url: str = ""
    video_url: str = ""
    cover_url: str = ""

    @property
    def formatted(self) -> str:
        mins, secs = divmod(self.duration, 60)
        return f"🎵 <b>{self.title}</b>\n👤 {self.artist} | ⏱ {mins:02d}:{secs:02d}"


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
    logger.info(f"کاربر جدید: {user.id} - {user.full_name}")
    welcome = (
        f"🎶 سلام <b>{user.first_name}</b> عزیز!\n\n"
        "به ربات <b>آهنگ‌یاب حرفه‌ای</b> خوش آمدید. 🎧\n\n"
        "🔍 نام آهنگ یا خواننده رو بفرستید تا براتون پیدا کنم.\n"
        "📝 میتونید متن آهنگ هم بگیرید.\n"
        "🎤 ویس و 🎬 ویدیو آهنگ هم در دسترس شماست.\n\n"
        "⚡ <i>سازنده: امیر علی فروزان اصل</i>"
    )
    bot.send_message(message.chat.id, welcome, reply_markup=main_keyboard())


# ─── هندلر /help ─────────────────────────────────────────────────
@bot.message_handler(commands=["help"])
def cmd_help(message):
    help_text = (
        "📖 <b>راهنمای ربات آهنگ‌یاب</b>\n\n"
        "🎵 <b>جستجوی آهنگ</b> — نام آهنگ یا خواننده رو بفرستید\n"
        "📝 <b>متن آهنگ</b> — متن کامل ترانه رو دریافت کنید\n"
        "🎤 <b>ویس آهنگ</b> — فایل صوتی آهنگ رو بگیرید\n"
        "🎬 <b>ویدیو آهنگ</b> — موزیک‌ویدیو رو دریافت کنید\n"
        "📊 <b>آمار ربات</b> — تعداد کاربران و جستجوها\n\n"
        "⚡ <i>سازنده: امیر علی فروزان اصل</i>"
    )
    bot.send_message(message.chat.id, help_text)


# ─── هندلر /about ────────────────────────────────────────────────
@bot.message_handler(func=lambda m: m.text == "👤 درباره سازنده")
def cmd_about(message):
    about = (
        "👤 <b>درباره سازنده</b>\n\n"
        "🧑‍💻 <b>امیر علی فروزان اصل</b>\n"
        "🔧 نسخه ربات: <code>2.0.0</code>\n"
        "🐍 زبان: Python 3.11+\n"
        "📚 کتابخانه: pyTelegramBotAPI\n\n"
        "📧 ارتباط: @amirforozanasl"
        "⭐ <i>ساخته شده با عشق</i>"
    )
    bot.send_message(message.chat.id, about)


# ─── جستجوی آهنگ از API ──────────────────────────────────────────
def search_tracks(query: str, search_type: str = "track") -> List[Track]:
    """جستجوی آهنگ از طریق API خارجی با مدیریت خطا."""
    try:
        response = requests.get(
            f"{API_BASE}/search",
            params={"q": query, "type": search_type, "limit": MAX_RESULTS},
            timeout=SEARCH_TIMEOUT,
            headers={"User-Agent": "MusicBot/2.0"}
        )
        response.raise_for_status()
        data = response.json()
        tracks = []
        for item in data.get("results", []):
            tracks.append(Track(
                title=item.get("title", "نامشخص"),
                artist=item.get("artist", "نامشخص"),
                duration=item.get("duration", 0),
                audio_url=item.get("audio_url", ""),
                video_url=item.get("video_url", ""),
                cover_url=item.get("cover_url", ""),
            ))
        return tracks
    except requests.Timeout:
        logger.error(f"تایم‌اوت در جستجو: {query}")
        return []
    except requests.RequestException as e:
        logger.error(f"خطای API: {e}")
        return []


# ─── هندلر جستجوی آهنگ ───────────────────────────────────────────
@bot.message_handler(func=lambda m: m.text == "🎵 جستجوی آهنگ")
def handle_search_track(message):
    user_modes[message.chat.id] = "track"
    bot.send_message(message.chat.id, "🔍 نام آهنگ یا خواننده رو بفرستید:")
    bot.set_state(message.from_user.id, SearchStates.waiting_query, message.chat.id)


# ─── هندلر ویس آهنگ ──────────────────────────────────────────────
@bot.message_handler(func=lambda m: m.text == "🎤 ویس آهنگ")
def handle_search_voice(message):
    user_modes[message.chat.id] = "voice"
    bot.send_message(message.chat.id, "🎤 نام آهنگ رو بفرستید تا ویسش رو بفرستم:")
    bot.set_state(message.from_user.id, SearchStates.waiting_query, message.chat.id)


# ─── هندلر ویدیو آهنگ ────────────────────────────────────────────
@bot.message_handler(func=lambda m: m.text == "🎬 ویدیو آهنگ")
def handle_search_video(message):
    user_modes[message.chat.id] = "video"
    bot.send_message(message.chat.id, "🎬 نام آهنگ رو بفرستید تا ویدیوش رو پیدا کنم:")
    bot.set_state(message.from_user.id, SearchStates.waiting_query, message.chat.id)


# ─── هندلر متن آهنگ ──────────────────────────────────────────────
@bot.message_handler(func=lambda m: m.text == "📝 متن آهنگ")
def handle_search_lyrics(message):
    user_modes[message.chat.id] = "lyrics"
    bot.send_message(message.chat.id, "📝 نام آهنگ رو بفرستید تا متنش رو پیدا کنم:")
    bot.set_state(message.from_user.id, SearchStates.waiting_query, message.chat.id)


# ─── پردازش جستجو ────────────────────────────────────────────────
@bot.message_handler(state=SearchStates.waiting_query)
def process_search(message):
    query = message.text.strip()
    if not query:
        bot.send_message(message.chat.id, "❌ لطفاً متن معتبر بفرستید.")
        return

    chat_id = message.chat.id
    mode = user_modes.get(chat_id, "track")
    bot.delete_state(message.from_user.id, chat_id)

    bot.send_chat_action(chat_id, "typing")
    logger.info(f"جستجو [{mode}]: '{query}' توسط {message.from_user.id}")

    tracks = search_tracks(query, search_type="video" if mode == "video" else "track")

    if not tracks:
        bot.send_message(chat_id, "❌ نتیجه‌ای پیدا نشد. دوباره تلاش کنید.")
        return

    user_cache[chat_id] = [t.__dict__ for t in tracks]

    if mode == "lyrics":
        bot.send_chat_action(chat_id, "typing")
        lyrics = fetch_lyrics(tracks[0])
        bot.send_message(chat_id, f"📝 <b>{tracks[0].title}</b>\n\n{lyrics[:3500]}")
        return

    text = f"🔎 نتایج جستجو برای: <b>{query}</b>\n\n"
    for i, track in enumerate(tracks[:MAX_RESULTS], 1):
        text += f"{i}. {track.formatted}\n"
    text += "\n📌 شماره آهنگ رو بفرستید."
    bot.send_message(chat_id, text)
    bot.set_state(message.from_user.id, SearchStates.waiting_selection, chat_id)


# ─── دریافت متن آهنگ ─────────────────────────────────────────────
def fetch_lyrics(track: Track) -> str:
    try:
        response = requests.get(
            f"https://api.lyrics.ovh/v1/{track.artist}/{track.title}",
            timeout=SEARCH_TIMEOUT
        )
        data = response.json()
        return data.get("lyrics", "❌ متن پیدا نشد.")
    except Exception as e:
        logger.error(f"خطا در دریافت متن: {e}")
        return "❌ متاسفانه متن آهنگ دریافت نشد."


# ─── انتخاب و دانلود ────────────────────────────────────────────
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
    caption = f"🎵 <b>{track['title']}</b>\n👤 {track['artist']}\n\n⚡ @MusicFinderBot"

    try:
        if mode == "voice":
            bot.send_chat_action(chat_id, "record_audio")
            bot.send_voice(chat_id, track.get("audio_url", ""), caption=caption)
        elif mode == "video":
            bot.send_chat_action(chat_id, "upload_video")
            bot.send_video(chat_id, track.get("video_url", ""), caption=caption)
        else:
            bot.send_chat_action(chat_id, "upload_audio")
            bot.send_audio(
                chat_id, track.get("audio_url", ""),
                title=track["title"], performer=track["artist"], caption=caption
            )
        logger.info(f"ارسال موفق [{mode}]: {track['title']}")
    except Exception as e:
        logger.error(f"خطا در ارسال: {e}")
        bot.send_message(chat_id, "⚠️ خطا در ارسال آهنگ. لطفاً دوباره تلاش کنید.")


# ─── آمار ربات (فقط ادمین) ──────────────────────────────────────
@bot.message_handler(func=lambda m: m.text == "📊 آمار ربات")
def cmd_stats(message):
    if message.from_user.id != ADMIN_ID and ADMIN_ID != 0:
        bot.send_message(message.chat.id, "⛔ این بخش فقط برای ادمین قابل دسترسی است.")
        return
    stats = (
        "📊 <b>آمار ربات</b>\n\n"
        f"👥 کاربران فعال در حافظه: <b>{len(user_cache)}</b>\n"
        f"🎵 جستجوهای ذخیره‌شده: <b>{sum(len(v) for v in user_cache.values())}</b>\n"
        f"🕐 زمان سرور: <code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</code>"
    )
    bot.send_message(message.chat.id, stats)


# ─── جستجوی سریع (هر متنی) ──────────────────────────────────────
@bot.message_handler(func=lambda m: True, content_types=["text"])
def quick_search(message):
    user_modes[message.chat.id] = "track"
    bot.set_state(message.from_user.id, SearchStates.waiting_query, message.chat.id)
    process_search(message)


# ─── هندلر خطاهای اصلی ──────────────────────────────────────────



# ─── اجرای ربات ─────────────────────────────────────────────────
def main():
    logger.info("🎵 ربات آهنگ‌یاب نسخه 2.0.0 آماده کار است")
    logger.info("⚡ سازنده: امیر علی فروزان اصل")
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
