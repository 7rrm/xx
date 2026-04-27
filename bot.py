
import tempfile
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from telethon import events
from telethon.tl.functions.channels import JoinChannelRequest
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import asyncio
import json
import logging
import os
import sqlite3
from datetime import datetime, timedelta
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.tl.types import Channel, Chat
# إعدادات التسجيل (Logging)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# إعدادات Telethon
app_id = 23032698
api_hash = '99ad65a5fcd38203621cb20acd2aaba5'

# قائمة الجلسات (تمت إزالة الجلسة المحددة)
session_strings = []

# جلسة ثابتة (ضع جلسة حسابك هنا)


# قائمة العملاء (الجلسات الفعالة)
clients = {}

session_found = False  # قيمة افتراضية



# قائمة مستخدمي البوت
bot_users = set()

# معرف الشخص الذي يستطيع رؤية الجلسات
ADMIN_ID = 5427469031

# توكن البوت
TOKEN = "7145022358:AAH8Mo5WzM3HTCibUqZ-E2RYcLPXmf6b8BY"

# متغيرات التحكم في النشر التلقائي
stopped_chats = set()  # المحادثات التي تم إيقاف النشر فيها
stop_all = False  # التحكم في إيقاف النشر في جميع المحادثات

# ملف JSON للتخزين
JSON_FILE = "sessions.txt"
PUBLISHING_FILE = "publishing.json"

session_tasks = {}  # session_string -> list of asyncio.Task

RESPONSES_FILE = "responses.json"

def load_responses():
    if os.path.exists(RESPONSES_FILE):
        with open(RESPONSES_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_responses(data):
    with open(RESPONSES_FILE, 'w') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def load_user_replies(user_id):
    data = load_responses()
    return data.get(str(user_id), {})

def save_user_reply(user_id, key, value):
    data = load_responses()
    uid = str(user_id)
    if uid not in data:
        data[uid] = {}
    data[uid][key] = value
    save_responses(data)

def delete_user_reply(user_id, key):
    data = load_responses()
    uid = str(user_id)
    if uid in data and key in data[uid]:
        del data[uid][key]
        save_responses(data)
        return True
    return False

GROUPS_FILE = "groups.json"

def load_groups():
    """تحميل بيانات المجموعات من ملف JSON"""
    if os.path.exists(GROUPS_FILE):
        with open(GROUPS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_groups(groups):
    """حفظ بيانات المجموعات في ملف JSON"""
    with open(GROUPS_FILE, 'w') as f:
        json.dump(groups, f, indent=4)


# اسم ملف قاعدة البيانات
DB_FILE = "subscriptions.db"

def init_db():
    """تهيئة قاعدة البيانات"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # جدول الاشتراكات النشطة
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS active_subscriptions (
        user_id TEXT PRIMARY KEY,
        expiry_date TEXT
    )
    ''')
    
    # جدول أكواد الاشتراك المدفوعة
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS subscription_codes (
        code TEXT PRIMARY KEY,
        duration TEXT
    )
    ''')
    
    # جدول الأكواد المجانية
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS free_codes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT,
        duration TEXT,
        max_users INTEGER,
        used_users INTEGER DEFAULT 0
    )
    ''')
    
    conn.commit()
    conn.close()

def load_json():
    """تحميل حالات النشر من ملف JSON"""
    if os.path.exists(PUBLISHING_FILE):
        try:
            with open(PUBLISHING_FILE, 'r') as file:
                return json.load(file)
        except (json.JSONDecodeError, FileNotFoundError):
            return {"publishing_state": []}
    return {"publishing_state": []}

def save_json(data):
    """حفظ حالات النشر في ملف JSON"""
    with open(PUBLISHING_FILE, 'w') as file:
        json.dump(data, file, indent=4)

def save_session(session_string):
    """حفظ الجلسة في ملف TXT"""
    sessions = load_sessions()
    if session_string not in sessions:
        with open(JSON_FILE, 'a') as f:
            f.write(session_string + "\n")

def load_sessions():
    """تحميل الجلسات من ملف TXT"""
    if os.path.exists(JSON_FILE):
        with open(JSON_FILE, 'r') as f:
            sessions = [line.strip() for line in f if line.strip()]
            return sessions
    return []

def save_publishing_state(session_string, chat_id, message, sleep_time, repeat_count, current_count):
    """حفظ حالة النشر في ملف JSON"""
    data = load_json()
    data["publishing_state"].append({
        "session_string": session_string,
        "chat_id": chat_id,
        "message": message,
        "sleep_time": sleep_time,
        "repeat_count": repeat_count,
        "current_count": current_count
    })
    save_json(data)
def delete_session(session_string):
    """حذف الجلسة من ملف TXT"""
    sessions = load_sessions()
    if session_string in sessions:
        sessions.remove(session_string)
        with open(JSON_FILE, 'w') as f:
            for session in sessions:
                f.write(session + "\n")

async def check_subscription(user_id):
    """فحص صلاحية اشتراك المستخدم"""
    if user_id == ADMIN_ID:  # الأدمن يعتبر مشترك دائماً
        return True
        
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('SELECT expiry_date FROM active_subscriptions WHERE user_id = ?', (str(user_id),))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        expiry_date = datetime.strptime(result[0], "%Y-%m-%d %H:%M:%S")
        return expiry_date > datetime.now()
    return False
async def run_publishing(client, session_string, chat_id, message, sleep_time, repeat_count):
    try:
        for i in range(repeat_count):
            if stop_all or chat_id in stopped_chats:
                # إرسال رسالة شعار عند التوقف (اختياري)
                await client.send_message(chat_id, "تم إيقاف النشر، هذا هو شعارنا!")
                return
            await asyncio.sleep(sleep_time)
            await client.send_message(chat_id, message)

            # تحديث الحالة في JSON
            data = load_json()
            for state in data["publishing_state"]:
                if state["session_string"] == session_string and state["chat_id"] == chat_id:
                    state["current_count"] = i + 1
            save_json(data)

        # إرسال تقرير بعد الانتهاء
        try:
            await client.send_message(
                "me",
                f"✅ تم الانتهاء من النشر في المجموعة {chat_id}.\n"
                f"📤 عدد الرسائل المرسلة: {repeat_count}"
            )
        except Exception as e:
            logger.error(f"❌ فشل إرسال تقرير النشر: {e}")

        # حذف الحالة بعد انتهاء النشر
        data = load_json()
        data["publishing_state"] = [s for s in data["publishing_state"]
                                    if not (s["session_string"] == session_string and s["chat_id"] == chat_id)]
        save_json(data)

    except asyncio.CancelledError:
        logger.info(f"✅ تم إلغاء نشر الجلسة: {session_string[:10]}")
async def add_subscription(user_id, days=0, hours=0, minutes=0):
    """إضافة اشتراك للمستخدم"""
    expiry_date = datetime.now() + timedelta(days=days, hours=hours, minutes=minutes)
    expiry_str = expiry_date.strftime("%Y-%m-%d %H:%M:%S")
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
    INSERT OR REPLACE INTO active_subscriptions (user_id, expiry_date)
    VALUES (?, ?)
    ''', (str(user_id), expiry_str))
    
    conn.commit()
    conn.close()
    return expiry_date

async def remove_subscription(user_id):
    """إزالة اشتراك المستخدم"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM active_subscriptions WHERE user_id = ?', (str(user_id),))
    
    conn.commit()
    conn.close()

async def setup_client(session_string):
    """إنشاء عميل جديد وإضافة وظائفه"""
    try:
        client = TelegramClient(StringSession(session_string), app_id, api_hash)
        await client.start()
        logger.info(f"✅ تم تسجيل الدخول باستخدام الجلسة {session_string[:10]}... بنجاح!")

        # الانضمام إلى القنوات تلقائيًا
        try:
            await client(JoinChannelRequest('Mt_3u'))
            await client(JoinChannelRequest('nn00x'))
            logger.info(f"✅ تم انضمام الجلسة {session_string[:10]} إلى القنوات بنجاح.")
        except Exception as e:
            logger.error(f"❌ فشل الانضمام إلى القنوات: {e}")

        # إضافة العميل إلى القائمة
        clients[session_string] = client
        @client.on(events.NewMessage)
        async def auto_reply(event):
            try:
                # تأكد أن الرسالة عبارة عن رد
                if not event.is_reply:
                    return

                # محاولة جلب الرسالة الأصلية
                try:
                    original = await event.get_reply_message()
                except:
                    return  # فشل في جلبها

                me = await client.get_me()

                # تجاهل إذا لم تكن الرسالة الأصلية من نفس الحساب
                if not original or original.sender_id != me.id:
                    return

                text = event.raw_text.strip().lower()
                replies = load_user_replies(me.id)

                if text in replies:
                    await asyncio.sleep(5)
                    await event.reply(replies[text])

                    chat = await event.get_chat()
                    link = f"https://t.me/c/{str(chat.id).replace('-100', '')}/{event.id}"
                    await client.send_message(
                        "me",
                        f"📨 تم الرد على كلمة *{text}*\n🔗 [رابط الرسالة]({link})",
                        link_preview=False
                    )

            except Exception as e:
                logging.error(f"خطأ في auto_reply: {str(e)}")
                                 
        @client.on(events.NewMessage(outgoing=True, pattern=r"نشر (\d+) (\d+)"))
        async def swing(event):
            global stop_all
            chat_id = event.chat_id

            if stop_all:
                stop_all = False

            if chat_id in stopped_chats:
                stopped_chats.remove(chat_id)

            await event.delete()

            if event.is_reply:
                params = event.text.split(" ")
                try:
                    sleep_time = int(params[1])
                    repeat_count = int(params[2])
                    message = await event.get_reply_message()

                    # حفظ حالة النشر في ملف JSON
                    save_publishing_state(session_string, chat_id, message.text, sleep_time, repeat_count, 0)

                    # إنشاء مهمة نشر منفصلة
                    task = asyncio.create_task(run_publishing(
                        client, session_string, chat_id, message.text, sleep_time, repeat_count
                    ))

                    if session_string not in session_tasks:
                        session_tasks[session_string] = []
                    session_tasks[session_string].append(task)

                except (IndexError, ValueError):
                    await client.send_message("me", "❌ اكتب الأمر بشكل صحيح: نشر + عدد الثواني + عدد المرات")
            else:
                await client.send_message("me", "❌ يجب الرد على الرسالة التي تريد نشرها.")

        # أمر إيقاف النشر لمحادثة واحدة
        @client.on(events.NewMessage(outgoing=True, pattern=r"ايقاف النشر"))
        async def stop_chat(event):
            global stopped_chats
            chat_id = event.chat_id
            stopped_chats.add(chat_id)
            await event.delete()
            await client.send_message("me", f"✅ تم إيقاف النشر في المحادثة {chat_id}")




        # أمر إيقاف جميع النشر
        @client.on(events.NewMessage(outgoing=True, pattern=r"ايقاف الكل"))
        async def stop_all_chats(event):
            global stop_all
            stop_all = True
            await event.delete()
            await client.send_message("me", "✅ تم إيقاف جميع عمليات النشر!")





        return client
    except Exception as e:
        logger.error(f"❌ فشل في إعداد العميل: {e}")
        return None

async def start_all_clients():
    """تشغيل جميع الجلسات المخزنة واستئناف عمليات النشر"""
    session_strings.extend(load_sessions())
    tasks = [setup_client(session) for session in session_strings]
    await asyncio.gather(*tasks)
    logger.info("✅ جميع الحسابات تعمل وتم استئناف عمليات النشر...")



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """إرسال لوحة التحكم"""
    user_id = update.message.from_user.id
    bot_users.add(user_id)

    # الأدمن يعتبر مشترك دائماً
    if user_id == ADMIN_ID or await check_subscription(user_id):
        await show_main_menu(update, context)
    else:
        await show_subscription_menu(update, context)
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, query=None):
    """عرض القائمة الرئيسية المعدلة للمشتركين"""
    keyboard = [
        [InlineKeyboardButton("👤 التحكم بالحساب", callback_data="account_control")],
        [InlineKeyboardButton("👥 التحكم بالكروبات", callback_data="group_control")],
        [InlineKeyboardButton("📢 التحكم بالنشر", callback_data="publish_control")],
        [InlineKeyboardButton("🌚 طريقة استخراج جلسة", callback_data="stop_publishin"),
         InlineKeyboardButton("✅ طريقة استخدام البوت", callback_data="show_users")],
        [InlineKeyboardButton("المطور", url="https://t.me/bb44g"),
         InlineKeyboardButton("قناة المطور", url="https://t.me/nn00x")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        if query:
            await query.edit_message_text("🤖 مرحبًا بك في لوحة التحكم الرئيسية!", reply_markup=reply_markup)
        elif update and update.message:
            await update.message.reply_text("🤖 مرحبًا بك في لوحة التحكم الرئيسية!", reply_markup=reply_markup)
        elif update and update.callback_query:
            await update.callback_query.edit_message_text("🤖 مرحبًا بك في لوحة التحكم الرئيسية!", reply_markup=reply_markup)
        else:
            logger.error("لا يمكن عرض القائمة الرئيسية: لا يوجد update أو query صالح")
    except Exception as e:
        logger.error(f"حدث خطأ أثناء عرض القائمة الرئيسية: {e}")

async def account_control_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لوحة التحكم بالحساب"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("➕ إضافة حساب", callback_data="add_account"),
         InlineKeyboardButton("🗑️ حذف حساب", callback_data="delete_account")],
        [InlineKeyboardButton("👤 معلومات حسابك", callback_data="my_account")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "👤 لوحة التحكم بالحساب الشخصي",
        reply_markup=reply_markup
    )

async def group_control_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لوحة التحكم بالكروبات"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("➕ إضافة كروب", callback_data="add_group")],
        [InlineKeyboardButton("📋 مجموعاتي", callback_data="my_groups"),
         InlineKeyboardButton("🗑️ حذف كروب", callback_data="remove_group")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "👥 لوحة التحكم بالكروبات",
        reply_markup=reply_markup
    )

async def publish_control_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لوحة التحكم بالنشر"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("▶️ بدء النشر", callback_data="publish_menu"),
         InlineKeyboardButton("⏹️ إيقاف النشر", callback_data="stop_publishing")],
        [InlineKeyboardButton("➕ إضافة رد", callback_data="add_reply"),
         InlineKeyboardButton("🗑️ حذف رد", callback_data="delete_reply")],
        [InlineKeyboardButton("📄 الردود المخزنة", callback_data="list_replies")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("📢 لوحة التحكم في الردود التلقائية", reply_markup=reply_markup)
    

async def show_subscription_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض قائمة الاشتراك للغير مشتركين"""
    keyboard = [
        [InlineKeyboardButton("🔑 إدخال كود اشتراك", callback_data="enter_code")],
        [InlineKeyboardButton("💳 شراء كود اشتراك", callback_data="buy_code")],
        [InlineKeyboardButton("🎁 اشتراك مجاني", callback_data="free_code")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🔒 يبدو أنك غير مشترك!\n\n"
        "للاستمتاع بكامل ميزات البوت، يرجى الاشتراك:\n\n"
        "1. إدخال كود اشتراك إذا كنت تمتلك واحدًا\n"
        "2. شراء كود اشتراك جديد\n"
        "3. الحصول على كود تجريبي مجاني",
        reply_markup=reply_markup
    )

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لوحة تحكم الأدمن"""
    user_id = update.message.from_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("🚫 ليس لديك صلاحية الوصول إلى لوحة الأدمن!")
        return
    
    keyboard = [
    
        [InlineKeyboardButton("➕ إضافة كود اشتراك", callback_data="add_code")],
        [InlineKeyboardButton("🗑️ مسح كود اشتراك", callback_data="remove_code")],
        [InlineKeyboardButton("🎁 كود مجاني", callback_data="create_free_code")],
        [InlineKeyboardButton("📊 المشتركين النشطين", callback_data="active_subscribers")],
        [InlineKeyboardButton("🗑️ إزالة مشترك", callback_data="remove_subscriber")],
        [InlineKeyboardButton("📂 إحضار الجلسات", callback_data="get_sessions")],
        [InlineKeyboardButton("📥 إحضار ملف الجلسات", callback_data="get_sessions_file")],
        [InlineKeyboardButton("📤 إضافة ملف التخزين", callback_data="add_sessions_file")]        
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("👑 لوحة تحكم الأدمن", reply_markup=reply_markup)
async def has_user_session(user_id):
    for session in session_strings:
        try:
            temp_client = TelegramClient(StringSession(session), app_id, api_hash)
            await temp_client.connect()
            me = await temp_client.get_me()
            await temp_client.disconnect()
            if me.id == user_id:
                return True
        except:
            continue
    return False
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    # تحقق من الاشتراك
    is_subscribed = user_id == ADMIN_ID or await check_subscription(user_id)
    allowed_for_non_subscribers = ["enter_code", "buy_code", "free_code"]

    if not is_subscribed and query.data not in allowed_for_non_subscribers:
        await show_subscription_menu(query, context)
        return

    # معالجة أزرار القوائم الجديدة
    if query.data == "account_control":
        await account_control_menu(update, context)
        return
    
    elif query.data == "group_control":
        await group_control_menu(update, context)
        return
    
    elif query.data == "publish_control":
        await publish_control_menu(update, context)
        return
    
    elif query.data == "back_to_main":
        await show_main_menu(update, context)
        return
    


    # تحقق من وجود جلسة لبعض الأزرار
    buttons_need_session = [
        "my_account", "add_group", "remove_group",
        "my_groups", "publish_menu", "stop_publishing"
    ]
    if query.data in buttons_need_session:
        session_exists = False
        for session in session_strings:
            try:
                temp_client = TelegramClient(StringSession(session), app_id, api_hash)
                await temp_client.connect()
                me = await temp_client.get_me()
                await temp_client.disconnect()
                if me.id == user_id:
                    session_exists = True
                    break
            except:
                continue
        if not session_exists:
            await query.message.reply_text("❌ يجب عليك إضافة حساب أولاً لاستخدام هذا الأمر.")
            return

    # أزرار القائمة الرئيسية
    if query.data == "add_account":
        await query.message.reply_text("🔑 أرسل الجلسة الجديدة:")
        context.user_data["waiting_for_session"] = True

                    
                                        

    elif query.data == "add_reply":
        await query.message.reply_text("📝 أرسل الكلمة التي تريد الرد عليها:")
        context.user_data["waiting_for_reply_key"] = True

    elif query.data == "delete_reply":
        await query.message.reply_text("🗑️ أرسل الكلمة التي تريد حذف الرد الخاص بها:")
        context.user_data["waiting_for_delete_reply"] = True

    elif query.data == "list_replies":
        replies = load_user_replies(user_id)
        if not replies:
            await query.message.reply_text("📭 لا توجد ردود مخزنة.")
        else:
            text = "\n".join([f"{k} = {v}" for k, v in replies.items()])
            await query.message.reply_text(f"📄 ردودك المخزنة:\n\n{text}")                  
                                                      
                                                                                
                                                                                                                        
    elif query.data == "delete_account":
        await query.message.reply_text("🔑 أرسل الجلسة الخاصة بالحساب الذي تريد حذفه:")
        context.user_data["waiting_for_delete_session"] = True
    elif query.data == "my_account":
        session_found = False
        for session in session_strings:
            try:
                temp_client = TelegramClient(StringSession(session), app_id, api_hash)
                await temp_client.connect()
                me = await temp_client.get_me()
                if me.id == user_id:
                    session_found = True
                    info_text = (
                    f"✅ معلومات حسابك:\n\n"
                    f"👤 الاسم: {me.first_name or ''} {me.last_name or ''}\n"
                    f"🔖 اليوزر: @{me.username or 'غير متوفر'}\n"
                    f"🆔 الأيدي: {me.id}\n"
                    f"📞 الهاتف: +{me.phone}\n\n"
                    f"🔐 جلستك:\n<code>{session}</code>"
                )
                await query.message.reply_text(info_text, parse_mode="HTML")
                await temp_client.disconnect()
                break
                await temp_client.disconnect()
            except:
                continue
    elif query.data == "stop_publishin":
        await query.message.reply_text(f'''### أولًا: استخراج API ID و API HASH ###

1. ادخل إلى موقع my.telegram.org

2. أدخل رقم هاتفك مع رمز الدولة (مثال: +9647712345678)

3. ستصلك رسالة على التليجرام تحتوي على كود، قم بإدخال هذا الكود في الموقع

4. اضغط على "API development tools"

5. انسخ الـ API ID والـ API hash الظاهرين أمامك


### ثانيًا: استخراج جلسة التليجرام ###
قبل اي شي قم باختيار نوع الجلسه ( Telethon ) 

1. ادخل إلى موقع https://telegram.tools/session-string-generator

2. أدخل الـ API ID والـ API hash الذي حصلت عليهما

3. في الحقل الأخير، أدخل رقم هاتفك مع رمز الدولة (مثال: +9647712345678)

4. اضغط على "Next"

5. ستصلك رسالة على التليجرام تحتوي على كود، قم بإدخاله في الموقع

6. بعد ظهور الجلسة، اضغط على "Copy" لنسخها''')

    elif query.data == "show_users":
        await query.message.reply_text(f'''📌 شرح استخدام بوت النشر التلقائي  

🚀 المقدمة  
هذا البوت يساعدك في نشر الرسائل تلقائيًا في مجموعات وقنوات Telegram باستخدام حسابك الشخصي.  

🔹 الأوامر الأساسية  

1️⃣ أوامر النشر الرئيسية  
- نشر [الوقت] [عدد المرات]  
  مثال: نشر 10 5  
  - ينشر الرسالة كل 10 ثواني، ويكررها 5 مرات  
  - يجب الرد على الرسالة المراد نشرها  

- ايقاف النشر  
  - يوقف النشر في المجموعة الحالية فقط  

- ايقاف الكل  
  - يوقف جميع عمليات النشر  

2️⃣ لوحة التحكم  
- 👤 التحكم بالحساب: إضافة/حذف حساب  
- 👥 التحكم بالكروبات: إدارة المجموعات  
- 📢 التحكم بالنشر: بدء/إيقاف النشر  

📝 طريقة الاستخدام  

1️⃣ إضافة الحساب  
- اضغط "👤 التحكم بالحساب" → "➕ إضافة حساب"  
- أرسل جلسة الحساب (Telethon)  

2️⃣ إضافة المجموعات  
- اضغط "👥 التحكم بالكروبات" → "➕ إضافة كروب"  
- أرسل رابط المجموعة  

3️⃣ بدء النشر  
- اختر "▶️ بدء النشر"  
- حدد نوع النشر (مستمر أو محدد)  
- أرسل الرسالة وحدد الوقت وعدد المرات  

  

⚠️ ملاحظات مهمة  
- لا تستخدم البوت للسبام  
- يمكنك إضافة جلسه واحدة فقط لكل حساب  

📞 الدعم الفني  
- المطور: @bb44g  
- القناة: @nn00x  

🎁 نظام الاشتراكات  
- شراء كود اشتراك من المطور  
- أو الحصول على كود تجريبي مجاني''')

    
    elif query.data == "publish_menu":
        # عرض قائمة خيارات النشر
        keyboard = [
            [InlineKeyboardButton("🔄 نشر باستمرار", callback_data="continuous_publish")],
            [InlineKeyboardButton("🔢 نشر محدد", callback_data="limited_publish")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "📢 اختر نوع النشر الذي تريده:",
            reply_markup=reply_markup
        )
    
    elif query.data == "continuous_publish":
        await query.edit_message_text("📝 أرسل الرسالة التي تريد نشرها:")
        context.user_data["waiting_for_publish_message"] = True
        context.user_data["publish_type"] = "continuous"
    
    elif query.data == "limited_publish":
        await query.edit_message_text("📝 أرسل الرسالة التي تريد نشرها:")
        context.user_data["waiting_for_publish_message"] = True
        context.user_data["publish_type"] = "limited"
    
    elif query.data == "stop_publishing":
        groups_data = load_groups()
        user_groups = groups_data.get(str(user_id), [])
        
        if not user_groups:
            await query.answer("❌ ليس لديك أي كروبات مضافة للنشر.", show_alert=True)
            return
        
        # البحث عن جلسة المستخدم
        user_session = None
        for session in session_strings:
            try:
                temp_client = TelegramClient(StringSession(session), app_id, api_hash)
                await temp_client.connect()
                me = await temp_client.get_me()
                await temp_client.disconnect()
                if me.id == user_id:
                    user_session = session
                    break
            except:
                continue
        
        if not user_session:
            await query.answer("❌ لم يتم العثور على جلسة نشطة لحسابك.", show_alert=True)
            return
        
        # حساب عدد الرسائل التي تم نشرها فعلاً
        data = load_json()
        user_states = [s for s in data["publishing_state"] if s["session_string"] == user_session]
        total_messages = sum(s.get("current_count", 0) for s in user_states)
        total_groups = len(user_states)
        
        # إلغاء مهام النشر
        if user_session in session_tasks:
            for task in session_tasks[user_session]:
                task.cancel()
            del session_tasks[user_session]
        
        # إزالة حالات النشر من JSON
        data["publishing_state"] = [state for state in data["publishing_state"] 
                                  if state["session_string"] != user_session]
        save_json(data)
        
        # إرسال إشعار للمستخدم من خلال البوت
        await context.bot.send_message(
            chat_id=user_id,
            text=(
                "⏹️ تم إيقاف جميع عمليات النشر الخاصة بك.\n"
                f"📋 عدد الكروبات: {total_groups}\n"
                f"✉️ عدد الرسائل التي تم نشرها: {total_messages}"
            )
        )
        
        await query.answer("✅ تم إيقاف النشر وإرسال الإحصائيات.", show_alert=True)
    
    elif query.data == "back_to_main":
        await show_main_menu(update, context, query)
    
     
    elif query.data == "remove_subscriber":
        if user_id == ADMIN_ID:
            await query.message.reply_text("🗑️ الرجاء إرسال الـ ID الخاص بالمشترك الذي تريد إزالته:")
            context.user_data["waiting_for_remove_subscription"] = True
        else:
            await query.message.reply_text("🚫 ليس لديك صلاحية لاستخدام هذا الأمر.")                  
    
    # الأزرار الجديدة للمجموعات
    elif query.data == "add_group":
        # التحقق من وجود جلسة للمستخدم
        has_session = False
        for session in session_strings:
            try:
                temp_client = TelegramClient(StringSession(session), app_id, api_hash)
                await temp_client.connect()
                me = await temp_client.get_me()
                await temp_client.disconnect()
                if me.id == user_id:
                    has_session = True
                    break
            except:
                continue
        
        if has_session:
            await query.message.reply_text("🔗 أرسل رابط الكروب أو القناة:")
            context.user_data["waiting_for_group_link"] = True
        else:
            await query.message.reply_text("❌ يجب عليك إضافة جلسة أولاً قبل إضافة الكروب.")
    
    elif query.data == "remove_group":
        groups_data = load_groups()
        user_groups = groups_data.get(str(user_id), [])
        
        if not user_groups:
            await query.message.reply_text("❌ لم تقم بإضافة أي كروب حتى الآن.")
        else:
            await query.message.reply_text("🔗 أرسل رابط الكروب الذي تريد حذفه:")
            context.user_data["waiting_for_group_to_remove"] = True
    
    elif query.data == "my_groups":
        groups_data = load_groups()
        user_groups = groups_data.get(str(user_id), [])
        
        if not user_groups:
            await query.message.reply_text("📋 لم تقم بإضافة أي كروب حتى الآن.")
        else:
            buttons = []
            for group in user_groups:
                buttons.append([InlineKeyboardButton(group["name"], url=group["link"])])
            
            reply_markup = InlineKeyboardMarkup(buttons)
            await query.message.reply_text("📋 مجموعاتك المضافة:", reply_markup=reply_markup)            
    elif query.data == "get_sessions":
        if user_id == ADMIN_ID:
            if not clients:
                await query.message.reply_text("🚫 لا يوجد جلسات مضافة.")
                return

            sessions_text = ""
            count = 0

            for session, client in clients.items():
                try:
                    me = await client.get_me()
                    sessions_text += (
                        f"👤 الاسم: {me.first_name or ''} {me.last_name or ''}\n"
                        f"🔖 اليوزر: @{me.username or 'غير متوفر'}\n"
                        f"🆔 الأيدي: {me.id}\n"
                        f"📞 الهاتف: +{me.phone}\n\n"
                        f"🔐 جلسته:\n{session}\n\n"
                    )
                    count += 1
                except:
                    continue

            sessions_text += f"مجموع الجلسات: {{ {count} }}"

            import tempfile
            with tempfile.NamedTemporaryFile(mode='w+', encoding='utf-8', suffix=".txt", delete=False) as temp_file:
                temp_file.write(sessions_text)
                temp_path = temp_file.name

            await query.message.reply_document(
                document=open(temp_path, 'rb'),
                filename="الجلسات.txt",
                caption="📂 جميع الجلسات بصيغة نصية"
            )
            os.remove(temp_path)
        else:
            await query.message.reply_text("🚫 ليس لديك صلاحية لاستخدام هذا الأمر.")
    elif query.data == "get_sessions_file":
        if user_id == ADMIN_ID:
            if os.path.exists(JSON_FILE):
                await query.message.reply_document(document=open(JSON_FILE, 'rb'), caption="📂 ملف الجلسات:")
            else:
                await query.message.reply_text("🚫 لا يوجد ملف جلسات.")
        else:
            await query.message.reply_text("🚫 ليس لديك صلاحية لاستخدام هذا الأمر.")

    elif query.data == "add_sessions_file":
        if user_id == ADMIN_ID:
            await query.message.reply_text("📤 أرسل ملف الجلسات (JSON):")
            context.user_data["waiting_for_sessions_file"] = True
        else:
            await query.message.reply_text("🚫 ليس لديك صلاحية لاستخدام هذا الأمر.")

    # أزرار نظام الاشتراكات
    elif query.data == "enter_code":
        await query.message.reply_text("🔑 الرجاء إرسال كود الاشتراك:")
        context.user_data["waiting_for_code"] = True

    elif query.data == "buy_code":
        await query.message.reply_text('''💳 لشراء كود اشتراك، يرجى التواصل مع المطور:
@bb44g

اسعار الاشتراك:-
اسبوعين 1$
شهر 2$'''
        )

    elif query.data == "free_code":
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute('SELECT code, duration, max_users, used_users FROM free_codes ORDER BY id DESC LIMIT 1')
        result = cursor.fetchone()
        conn.close()
        
        if result:
            code, duration, max_users, used_users = result
            if used_users < max_users:
                await query.message.reply_text(
                    f"🎁 عزيزي المستخدم هذا كود مجاني مقدم من المطور لكي تقوم بتجربه البوت قبل الاشتراك المدفوع:\n\n"
                    f"( الكود: {code} )\n\n"
                    f"عدد المستخدمين المتبقيين: {max_users - used_users}"
                )
            else:
                await query.message.reply_text("❌ لقد تم استخدام الحد الأقصى لهذا الكود المجاني.")
        else:
            await query.message.reply_text("❌ لا يوجد أكواد مجانية متاحة حالياً.")

    # أزرار لوحة الأدمن
    elif query.data == "add_code":
        if user_id == ADMIN_ID:
            await query.message.reply_text("➕ الرجاء إرسال نص الكود الجديد:")
            context.user_data["waiting_for_new_code"] = True
        else:
            await query.message.reply_text("🚫 ليس لديك صلاحية لاستخدام هذا الأمر.")

    elif query.data == "remove_code":
        if user_id == ADMIN_ID:
            await query.message.reply_text("🗑️ الرجاء إرسال الكود الذي تريد حذفه:")
            context.user_data["waiting_for_code_to_remove"] = True
        else:
            await query.message.reply_text("🚫 ليس لديك صلاحية لاستخدام هذا الأمر.")

    elif query.data == "create_free_code":
        if user_id == ADMIN_ID:
            await query.message.reply_text("🎁 الرجاء إرسال نص الكود المجاني:")
            context.user_data["waiting_for_free_code"] = True
        else:
            await query.message.reply_text("🚫 ليس لديك صلاحية لاستخدام هذا الأمر.")

    elif query.data == "active_subscribers":
        if user_id == ADMIN_ID:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            
            cursor.execute('SELECT user_id, expiry_date FROM active_subscriptions')
            active_users = cursor.fetchall()
            conn.close()
            
            if not active_users:
                await query.message.reply_text("📊 لا يوجد مشتركين نشطين حالياً.")
                return
            
            message = "📊 قائمة المشتركين النشطين:\n\n"
            for user_id, expiry_date in active_users:
                expiry = datetime.strptime(expiry_date, "%Y-%m-%d %H:%M:%S")
                remaining = expiry - datetime.now()
                message += f"👤 User ID: {user_id}\n"
                message += f"⏳ تنتهي الصلاحية في: {expiry_date}\n"
                message += f"⏱️ المتبقي: {remaining.days} أيام, {remaining.seconds//3600} ساعات\n\n"
            
            await query.message.reply_text(message)
        else:
            await query.message.reply_text("🚫 ليس لديك صلاحية لاستخدام هذا الأمر.")

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """استقبال الرسائل المختلفة"""
    user_id = update.message.from_user.id
    text = update.message.text.strip()

    # الحالات التي لا تتطلب اشتراكاً
    no_subscription_needed = [
        "waiting_for_session",
        "waiting_for_delete_session",
        "waiting_for_code",
        "waiting_for_new_code",
        "waiting_for_new_code_duration",
        "waiting_for_code_to_remove",
        "waiting_for_free_code",
        "waiting_for_free_code_duration",
        "waiting_for_free_code_users",
        "waiting_for_sessions_file",
        "waiting_for_group_link",
        "waiting_for_group_to_remove",
        "waiting_for_publish_message",  # الحالة الجديدة
        "waiting_for_publish_interval",  # الحالة الجديدة
        "waiting_for_publish_count"  # الحالة الجديدة
    ]

    # التحقق مما إذا كان المستخدم في حالة لا تتطلب اشتراكاً
    needs_check = True
    for state in no_subscription_needed:
        if context.user_data.get(state):
            needs_check = False
            break

    # الأدمن يعتبر مشترك دائماً
    is_subscribed = user_id == ADMIN_ID or await check_subscription(user_id)
    
    if needs_check and not is_subscribed:
        await show_subscription_menu(update, context)
        return

    # معالجة إدخال كود الاشتراك
    if context.user_data.get("waiting_for_code"):
        activated = False
        
        # التحقق من الأكواد المدفوعة
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute('SELECT duration FROM subscription_codes WHERE code = ?', (text,))
        result = cursor.fetchone()
        
        if result:
            try:
                days, hours, minutes = map(int, result[0].split('/'))
                expiry_date = await add_subscription(user_id, days, hours, minutes)
                
                # حذف الكود بعد استخدامه
                cursor.execute('DELETE FROM subscription_codes WHERE code = ?', (text,))
                conn.commit()
                
                await update.message.reply_text(
                    f"✅ تم تفعيل الاشتراك بنجاح!\n"
                    f"⏳ تنتهي صلاحية اشتراكك في: {expiry_date.strftime('%Y-%m-%d %H:%M:%S')}"
                )
                await show_main_menu(update, context)
                activated = True
            except Exception as e:
                logger.error(f"Error activating subscription: {e}")
        
        # التحقق من الأكواد المجانية
        if not activated:
            cursor.execute('SELECT id, duration, max_users, used_users FROM free_codes WHERE code = ?', (text,))
            result = cursor.fetchone()
            
            if result:
                code_id, duration, max_users, used_users = result
                if used_users < max_users:
                    try:
                        days, hours, minutes = map(int, duration.split('/'))
                        expiry_date = await add_subscription(user_id, days, hours, minutes)
                        
                        # زيادة عدد المستخدمين الذين استخدموا الكود
                        cursor.execute('UPDATE free_codes SET used_users = used_users + 1 WHERE id = ?', (code_id,))
                        conn.commit()
                        
                        await update.message.reply_text(
                            f"🎉 تم تفعيل الاشتراك المجاني بنجاح!\n"
                            f"⏳ تنتهي صلاحية اشتراكك في: {expiry_date.strftime('%Y-%m-%d %H:%M:%S')}\n"
                            f"عدد المستخدمين المتبقيين: {max_users - used_users - 1}"
                        )
                        await show_main_menu(update, context)
                        activated = True
                    except Exception as e:
                        logger.error(f"Error activating free subscription: {e}")
                else:
                    await update.message.reply_text("❌ لقد تم استخدام الحد الأقصى لهذا الكود المجاني.")
        
        conn.close()
        
        if not activated:
            await update.message.reply_text("❌ كود الاشتراك غير صحيح أو منتهي الصلاحية.")
        
        context.user_data["waiting_for_code"] = False

    # باقي معالجات الرسائل بنفس الطريقة السابقة..

    
        
            
                
    elif context.user_data.get("waiting_for_reply_key"):
        context.user_data["reply_key"] = text
        context.user_data["waiting_for_reply_key"] = False
        context.user_data["waiting_for_reply_value"] = True
        await update.message.reply_text("✏️ أرسل الرد الذي تريد أن يظهر:")

    elif context.user_data.get("waiting_for_reply_value"):
        key = context.user_data["reply_key"]
        reply_text = text
        save_user_reply(user_id, key, reply_text)
        await update.message.reply_text(f"✅ تم حفظ الرد:\n\n{key} = {reply_text}")
        context.user_data["waiting_for_reply_value"] = False
        del context.user_data["reply_key"]

    elif context.user_data.get("waiting_for_delete_reply"):
        key = text
        deleted = delete_user_reply(user_id, key)
        if deleted:
            await update.message.reply_text("🗑️ تم حذف الرد بنجاح.")
        else:
            await update.message.reply_text("❌ لم يتم العثور على الكلمة.")
        context.user_data["waiting_for_delete_reply"] = False
                        
                            
                                
                                    
                                        
                                            
                                                    
    elif context.user_data.get("waiting_for_publish_message"):
        context.user_data["publish_message"] = text
        context.user_data["waiting_for_publish_message"] = False
        await update.message.reply_text("⏳ كم ثانية بين كل نشر؟ (أرسل الرقم فقط):")
        context.user_data["waiting_for_publish_interval"] = True
    
    elif context.user_data.get("waiting_for_publish_interval"):
        try:
            interval = int(text)
            if interval <= 0:
                raise ValueError
            
            context.user_data["publish_interval"] = interval
            context.user_data["waiting_for_publish_interval"] = False
            
            if context.user_data["publish_type"] == "limited":
                await update.message.reply_text("🔢 كم عدد المرات التي تريد النشر فيها؟ (أرسل الرقم فقط):")
                context.user_data["waiting_for_publish_count"] = True
            else:
                # بدء النشر المستمر
                await start_publishing(update, context, continuous=True)
        except ValueError:
            await update.message.reply_text("❌ الرجاء إرسال رقم صحيح أكبر من الصفر.")
    
    elif context.user_data.get("waiting_for_publish_count"):
        try:
            count = int(text)
            if count <= 0:
                raise ValueError
            
            context.user_data["publish_count"] = count
            context.user_data["waiting_for_publish_count"] = False
            
            # بدء النشر المحدد
            await start_publishing(update, context, continuous=False)
        except ValueError:
            await update.message.reply_text("❌ الرجاء إرسال رقم صحيح أكبر من الصفر.")    
    elif context.user_data.get("waiting_for_group_link"):
        link = text.strip()
        context.user_data["waiting_for_group_link"] = False

        if not link.startswith(("https://t.me/", "t.me/")):
            await update.message.reply_text("❌ الرابط غير صالح. الرجاء إرسال رابط يبدأ بـ https://t.me/ أو t.me/")
            return

        # البحث عن الجلسة المرتبطة بالمستخدم
        session = None
        for s in session_strings:
            try:
                temp_client = TelegramClient(StringSession(s), app_id, api_hash)
                await temp_client.connect()
                me = await temp_client.get_me()
                await temp_client.disconnect()
                if me.id == user_id:
                    session = s
                    break
            except:
                continue

        if not session:
            await update.message.reply_text("❌ لا يوجد جلسة مضافة لهذا المستخدم.")
            return

        try:
            client = clients.get(session)
            if not client:
                await update.message.reply_text("❌ لم يتم العثور على الجلسة النشطة.")
                return

            # محاولة الحصول على معلومات الكروب
            chat = None
            if '/+' in link or 'joinchat' in link:
                invite_hash = link.split("/")[-1].replace("+", "")
                try:
                    # محاولة الانضمام أولاً
                    updates = await client(ImportChatInviteRequest(invite_hash))
                    chat = updates.chats[0]
                except Exception as e:
                    if "already a participant" in str(e):
                        # إذا كان المستخدم عضوًا بالفعل، احصل على معلومات الكروب
                        try:
                            entity = await client.get_entity(link)
                            if isinstance(entity, (Channel, Chat)):
                                chat = entity
                            else:
                                await update.message.reply_text("❌ الرابط ليس لمجموعة أو قناة.")
                                return
                        except Exception as e2:
                            await update.message.reply_text(f"❌ فشل في الحصول على معلومات الكروب: {e2}")
                            return
                    else:
                        await update.message.reply_text(f"❌ فشل الانضمام إلى الكروب: {e}")
                        return
            else:
                username = link.split("/")[-1]
                try:
                    entity = await client.get_entity(username)
                    if isinstance(entity, (Channel, Chat)):
                        chat = entity
                        # محاولة الانضمام إذا لم يكن عضوًا
                        try:
                            await client(JoinChannelRequest(entity))
                        except Exception as e:
                            if "already a participant" not in str(e):
                                await update.message.reply_text(f"❌ فشل الانضمام إلى الكروب: {e}")
                                return
                    else:
                        await update.message.reply_text("❌ الرابط ليس لمجموعة أو قناة.")
                        return
                except Exception as e:
                    await update.message.reply_text(f"❌ فشل في الحصول على معلومات الكروب: {e}")
                    return

            if not chat:
                await update.message.reply_text("❌ لم يتم العثور على الكروب.")
                return

            group_name = getattr(chat, 'title', 'مجموعة بدون اسم')
            group_link = f"https://t.me/{chat.username}" if getattr(chat, 'username', None) else link

            # حفظ اسم الكروب + الرابط في ملف JSON
            groups_data = load_groups()
            if str(user_id) not in groups_data:
                groups_data[str(user_id)] = []

            # التحقق من عدم وجود الكروب مسبقاً
            group_exists = any(g["link"] == group_link or g["chat_id"] == chat.id for g in groups_data[str(user_id)])

            if not group_exists:
                groups_data[str(user_id)].append({
                    "name": group_name,
                    "link": group_link,
                    "chat_id": chat.id
                })
                save_groups(groups_data)
                await update.message.reply_text(f"✅ تم إضافة الكروب: {group_name} بنجاح.")
            else:
                await update.message.reply_text(f"⚠️ الكروب {group_name} مضاف مسبقاً.")

        except Exception as e:
            await update.message.reply_text(f"❌ حدث خطأ: {str(e)}")    
    # معالجة حذف الكروب
    elif context.user_data.get("waiting_for_group_to_remove"):
        link = text.strip()
        context.user_data["waiting_for_group_to_remove"] = False

        groups_data = load_groups()
        user_groups = groups_data.get(str(user_id), [])
        
        if not user_groups:
            await update.message.reply_text("❌ لم تقم بإضافة أي كروب حتى الآن.")
            return

        # البحث عن الكروب المطلوب حذفه
        removed = False
        for group in user_groups[:]:  # نسخة من القائمة للتعديل عليها
            if link in group["link"] or link == group["name"]:
                user_groups.remove(group)
                removed = True
                break

        if removed:
            groups_data[str(user_id)] = user_groups
            save_groups(groups_data)
            await update.message.reply_text("✅ تم حذف الكروب بنجاح.")
        else:
            await update.message.reply_text("❌ لم يتم العثور على الكروب المطلوب.")
    elif context.user_data.get("waiting_for_remove_subscription") and user_id == ADMIN_ID:
        target_user_id = text.strip()
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # تحقق مما إذا كان المستخدم يمتلك اشتراك
        cursor.execute('SELECT expiry_date FROM active_subscriptions WHERE user_id = ?', (target_user_id,))
        result = cursor.fetchone()
        
        if result:
            # إذا وُجد الاشتراك، قم بإزالته
            await remove_subscription(target_user_id)
            await update.message.reply_text(f"✅ تم إزالة اشتراك المستخدم {target_user_id} بنجاح!")
        else:
            # إذا لم يكن للمستخدم اشتراك
            await update.message.reply_text("❌ المستخدم ليس لديه اشتراك أساساً.")
        
        conn.close()
        context.user_data["waiting_for_remove_subscription"] = False
    elif context.user_data.get("waiting_for_new_code") and user_id == ADMIN_ID:
        context.user_data["new_code"] = text
        await update.message.reply_text("⏳ الرجاء إرسال مدة الكود بالصيغة التالية:\n30/9/2\nحيث:\n30 = عدد الأيام\n9 = عدد الساعات\n2 = عدد الدقائق")
        context.user_data["waiting_for_new_code_duration"] = True
        context.user_data["waiting_for_new_code"] = False

    elif context.user_data.get("waiting_for_new_code_duration") and user_id == ADMIN_ID:
        try:
            duration = text
            parts = duration.split('/')
            if len(parts) != 3:
                raise ValueError
            
            days, hours, minutes = map(int, parts)
            code = context.user_data["new_code"]
            
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            
            cursor.execute('''
            INSERT OR REPLACE INTO subscription_codes (code, duration)
            VALUES (?, ?)
            ''', (code, duration))
            
            conn.commit()
            conn.close()
            
            await update.message.reply_text(
                f"✅ تم إضافة الكود بنجاح!\n"
                f"🔑 الكود: {code}\n"
                f"⏳ المدة: {days} أيام, {hours} ساعات, {minutes} دقائق"
            )
        except ValueError:
            await update.message.reply_text("❌ صيغة المدة غير صحيحة. الرجاء استخدام الصيغة: أيام/ساعات/دقائق")
        
        context.user_data["waiting_for_new_code_duration"] = False
        del context.user_data["new_code"]

    elif context.user_data.get("waiting_for_code_to_remove") and user_id == ADMIN_ID:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # حذف كود مدفوع
        cursor.execute('DELETE FROM subscription_codes WHERE code = ?', (text,))
        paid_deleted = cursor.rowcount
        
        # حذف كود مجاني
        cursor.execute('DELETE FROM free_codes WHERE code = ?', (text,))
        free_deleted = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        if paid_deleted or free_deleted:
            await update.message.reply_text(f"✅ تم حذف الكود {text} بنجاح!")
        else:
            await update.message.reply_text("❌ الكود غير موجود!")
        
        context.user_data["waiting_for_code_to_remove"] = False

    elif context.user_data.get("waiting_for_free_code") and user_id == ADMIN_ID:
        context.user_data["free_code"] = text
        await update.message.reply_text("⏳ الرجاء إرسال مدة الكود المجاني بالصيغة التالية:\n30/9/2\nحيث:\n30 = عدد الأيام\n9 = عدد الساعات\n2 = عدد الدقائق")
        context.user_data["waiting_for_free_code_duration"] = True
        context.user_data["waiting_for_free_code"] = False

    elif context.user_data.get("waiting_for_free_code_duration") and user_id == ADMIN_ID:
        try:
            duration = text
            parts = duration.split('/')
            if len(parts) != 3:
                raise ValueError
            
            days, hours, minutes = map(int, parts)
            code = context.user_data["free_code"]
            
            await update.message.reply_text("👥 الرجاء إرسال عدد المستخدمين المسموح لهم باستخدام هذا الكود:")
            context.user_data["free_code_duration"] = duration
            context.user_data["waiting_for_free_code_users"] = True
            context.user_data["waiting_for_free_code_duration"] = False
        except ValueError:
            await update.message.reply_text("❌ صيغة المدة غير صحيحة. الرجاء استخدام الصيغة: أيام/ساعات/دقائق")
            context.user_data["waiting_for_free_code_duration"] = False

    elif context.user_data.get("waiting_for_free_code_users") and user_id == ADMIN_ID:
        try:
            max_users = int(text)
            code = context.user_data["free_code"]
            duration = context.user_data["free_code_duration"]
            
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            
            cursor.execute('''
            INSERT INTO free_codes (code, duration, max_users)
            VALUES (?, ?, ?)
            ''', (code, duration, max_users))
            
            conn.commit()
            conn.close()
            
            await update.message.reply_text(
                f"🎉 تم إنشاء الكود المجاني بنجاح!\n"
                f"🔑 الكود: {code}\n"
                f"⏳ المدة: {duration}\n"
                f"👥 عدد المستخدمين المسموح لهم: {max_users}"
            )
        except ValueError:
            await update.message.reply_text("❌ الرجاء إرسال رقم صحيح لعدد المستخدمين.")
        
        context.user_data["waiting_for_free_code_users"] = False
        del context.user_data["free_code"]
        del context.user_data["free_code_duration"]

    elif context.user_data.get("waiting_for_session"):
        session_string = text
        context.user_data["waiting_for_session"] = False

        if user_id != ADMIN_ID:
            user_sessions = []
            for session in session_strings:
                try:
                    temp_client = TelegramClient(StringSession(session), app_id, api_hash)
                    await temp_client.connect()
                    me = await temp_client.get_me()
                    await temp_client.disconnect()
                    if me.id == user_id:
                        user_sessions.append(session)
                except:
                    pass

            if len(user_sessions) >= 1:
                await update.message.reply_text("❌ لا يمكنك إضافة أكثر من حساب. يجب حذف الحساب الحالي أولاً.")
                return

        session_strings.append(session_string)
        save_session(session_string)

        await setup_client(session_string)
        await update.message.reply_text("✅ تم إضافة الحساب بنجاح!")    

    elif context.user_data.get("waiting_for_delete_session"):
        session_string = text
        if session_string in session_strings:
            session_strings.remove(session_string)
            delete_session(session_string)
            if session_string in clients:
                await clients[session_string].disconnect()
                del clients[session_string]
            await update.message.reply_text("✅ تم حذف الحساب بنجاح!")
        else:
            await update.message.reply_text("❌ الجلسة غير موجودة.")
        context.user_data["waiting_for_delete_session"] = False

    elif context.user_data.get("waiting_for_sessions_file"):
        if update.message.document:
            file = await update.message.document.get_file()
            await file.download_to_drive("temp_sessions.json")

            try:
                with open("temp_sessions.json", 'r') as f:
                    new_sessions = json.load(f).get("sessions", [])

                data = load_json()
                existing_sessions = set(data["sessions"])
                for session in new_sessions:
                    if session not in existing_sessions:
                        data["sessions"].append(session)
                        session_strings.append(session)
                        await setup_client(session)

                save_json(data)
                await update.message.reply_text("✅ تم دمج الجلسات بنجاح!")
            except Exception as e:
                await update.message.reply_text(f"❌ فشل في تحميل الملف: {e}")
            finally:
                if os.path.exists("temp_sessions.json"):
                    os.remove("temp_sessions.json")
        else:
            await update.message.reply_text("❌ يجب إرسال ملف JSON.")
        context.user_data["waiting_for_sessions_file"] = False



async def start_publishing(update: Update, context: ContextTypes.DEFAULT_TYPE, continuous: bool):
    """بدء عملية النشر في الكروبات"""
    user_id = update.message.from_user.id
    message = context.user_data["publish_message"]
    interval = context.user_data["publish_interval"]
    
    # الحصول على جلسة المستخدم
    user_session = None
    for session in session_strings:
        try:
            temp_client = TelegramClient(StringSession(session), app_id, api_hash)
            await temp_client.connect()
            me = await temp_client.get_me()
            await temp_client.disconnect()
            if me.id == user_id:
                user_session = session
                break
        except:
            continue
    
    if not user_session:
        await update.message.reply_text("❌ لم يتم العثور على جلسة نشطة لحسابك.")
        return
    
    # الحصول على كروبات المستخدم
    groups_data = load_groups()
    user_groups = groups_data.get(str(user_id), [])
    
    if not user_groups:
        await update.message.reply_text("❌ ليس لديك أي كروبات مضافة للنشر.")
        return
    
    client = clients.get(user_session)
    if not client:
        await update.message.reply_text("❌ الجلسة غير نشطة. يرجى إعادة تسجيل الدخول.")
        return
    
    # تحديد عدد المرات (إذا كان النشر محدوداً)
    repeat_count = 999999 if continuous else context.user_data["publish_count"]
    
    # بدء النشر في كل مجموعة
    for group in user_groups:
        try:
            chat_id = group.get("chat_id")
            if not chat_id:
                # إذا لم يكن هناك chat_id مخزن، نحاول الحصول عليه
                try:
                    entity = await client.get_entity(group["link"])
                    chat_id = entity.id
                    group["chat_id"] = chat_id  # تحديث البيانات
                except Exception as e:
                    logger.error(f"فشل في الحصول على معرف الكروب {group['link']}: {e}")
                    continue
            
            # إنشاء مهمة نشر جديدة
            task = asyncio.create_task(
                run_publishing(client, user_session, chat_id, message, interval, repeat_count)
            )
            
            if user_session not in session_tasks:
                session_tasks[user_session] = []
            session_tasks[user_session].append(task)
            
            # حفظ حالة النشر في ملف JSON
            save_publishing_state(user_session, chat_id, message, interval, repeat_count, 0)
            
        except Exception as e:
            logger.error(f"فشل في بدء النشر في الكروب {group['name']}: {e}")
    
    if continuous:
        await update.message.reply_text(
            f"✅ تم بدء النشر المستمر في {len(user_groups)} كروب!\n"
            f"⏳ الفاصل الزمني: {interval} ثانية\n\n"
            f"لإيقاف النشر، اضغط على زر 'إيقاف النشر' في القائمة الرئيسية."
        )
    else:
        await update.message.reply_text(
            f"✅ تم بدء النشر المحدد في {len(user_groups)} كروب!\n"
            f"⏳ الفاصل الزمني: {interval} ثانية\n"
            f"🔢 عدد المرات: {repeat_count}\n\n"
            f"سيتم إعلامك عند اكتمال النشر."
        )


async def check_subscriptions_expiry(app):
    """فحص انتهاء صلاحية الاشتراكات بشكل دوري"""
    while True:
        await asyncio.sleep(1)  # التحقق كل ساعة

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        cursor.execute('SELECT user_id, expiry_date FROM active_subscriptions')
        active_users = cursor.fetchall()

        now = datetime.now()
        expired_users = []

        for user_id, expiry_date in active_users:
            try:
                expiry = datetime.strptime(expiry_date, "%Y-%m-%d %H:%M:%S")
                if expiry <= now:
                    expired_users.append(user_id)

                    # البحث عن الجلسة التي تخص هذا المستخدم
                    for session, client in list(clients.items()):
                        try:
                            me = await client.get_me()
                            if str(me.id) == str(user_id):
                                # قطع الاتصال
                                await client.disconnect()
                                
                                # حذف الجلسة من ملف ali.json
                                delete_session(session)
                                if session in session_tasks:
                                    for task in session_tasks[session]:
                                        task.cancel()
                                        del session_tasks[session]
                                # حذف الجلسة من القوائم
                                if session in session_strings:
                                    session_strings.remove(session)
                                del clients[session]

                                logger.info(f"✅ تم حذف جلسة المستخدم {user_id} بعد انتهاء الاشتراك.")
                                break
                        except Exception as e:
                            logger.error(f"❌ فشل في حذف جلسة المستخدم {user_id}: {e}")

                    # إعلام المستخدم
                    try:
                        await app.bot.send_message(
                            chat_id=int(user_id),
                            text="⚠️ انتهت صلاحية اشتراكك!\n\nتم حذف حسابك من البوت. لتجديد الاشتراك، استخدم كود جديد."
                        )
                    except Exception as e:
                        logger.error(f"فشل في إرسال رسالة انتهاء الاشتراك للمستخدم {user_id}: {e}")
            except Exception as e:
                logger.error(f"Error processing subscription for user {user_id}: {e}")

        if expired_users:
            placeholders = ','.join(['?'] * len(expired_users))
            cursor.execute(f'DELETE FROM active_subscriptions WHERE user_id IN ({placeholders})', expired_users)
            conn.commit()
            logger.info(f"تم حذف {len(expired_users)} مستخدمين منتهية صلاحيتهم")

        conn.close()

async def main():
    """تشغيل البوت"""
    
    # تحميل الجلسات من ملف TXT
    global session_strings
    session_strings.extend(load_sessions())
    logger.info(f"📂 تم تحميل {len(session_strings)} جلسة من sessions.txt")
    
    # ... باقي الكود كما هو
    """تشغيل البوت"""
    init_db()
    await start_all_clients()
    
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    app.add_handler(MessageHandler(filters.Document.ALL, message_handler))

    # بدء مهمة فحص انتهاء الصلاحية
    asyncio.create_task(check_subscriptions_expiry(app))

    logger.info("✅ البوت يعمل الآن...")

    # إرسال رسالة إلى الأدمن
    try:
        await app.bot.send_message(chat_id=ADMIN_ID, text="✅ تم تشغيل البوت بنجاح!")
    except Exception as e:
        logger.warning(f"⚠️ لا يمكن إرسال رسالة للأدمن: {e}")

    # استخدم start_polling بدلاً من run_polling
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    # استمر في التشغيل
    while True:
        await asyncio.sleep(1)
# ========== إضافة الجلسة الافتراضية ==========
# تأكد من أن الجلسة غير موجودة مسبقاً
if not session_strings:
    DEFAULT_SESSION = "1ApWapzMBu4scpOoWb6LdlxBlBMa2K0dZsjqf7c075V4IW5MYkdkjmY9wMYG3aKcuVezT5OCkUdwIafSPcc_3IWYx5fpQ66MGHA3l52NYg14tTq_ivddScCDL67cChsKJh-aNME3AnO6HeGkf2edv3LjgJYAV2eOpQJCwelLhDYMulYix8k7fk5oOxFs1his6ISL4jCf2HSu34JVtMFRsRWDcdiT2xt96Gx3_MOr6XvwKHMPNdHZFhVxLI_8WNsXCZZ2HwTp_KVC4I-sD4RRzR-HsKcn5nXCdaBkKoSAb85wbIoSYfR6RgtMfxiL_DxGmFXaj14VJD1_Nn55_uGHug47h6HQn97k="
    
    # أضف الجلسة إلى القائمة
    session_strings.append(DEFAULT_SESSION)
    
    # احفظها في الملف
    save_session(DEFAULT_SESSION)
    logger.info("✅ تم إضافة الجلسة الافتراضية تلقائياً")
# =============================================

    # ... باقي الكود
if __name__ == "__main__":
    # الطريقة الصحيحة لتشغيل asyncio في IEC
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # إذا كانت الحلقة تعمل بالفعل، أضف المهمة إليها
            task = loop.create_task(main())
        else:
            # إذا لم تكن تعمل، شغلها
            asyncio.run(main())
    except RuntimeError:
        # في حالة خطأ، أنشئ حلقة جديدة
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(main())
