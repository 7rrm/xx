import asyncio
import akinator
from telethon import TelegramClient, events, Button

# ========== بياناتك ==========
API_ID = 23032698
API_HASH = "99ad65a5fcd38203621cb20acd2aaba5"
BOT_TOKEN = "7068624335:AAHagvK1fby2WpnulcN1akudmRTfhIJ42-4"
# ===========================

bot = TelegramClient("bot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)
games = {}

buttons = [
    [Button.inline("✅ نعم", b"0"), Button.inline("❌ لا", b"1")],
    [Button.inline("❓ لا أعرف", b"2"), Button.inline("🤔 ربما", b"3")],
    [Button.inline("😕 الأغلب لا", b"4")]
]

@bot.on(events.NewMessage(pattern="/start"))
async def start(e):
    await e.reply("🎮 بوت Akinator\nأرسل /play لبدء اللعبة")

@bot.on(events.NewMessage(pattern="/play"))
async def play(e):
    cid = e.chat_id
    try:
        aki = akinator.Akinator()
        q = aki.start_game(language='ar')
        games[cid] = aki
        await e.reply(f"🧞‍♂️ {q}\n📊 {aki.progression}%", buttons=buttons)
    except Exception as ex:
        await e.reply(f"خطأ: {ex}")

@bot.on(events.CallbackQuery)
async def ans(e):
    cid = e.chat_id
    if cid not in games:
        await e.answer("انتهت! /play", alert=True)
        return
    aki = games[cid]
    try:
        aki.answer(int(e.data.decode()))
        if aki.progression < 80:
            await e.edit(f"🧞‍♂️ {aki.question}\n📊 {aki.progression}%", buttons=buttons)
        else:
            aki.win()
            g = aki.first_guess
            txt = f"🎉 {g['name']}\n{g['description']}"
            await e.edit(txt)
            del games[cid]
    except Exception as ex:
        await e.answer(f"خطأ: {ex}", alert=True)

print("✅ يعمل...")
bot.run_until_disconnected()
