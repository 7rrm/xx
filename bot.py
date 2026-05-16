import requests
import json
import telebot
import re
from telebot import types
import os
import threading
import yt_dlp

TELEGRAM_TOKEN = "8722624224:AAHsg9Q-yFY6-lllvkkYVvDyEYkra5-_zs0"
bot = telebot.TeleBot(TELEGRAM_TOKEN)

try:
    BOT_USERNAME = bot.get_me().username
except Exception as e:
    print(f"Failed to get bot username: {e}. Using a placeholder.")
    BOT_USERNAME = "t6ttbot"

OFFICIAL_BOT_USERNAME = "t6ttbot"
DEVELOPER_USERNAME_MD = "Yaa_Y"
DEVELOPER_CHAT_ID = 8312004279

notified_users = set()
WELCOME_PHOTO_URL = "https://t.me/hwgf100/48"

def download_audio_from_url(youtube_url, chat_id, message_id, user_id):
    processing_msg = None
    try:
        if message_id:
            processing_msg = bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text="جاري تجهيز الاغنية، يرجى الانتظار.."
            )
        else:
            processing_msg = bot.send_message(chat_id, "جاري تجهيز الاغنية، يرجى الانتظار..")
    except Exception as e:
        processing_msg = bot.send_message(chat_id, "جاري تجهيز الاغنية، يرجى الانتظار..")

    try:
        video_id = None
        if "youtube.com/watch?v=" in youtube_url:
            video_id = youtube_url.split("v=")[1].split("&")[0]
        elif "youtu.be/" in youtube_url:
            video_id = youtube_url.split("youtu.be/")[1].split("?")[0]

        if not video_id:
            bot.delete_message(chat_id, processing_msg.message_id)
            bot.send_message(chat_id, "عذرا، رابط يوتيوب غير صالح.")
            return

        filename = f"{video_id}.mp3"
        
        ydl_opts = {
            'format': 'bestaudio[filesize<50M]/bestaudio',
            'outtmpl': filename,
            'quiet': True,
            'no_warnings': True,
            'extract_audio': True,
            'audio_format': 'mp3',
            'prefer_ffmpeg': False,
            'noplaylist': True,
            'socket_timeout': 30,
            'retries': 3
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=True)
            title_raw = info.get('title', 'Unknown Title')
            duration = info.get('duration', 0)

            if duration > 18000:
                bot.delete_message(chat_id, processing_msg.message_id)
                bot.send_message(chat_id, "عذرا، الفيديو اطول من 5 ساعات. لا يمكن تحميله.")
                if os.path.exists(filename):
                    os.remove(filename)
                return

        if not os.path.exists(filename) or os.path.getsize(filename) == 0:
            bot.delete_message(chat_id, processing_msg.message_id)
            bot.send_message(chat_id, "عذرا، فشل تحميل الاغنية. قد يكون الملف محميا.")
            return

        bot.delete_message(chat_id, processing_msg.message_id)
        bot.send_chat_action(chat_id, 'upload_audio')

        with open(filename, 'rb') as audio_file:
            file_size = os.path.getsize(filename) / (1024 * 1024)
            
            if file_size > 50:
                bot.send_message(chat_id, "عذرا، حجم الملف اكبر من 50 ميجابايت.")
                os.remove(filename)
                return

            caption_text = f"""
اسم الاغنية: {title_raw}
تم التحميل بواسطة: @{BOT_USERNAME}
"""

            performer_text = f"« @{OFFICIAL_BOT_USERNAME} ~ @{DEVELOPER_USERNAME_MD} »"

            caption_markup = types.InlineKeyboardMarkup()
            caption_markup.add(
                types.InlineKeyboardButton(
                    f"البوت الرسمي @{OFFICIAL_BOT_USERNAME}", 
                    url=f"https://t.me/{OFFICIAL_BOT_USERNAME}",
                    style="primary"
                )
            )

            bot.send_audio(
                chat_id,
                audio_file,
                caption=caption_text,
                title=title_raw[:100],
                performer=performer_text,
                reply_markup=caption_markup
            )

        os.remove(filename)

    except Exception as e:
        print(f"Error in download_audio_from_url: {e}")
        try:
            if processing_msg:
                bot.delete_message(chat_id, processing_msg.message_id)
        except:
            pass
        
        error_msg = str(e)
        if "Video unavailable" in error_msg:
            bot.send_message(chat_id, "عذرا، الفيديو غير متاح او محذوف.")
        elif "Sign in" in error_msg:
            bot.send_message(chat_id, "عذرا، هذا الفيديو يتطلب تسجيل الدخول.")
        elif "This video is private" in error_msg:
            bot.send_message(chat_id, "عذرا، هذا الفيديو خاص.")
        else:
            bot.send_message(chat_id, "عذرا، حدث خطا في التحميل\nحاول مرة اخرى لاحقا")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    notify_developer_once(message.from_user)
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    add_button = types.InlineKeyboardButton(
        text="اضافة البوت للمجموعة",
        url=f"https://t.me/{BOT_USERNAME}?startgroup=true",
        style="primary"
    )
    usage_button = types.InlineKeyboardButton(
        text="استخدام داخل البوت",
        callback_data="show_usage",
        style="success"
    )
    markup.add(add_button, usage_button)

    welcome_caption = f"""
مرحبا بك عزيزي
انا بوت مساعد لــ Leo 
يجب اضافتي للمجموعة او القناة للعمل
اضفني من خلال الزر في الاسفل

المطور: @{DEVELOPER_USERNAME_MD}
"""

    try:
        bot.send_photo(
            message.chat.id,
            WELCOME_PHOTO_URL,
            caption=welcome_caption,
            reply_markup=markup
        )
    except Exception as e:
        print(f"Error sending photo: {e}")
        bot.reply_to(message, welcome_caption, reply_markup=markup)

def notify_developer_once(user):
    user_id = user.id
    if user_id not in notified_users:
        try:
            user_info = f"مستخدم جديد بدا البوت:\nالاسم: {user.first_name}"
            if user.last_name:
                user_info += f" {user.last_name}"
            if user.username:
                user_info += f"\nالمعرف: @{user.username}"
            user_info += f"\nالايدي: {user.id}"
            bot.send_message(DEVELOPER_CHAT_ID, user_info)
            notified_users.add(user_id)
        except Exception as e:
            print(f"Failed to notify developer: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "show_usage")
def show_usage_instructions(call):
    usage_text = f"""
طريقة استخدام البوت داخل المحادثة الخاصة والمجموعات والقنوات:

1. ارسل الامر: يوت متبوعا باسم الاغنية
   مثال: يوت احنه البيكيسي

2. سيظهر لك البوت 5 نتائج بحث من يوتيوب

3. اختر الاغنية المطلوبة من الازرار

4. انتظر قليلا وسيتم ارسال الملف الصوتي MP3

ملاحظات:
- الحد الاقصى لمدة الفيديو: 5 ساعات
- الحد الاقصى لحجم الملف: 50 ميجابايت
- للاستخدام داخل القنوات، يجب ان يكون البوت مشرفا ولديه صلاحية قراءة الرسائل.

للبدء مباشرة: 
ارسل الان يوت + اسم الاغنية في هذه المحادثة
"""
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    add_group_btn = types.InlineKeyboardButton(
        text="اضافة البوت للمجموعة",
        url=f"https://t.me/{BOT_USERNAME}?startgroup=true",
        style="success"
    )
    back_btn = types.InlineKeyboardButton(
        text="العودة للقائمة الرئيسية",
        callback_data="back_to_start",
        style="danger"
    )
    markup.add(add_group_btn, back_btn)
    
    try:
        bot.edit_message_caption(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            caption=usage_text,
            reply_markup=markup,
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"Error editing caption: {e}")
        bot.send_message(
            call.message.chat.id,
            usage_text,
            reply_markup=markup,
            parse_mode="Markdown"
        )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "back_to_start")
def back_to_start(call):
    markup = types.InlineKeyboardMarkup(row_width=1)
    add_button = types.InlineKeyboardButton(
        text="اضافة البوت للمجموعة",
        url=f"https://t.me/{BOT_USERNAME}?startgroup=true",
        style="primary"
    )
    usage_button = types.InlineKeyboardButton(
        text="استخدام داخل البوت",
        callback_data="show_usage",
        style="success"
    )
    markup.add(add_button, usage_button)

    welcome_caption = f"""
مرحبا بك عزيزي
انا بوت مساعد لــ Leo 
يجب اضافتي للمجموعة او القناة للعمل
اضفني من خلال الزر في الاسفل

المطور: @{DEVELOPER_USERNAME_MD}
"""

    try:
        media = types.InputMediaPhoto(
            media=WELCOME_PHOTO_URL,
            caption=welcome_caption
        )
        bot.edit_message_media(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            media=media,
            reply_markup=markup
        )
    except Exception as e:
        print(f"Error editing media: {e}")
        bot.send_photo(
            call.message.chat.id,
            WELCOME_PHOTO_URL,
            caption=welcome_caption,
            reply_markup=markup
        )
    bot.answer_callback_query(call.id)

# معالج الرسائل العادية (المجموعات والخاص)
@bot.message_handler(func=lambda msg: msg.text and msg.text.lower().startswith("يوت "))
def search_youtube_message(message):
    process_youtube_search(message)

# معالج رسائل القنوات
@bot.channel_post_handler(func=lambda msg: msg.text and msg.text.lower().startswith("يوت "))
def search_youtube_channel(message):
    process_youtube_search(message)

def process_youtube_search(message):
    query = message.text[len("يوت "):].strip()
    if not query:
        bot.reply_to(message, "يرجى كتابة اسم الاغنية بعد كلمة 'يوت'\n   مثال: يوت احنه البيكيسي")
        return

    search_indicator_msg = bot.reply_to(message, "جاري البحث عن طلبك...")
    bot.send_chat_action(message.chat.id, 'typing')

    search_url = "https://www.youtube.com/results"
    try:
        html = requests.get(search_url, params={"search_query": query}, timeout=10).text
    except requests.exceptions.RequestException as e:
        if search_indicator_msg:
            bot.delete_message(message.chat.id, search_indicator_msg.message_id)
        bot.reply_to(message, "حدث خطا اثناء الاتصال بالانترنت")
        return

    match = re.search(r"var ytInitialData = ({.*?});</script>", html)
    if not match:
        if search_indicator_msg:
            bot.delete_message(message.chat.id, search_indicator_msg.message_id)
        bot.reply_to(message, "لم اتمكن من تحليل نتائج البحث من يوتيوب")
        return

    try:
        data = json.loads(match.group(1))
        contents = data['contents']['twoColumnSearchResultsRenderer']['primaryContents']['sectionListRenderer']['contents']
        items = contents[0]['itemSectionRenderer']['contents']

        results = []
        for item in items:
            if 'videoRenderer' in item:
                video = item['videoRenderer']
                video_id = video['videoId']
                title = video['title']['runs'][0]['text']
                results.append((title, video_id))
            if len(results) >= 5:
                break

        if search_indicator_msg:
            bot.delete_message(message.chat.id, search_indicator_msg.message_id)

        if not results:
            bot.reply_to(message, f"لم يتم العثور على اي نتائج بحث لـ: {query}")
            return

        markup = types.InlineKeyboardMarkup(row_width=1)
        for title, vid in results:
            short_title = title[:35] + "..." if len(title) > 35 else title
            markup.add(
                types.InlineKeyboardButton(
                    text=f"{short_title}", 
                    callback_data=f"ytmp3|{vid}",
                    style="success"
                )
            )

        bot.reply_to(message, "اختر الاغنيه المطلوبة لتحويلها الى MP3:", reply_markup=markup)

    except Exception as e:
        if search_indicator_msg:
            bot.delete_message(message.chat.id, search_indicator_msg.message_id)
        print(f"Error during YouTube search: {e}")
        bot.reply_to(message, "خطا غير متوقع")

@bot.callback_query_handler(func=lambda call: call.data.startswith("ytmp3|"))
def handle_download(call):
    video_id = call.data.split("|")[1]
    url = f"https://www.youtube.com/watch?v={video_id}"

    try:
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="جاري تجهيز الاغنية، يرجى الانتظار..",
            reply_markup=None
        )
    except Exception as edit_err:
        print(f"Error editing message in callback: {edit_err}")
        bot.answer_callback_query(call.id, "جار تحميل الملف الصوتي...")

    thread = threading.Thread(target=download_audio_from_url, args=(url, call.message.chat.id, call.message.message_id, call.from_user.id))
    thread.start()

if __name__ == '__main__':
    print(f"Bot @{BOT_USERNAME} started successfully!")
    print(f"Official Bot: @{OFFICIAL_BOT_USERNAME}")
    try:
        bot.remove_webhook()
        bot.infinity_polling(timeout=60, long_polling_timeout=30, skip_pending=True)
    except Exception as e:
        print(f"Bot polling failed: {e}")
    finally:
        print(f"Bot @{BOT_USERNAME} stopped.")
