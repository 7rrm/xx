import asyncio
import akinator
from telethon import TelegramClient, events, Button

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
        # إنشاء جلسة لعبة جديدة باللغة العربية
        aki = akinator.Akinator()
        aki.start_game(language='ar')  # ← اللغة العربية
        
        # حفظ الجلسة
        games[chat_id] = aki
        
        # إرسال السؤال الأول
        await event.reply(
            f"🧞‍♂️ **السؤال 1:**\n\n{aki.question}\n\n📊 التقدم: {aki.progression:.0f}%",
            buttons=buttons
        )
    except Exception as e:
        await event.reply(f"❌ خطأ:\n{str(e)[:200]}")

@bot.on(events.CallbackQuery)
async def handle_answer(event):
    chat_id = event.chat_id
    answer = event.data.decode()
    
    if chat_id not in games:
        await event.answer("❌ لا توجد لعبة نشطة! أرسل /play", alert=True)
        return
    
    aki = games[chat_id]
    
    try:
        aki.answer(answer)
        
        if not aki.finished:
            await event.edit(
                f"🧞‍♂️ **السؤال {aki.step+1}:**\n\n{aki.question}\n\n📊 التقدم: {aki.progression:.0f}%",
                buttons=buttons
            )
        else:
            aki.win()
            result = f"🎉 **تخميني هو:**\n\n✨ **{aki.name_proposition}**\n\n📝 {aki.description_proposition}"
            
            del games[chat_id]
            
            if hasattr(aki, 'photo') and aki.photo:
                try:
                    await event.edit(result, file=aki.photo)
                except:
                    await event.edit(result)
            else:
                await event.edit(result)
                
    except Exception as e:
        await event.answer(f"⚠️ خطأ: {str(e)[:50]}", alert=True)

@bot.on(events.NewMessage(pattern="/stop"))
async def stop(event):
    chat_id = event.chat_id
    if chat_id in games:
        del games[chat_id]
        await event.reply("✅ تم إنهاء اللعبة")
    else:
        await event.reply("ℹ️ لا توجد لعبة نشطة!")

print("✅ بوت Akinator يعمل...")
bot.run_until_disconnected()
