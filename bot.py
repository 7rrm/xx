import asyncio
from telethon import TelegramClient, events, Button

# استيراد المكتبة الجديدة
from akinator_python import Akinator

# ========== بياناتك ==========
API_ID = 21623560
API_HASH = "8c448c687d43262833a0ab100255fb43"
BOT_TOKEN = "7145022358:AAHlgguv9tTBkQTwar57Swkb5xiKycptxR8"
# ===========================

bot = TelegramClient("aki_bot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# قاموس لتخزين جلسات اللعب لكل مستخدم
games = {}

# أزرار الإجابة (الأرقام تتوافق مع خيارات المكتبة)
buttons = [
    [Button.inline("✅ نعم", b"y"), Button.inline("❌ لا", b"n"), Button.inline("❓ لا أعلم", b"idk")],
    [Button.inline("🤔 من المحتمل", b"p"), Button.inline("😕 على الأغلب لا", b"pn")]
]

@bot.on(events.NewMessage(pattern="/start"))
async def start(event):
    await event.reply(
        "🧞‍♂️ **مرحباً! أنا بوت Akinator**\n\n"
        "✨ فكر في شخصية (حقيقية أو خيالية)\n"
        "📝 سأطرح عليك أسئلة لأحاول تخمينها\n\n"
        "🎮 **أرسل /play لبدء اللعبة**"
    )

@bot.on(events.NewMessage(pattern="/play"))
async def play(event):
    chat_id = event.chat_id
    try:
        # 1. إنشاء كائن اللعبة الجديد
        aki = Akinator(lang="ar") # تحديد اللغة العربية
        # 2. بدء اللعبة. .start_game() سترجع السؤال الأول بشكل نصي تلقائيًا
        first_question = aki.start_game() 
        
        # 3. حفظ الجلسة
        games[chat_id] = aki
        
        # 4. إرسال السؤال الأول للمستخدم
        await event.reply(
            f"🧞‍♂️ **السؤال 1:**\n\n{first_question}\n\n📊 التقدم: {aki.progression}%",
            buttons=buttons
        )
    except Exception as e:
        await event.reply(f"❌ خطأ في بدء اللعبة:\n{str(e)}")

@bot.on(events.CallbackQuery)
async def handle_answer(event):
    chat_id = event.chat_id
    user_answer = event.data.decode() # y, n, idk, p, pn
    
    if chat_id not in games:
        await event.answer("❌ لا توجد لعبة نشطة! أرسل /play", alert=True)
        return
    
    aki = games[chat_id] # استرداد كائن اللعبة من الذاكرة
    
    try:
        # إرسال الإجابة إلى مكتبة اللعبة
        # .post_answer() ستقوم بتحديث حالة اللعبة داخليًا
        aki.post_answer(user_answer)
        
        # التحقق مما إذا كان أكيناتور جاهزًا للتخمين
        if aki.answer_id:
            # هذا يعني أن أكيناتور لديه تخمين!
            name = aki.name
            description = aki.description
            
            result_text = f"🎉 **تخميني هو:**\n\n✨ **{name}**\n\n📝 {description}"
            
            # حذف الجلسة لأن اللعبة انتهت
            del games[chat_id]
            
            # إرسال النتيجة للمستخدم
            await event.edit(result_text)
            
        else:
            # إذا لم يكن هناك تخمين، نعرض السؤال التالي
            next_question = aki.question # الحصول على السؤال الجديد من المكتبة
            
            await event.edit(
                f"🧞‍♂️ **السؤال {aki.step}:**\n\n{next_question}\n\n📊 التقدم: {aki.progression}%",
                buttons=buttons
            )
            
    except Exception as e:
        await event.answer(f"⚠️ حدث خطأ: {str(e)[:100]}", alert=True)
        # في حالة الخطأ، ننظف الجلسة
        if chat_id in games:
            del games[chat_id]

@bot.on(events.NewMessage(pattern="/stop"))
async def stop(event):
    chat_id = event.chat_id
    if chat_id in games:
        del games[chat_id]
        await event.reply("✅ تم إنهاء اللعبة. أرسل /play للبدء من جديد")
    else:
        await event.reply("ℹ️ لا توجد لعبة نشطة!")

print("✅ بوت Akinator يعمل... انتظر الأوامر")
bot.run_until_disconnected()
