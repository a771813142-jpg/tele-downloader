import os
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from telebot.async_telebot import AsyncTeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import yt_dlp

# خادم ويب مدمج لإبقاء الخدمة نشطة على Render
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, format, *args):
        return

def start_health_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()

BOT_TOKEN = "8950979397:AAFQF-5yTZO6oa_siI7tY6Owvij2av_DDsA"
bot = AsyncTeleBot(BOT_TOKEN)

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# حفظ الروابط لتشغيل خيارات HD و MP3
user_urls = {}

@bot.message_handler(commands=['start'])
async def send_welcome(message):
    user_name = message.from_user.first_name or "صديقي"
    
    welcome_text = (
        f"👋 مرحباً ({user_name})\n\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        "📩 أرسل أي رابط وسأحمله لك فوراً\n\n"
        "المنصات المدعومة:\n"
        "📸 Instagram • 🔊 X (Twitter)\n"
        "🎵 TikTok • ▶️ YouTube\n"
        "👻 Snapchat • 📌 Pinterest\n"
        "🧵 Threads\n\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        "📖 داخل المجموعات:\n"
        "رابط ← تحميل /d\n"
        "رابط ← فيديو يوتيوب /v\n\n"
        "أو رد على رسالة بـ /d"
    )

    markup = InlineKeyboardMarkup(row_width=2)
    btn_yt = InlineKeyboardButton("اليوتيوب", callback_data="info_yt")
    btn_ig = InlineKeyboardButton("الانستكرام", callback_data="info_ig")
    btn_fb = InlineKeyboardButton("الفيسبوك", callback_data="info_fb")
    btn_tt = InlineKeyboardButton("التيك توك", callback_data="info_tt")
    btn_likee = InlineKeyboardButton("لايكي", callback_data="info_likee")
    btn_snap = InlineKeyboardButton("سناب جات", callback_data="info_snap")
    btn_tw = InlineKeyboardButton("تويتر", callback_data="info_tw")
    btn_pin = InlineKeyboardButton("بنترست", callback_data="info_pin")
    btn_stats = InlineKeyboardButton("📊 إحصائياتي", callback_data="info_stats")
    btn_add = InlineKeyboardButton("➕ أضف البوت لمجموعتك", url=f"https://t.me/{(await bot.get_me()).username}?startgroup=true")

    markup.add(btn_yt)
    markup.add(btn_ig, btn_fb)
    markup.add(btn_likee, btn_tt)
    markup.add(btn_snap, btn_tw)
    markup.add(btn_pin)
    markup.add(btn_stats)
    markup.add(btn_add)

    await bot.reply_to(message, welcome_text, reply_markup=markup)

@bot.message_handler(func=lambda message: message.text and ("http://" in message.text or "https://" in message.text))
async def handle_url(message):
    url = message.text.strip()
    status_msg = await bot.reply_to(message, "⏳ جاري التحميل والمعالجة...")
    
    file_path = f"{DOWNLOAD_DIR}/{message.chat.id}_{message.message_id}.mp4"
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': file_path,
        'quiet': True,
        'max_filesize': 50 * 1024 * 1024
    }

    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(ydl_opts).download([url]))

        user_urls[message.message_id] = url

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
        await bot.edit_message_text("❌ تعذر التحميل، تأكد من صحة الرابط والحجم المسموح.", message.chat.id, status_msg.message_id)
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

@bot.callback_query_handler(func=lambda call: call.data.startswith("info_"))
async def info_callback_handler(call):
    await bot.answer_callback_query(call.id, "أرسل رابط المنصة مباشرة ليتم تحميله فوراً!", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith("audio|") or call.data.startswith("hd|"))
async def action_callback_handler(call):
    action, msg_id_str = call.data.split("|")
    msg_id = int(msg_id_str)
    url = user_urls.get(msg_id)

    if not url:
        await bot.answer_callback_query(call.id, "⚠️ انتهت صلاحية الطلب، أرسل الرابط من جديد.")
        return

    if action == "hd":
        await bot.answer_callback_query(call.id, "🎬 جاري جلب أعلى دقة متوفرة...")
        wait_msg = await bot.send_message(call.message.chat.id, "⏳ جاري تنزيل نسخة HD بأعلى جودة...")
        hd_path = f"{DOWNLOAD_DIR}/hd_{call.message.chat.id}_{call.id}.mp4"
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': hd_path,
            'quiet': True,
            'max_filesize': 50 * 1024 * 1024
        }
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(ydl_opts).download([url]))
            with open(hd_path, 'rb') as video_file:
                await bot.send_video(chat_id=call.message.chat.id, video=video_file, caption="🎬 تم تنزيل الفيديو بأعلى جودة (HD) بنجاح!")
            await bot.delete_message(call.message.chat.id, wait_msg.message_id)
        except Exception:
            await bot.edit_message_text("❌ تعذر جلب نسخة HD، قد يتجاوز الملف الحجم الأقصى (50MB).", call.message.chat.id, wait_msg.message_id)
        finally:
            if os.path.exists(hd_path):
                os.remove(hd_path)

    elif action == "audio":
        await bot.answer_callback_query(call.id, "🎵 جاري استخراج الصوت بصيغة MP3...")
        wait_msg = await bot.send_message(call.message.chat.id, "⏳ جاري استخراج وتحويل الصوت...")
        audio_path = f"{DOWNLOAD_DIR}/audio_{call.message.chat.id}_{call.id}.mp3"
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': audio_path,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True,
            'max_filesize': 50 * 1024 * 1024
        }
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(ydl_opts).download([url]))
            target_file = audio_path if os.path.exists(audio_path) else f"{audio_path}.mp3"
            with open(target_file, 'rb') as audio_file:
                await bot.send_audio(chat_id=call.message.chat.id, audio=audio_file, caption="🎵 تم استخراج الصوت بنجاح!")
            await bot.delete_message(call.message.chat.id, wait_msg.message_id)
            if os.path.exists(target_file):
                os.remove(target_file)
        except Exception:
            await bot.edit_message_text("❌ تعذر استخراج الصوت من هذا الرابط.", call.message.chat.id, wait_msg.message_id)

if __name__ == '__main__':
    threading.Thread(target=start_health_server, daemon=True).start()
    asyncio.run(bot.polling(non_stop=True))
