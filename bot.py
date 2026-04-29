import asyncio
import akinator
from telethon import TelegramClient, events, Button

# ========== بياناتك ==========
API_ID = 23032698
API_HASH = "99ad65a5fcd38203621cb20acd2aaba5"
BOT_TOKEN = "7068624335:AAHagvK1fby2WpnulcN1akudmRTfhIJ42-4"
# ===========================

bot = TelegramClient("aki_bot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)
games = {}

buttons = [
    [Button.inline("✅ نعم", b"yes"), Button.inline("❌ لا", b"no")],
    [Button.inline("❓ لا أعرف", b"idk"), Button.inline("🤔 ربما", b"probably")],
    [Button.inline("😕 الأغلب لا", b"probably_not")]
]

@bot.on(events.NewMessage(pattern="/start"))
async def start(event):
    await event.reply(
        "🧞‍♂️ **بوت أكيناتور**\n\n"
        "✨ فكر في شخصية\n"
        "🎮 أرسل /play لبدء اللعبة"
    )

@bot.on(events.NewMessage(pattern="/play"))
async def play(event):
    chat_id = event.chat_id
    if chat_id in games:
        del games[chat_id]
    
    try:
        # 1. إنشاء كائن العميل
        aki = akinator.Akinator()
        
        # 2. بدء اللعبة (هذا لا يُرجع قيمة، بل يهيئ الكائن)
        aki.start_game(language='ar', child_mode=False)
        
        # 3. السؤال موجود الآن في aki.question
        games[chat_id] = aki
        
        await event.reply(
            f"🧞‍♂️ **السؤال 1:**\n\n{aki.question}\n\n📊 التقدم: {aki.progression}%",
            buttons=buttons
        )
    except Exception as e:
        await event.reply(f"❌ خطأ: {str(e)}")

@bot.on(events.CallbackQuery)
async def on_button_click(event):
    chat_id = event.chat_id
    user_answer = event.data.decode()  # yes, no, idk, probably, probably_not
    
    if chat_id not in games:
        await event.answer("❌ لا توجد لعبة! أرسل /play", alert=True)
        return
    
    aki = games[chat_id]
    
    try:
        # إرسال الإجابة إلى المكتبة
        aki.answer(user_answer)
        
        # التحقق من التخمين
        if aki.progression < 80:
            # عرض السؤال التالي
            await event.edit(
                f"🧞‍♂️ **السؤال {aki.step + 1}:**\n\n{aki.question}\n\n📊 التقدم: {aki.progression}%",
                buttons=buttons
            )
        else:
            # الوصول إلى تخمين
            aki.win()  # هذا يملأ aki.name_proposition وغيره
            name = aki.name_proposition
            description = aki.description_proposition
            
            result = f"🎉 **تخميني هو:**\n\n✨ **{name}**\n\n📝 {description}"
            
            if hasattr(aki, 'photo') and aki.photo:
                try:
                    await event.edit(result, file=aki.photo)
                except:
                    await event.edit(result)
            else:
                await event.edit(result)
            
            del games[chat_id]
    
    except akinator.InvalidChoiceError:
        await event.answer("⚠️ إجابة غير صالحة!", alert=True)
    except Exception as e:
        await event.answer(f"⚠️ خطأ: {str(e)[:50]}", alert=True)
        if chat_id in games:
            del games[chat_id]

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
