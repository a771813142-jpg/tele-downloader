import os
import asyncio
from telebot.async_telebot import AsyncTeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import yt_dlp

BOT_TOKEN = "8950979397:AAFDIKlzr-aGl6i_YTPmQOG8W66FnHee2hY"
bot = AsyncTeleBot(BOT_TOKEN)

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

@bot.message_handler(commands=['start', 'help'])
async def send_welcome(message):
    await bot.reply_to(message, "أهلاً بك! أرسل رابط الفيديو لتحميله مع خيارات الصوت وجودة HD.")

@bot.message_handler(func=lambda message: message.text and ("http://" in message.text or "https://" in message.text))
async def handle_url(message):
    url = message.text.strip()
    status_msg = await bot.reply_to(message, "⏳ جاري التحميل والمعالجة...")
    
    file_path = f"{DOWNLOAD_DIR}/{message.chat.id}_{message.message_id}.mp4"
    ydl_opts = {
        'format': 'best',
        'outtmpl': file_path,
        'quiet': True,
        'max_filesize': 50 * 1024 * 1024
    }

    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(ydl_opts).download([url]))

        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("🎵 تحويل إلى صوت MP3", callback_data=f"audio|{message.message_id}"),
            InlineKeyboardButton("🎬 تحميل بدقة HD", callback_data=f"hd|{message.message_id}")
        )

        with open(file_path, 'rb') as video_file:
            await bot.send_video(
                chat_id=message.chat.id,
                video=video_file,
                caption="✅ تم التحميل بنجاح!\nاختر الإجراء المطلوب:",
                reply_markup=markup
            )

        await bot.delete_message(message.chat.id, status_msg.message_id)

    except Exception:
        await bot.edit_message_text("❌ تعذر التحميل، تأكد من صحة الرابط والحجم.", message.chat.id, status_msg.message_id)
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

@bot.callback_query_handler(func=lambda call: call.data.startswith("audio") or call.data.startswith("hd"))
async def callback_handler(call):
    action = call.data.split("|")[0]
    if action == "audio":
        await bot.answer_callback_query(call.id, "🎵 جاري استخراج الصوت...")
    elif action == "hd":
        await bot.answer_callback_query(call.id, "🎬 جاري جلب دقة HD...")

if __name__ == '__main__':
    asyncio.run(bot.polling(non_stop=True))
