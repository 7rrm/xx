import asyncio
import akinator
from telethon import TelegramClient, events, Button
import os

# ========== بياناتك ==========
API_ID = 21623560
API_HASH = "8c448c687d43262833a0ab100255fb43"
BOT_TOKEN = "7145022358:AAHlgguv9tTBkQTwar57Swkb5xiKycptxR8"
# ===========================

bot = TelegramClient("aki_bot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)
games = {}

# أزرار الإجابة - نفس تنسيق المكتبة (y/n/idk/p/pn)
buttons = [
    [Button.inline("✅ نعم", b"y"), Button.inline("❌ لا", b"n"), Button.inline("❓ لا أعرف", b"idk")],
    [Button.inline("🤔 ربما", b"p"), Button.inline("😕 الأغلب لا", b"pn")]
]

# قاموس التحويل للأزرار التي تحتاج أرقاماً
answer_map = {
    "y": "y",
    "n": "n", 
    "idk": "idk",
    "p": "p",
    "pn": "pn"
}

@bot.on(events.NewMessage(pattern="/start"))
async def start(event):
    await event.reply(
        "🧞‍♂️ **مرحباً! أنا بوت أكيناتور**\n\n"
        "✨ فكر في شخصية (حقيقية أو خيالية)\n"
        "📝 سأطرح أسئلة لأحاول تخمينها\n\n"
        "🎮 **أرسل /play لبدء اللعبة**"
    )

@bot.on(events.NewMessage(pattern="/play"))
async def play(event):
    chat_id = event.chat_id
    try:
        # إنشاء جلسة لعبة جديدة
        aki = akinator.Akinator()
        
        # بدء اللعبة
        aki.start_game()
        
        # الحصول على السؤال الأول - المكتبة تخزنه في aki.question
        first_question = aki.question
        
        # حفظ الجلسة
        games[chat_id] = aki
        
        # إرسال السؤال
        await event.reply(
            f"🧞‍♂️ **السؤال 1:**\n\n{first_question}\n\n📊 التقدم: {aki.progression:.0f}%",
            buttons=buttons
        )
    except Exception as e:
        await event.reply(f"❌ خطأ:\n{str(e)[:200]}")
        # طباعة الخطأ كاملاً للتشخيص (في سجل الخادم)
        print(f"Full error: {e}")

@bot.on(events.CallbackQuery)
async def handle_answer(event):
    chat_id = event.chat_id
    answer = event.data.decode()
    
    # التحقق من وجود لعبة نشطة
    if chat_id not in games:
        await event.answer("❌ لا توجد لعبة نشطة! أرسل /play", alert=True)
        return
    
    aki = games[chat_id]
    
    try:
        # إرسال الإجابة بأمان
        aki.answer(answer)
        
        # التحقق من أن اللعبة لم تنتهِ بعد
        if not aki.finished:
            # عرض السؤال التالي
            next_question = aki.question
            await event.edit(
                f"🧞‍♂️ **السؤال {aki.step+1}:**\n\n{next_question}\n\n📊 التقدم: {aki.progression:.0f}%",
                buttons=buttons
            )
        else:
            # الحصول على التخمين النهائي
            aki.win()
            name = aki.name_proposition
            description = aki.description_proposition
            photo = aki.photo if hasattr(aki, 'photo') else None
            
            result = f"🎉 **تخميني هو:**\n\n✨ **{name}**\n\n📝 {description}"
            
            # حذف الجلسة
            del games[chat_id]
            
            # إرسال النتيجة (مع الصورة إن وجدت)
            if photo:
                try:
                    await event.edit(result, file=photo)
                except:
                    await event.edit(result)
            else:
                await event.edit(result)
                
    except Exception as e:
        await event.answer(f"⚠️ خطأ: {str(e)[:50]}", alert=True)
        print(f"Error in callback: {e}")

@bot.on(events.NewMessage(pattern="/stop"))
async def stop(event):
    chat_id = event.chat_id
    if chat_id in games:
        del games[chat_id]
        await event.reply("✅ تم إنهاء اللعبة. أرسل /play للبدء من جديد")
    else:
        await event.reply("ℹ️ لا توجد لعبة نشطة!")

print("✅ بوت Akinator يعمل...")
bot.run_until_disconnected()
