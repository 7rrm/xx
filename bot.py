import asyncio
import akinator
from telethon import TelegramClient, events, Button

# ========== بياناتك ==========
API_ID = 21623560
API_HASH = "8c448c687d43262833a0ab100255fb43"
BOT_TOKEN = "7145022358:AAHlgguv9tTBkQTwar57Swkb5xiKycptxR8"
# ===========================

bot = TelegramClient("aki_bot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# تخزين جلسات اللعب
games = {}

# أزرار الإجابة (بأرقام الإجابات التي تفهمها المكتبة)
buttons = [
    [
        Button.inline("✅ نعم", b"0"),
        Button.inline("❌ لا", b"1"),
        Button.inline("❓ لا أعلم", b"2")
    ],
    [
        Button.inline("🤔 من المحتمل", b"3"),
        Button.inline("😕 على الأغلب لا", b"4")
    ]
]

@bot.on(events.NewMessage(pattern="/start"))
async def start(event):
    await event.reply(
        "🧞‍♂️ **مرحباً! أنا بوت Akinator**\n\n"
        "✨ فكر بشخصية (حقيقية أو خيالية)\n"
        "📝 سأطرح عليك أسئلة لأحاول تخمينها\n\n"
        "🎮 **أرسل /play لبدء اللعبة**"
    )

@bot.on(events.NewMessage(pattern="/play"))
async def play(event):
    chat_id = event.chat_id
    
    try:
        # بدء لعبة جديدة مع سيرفر akinator الحقيقي
        aki = akinator.Akinator()
        question = aki.start_game()
        games[chat_id] = aki
        
        await event.reply(
            f"🧞‍♂️ **السؤال 1:**\n\n{question}\n\n📊 التقدم: {aki.progression}%",
            buttons=buttons
        )
    except Exception as e:
        await event.reply(f"❌ خطأ في بدء اللعبة:\n{str(e)[:200]}")

@bot.on(events.CallbackQuery)
async def handle_answer(event):
    chat_id = event.chat_id
    answer = event.data.decode()  # 0,1,2,3,4
    
    if chat_id not in games:
        await event.answer("❌ لا توجد لعبة نشطة! أرسل /play", alert=True)
        return
    
    aki = games[chat_id]
    
    try:
        # إرسال الإجابة إلى akinator
        question = aki.answer(answer)
        
        # إذا وصل التخمين إلى 80% أو أكثر
        if aki.progression >= 80:
            aki.win()
            guess = aki.first_guess
            
            result = f"🎉 **توقعتي هي:**\n\n✨ **{guess['name']}**\n\n📝 {guess['description']}"
            
            # محاولة إرسال الصورة
            if guess.get('absolute_picture_path'):
                try:
                    await event.edit(result, file=guess['absolute_picture_path'])
                except:
                    await event.edit(result)
            else:
                await event.edit(result)
            
            # حذف الجلسة
            del games[chat_id]
        else:
            # عرض السؤال التالي
            await event.edit(
                f"🧞‍♂️ **السؤال {aki.step + 1}:**\n\n{question}\n\n📊 التقدم: {aki.progression}%",
                buttons=buttons
            )
    except Exception as e:
        await event.answer(f"⚠️ خطأ: {str(e)[:50]}", alert=True)

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
