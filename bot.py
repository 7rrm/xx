import asyncio
import aiohttp
import re
import json
import time
from telethon import TelegramClient, events, Button

# ========== بياناتك الجديدة ==========
API_ID = 23032698
API_HASH = "99ad65a5fcd38203621cb20acd2aaba5"
BOT_TOKEN = "7068624335:AAHagvK1fby2WpnulcN1akudmRTfhIJ42-4"
# ===================================

bot = TelegramClient("aki_bot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# تخزين جلسات اللعب
games_data = {}

# أزرار الإجابة
buttons = [
    [Button.inline("✅ نعم", b"0")],
    [Button.inline("❌ لا", b"1")],
    [Button.inline("❓ لا أعرف", b"2")],
    [Button.inline("🤔 ربما", b"3")],
    [Button.inline("😕 الأغلب لا", b"4")]
]

# خيارات الإجابة
answers = ["yes", "no", "idk", "probably", "probably_not"]

async def start_new_game():
    """بدء لعبة جديدة والحصول على السؤال الأول"""
    
    timestamp = int(time.time() * 1000)
    
    async with aiohttp.ClientSession() as session:
        # الحصول على معلومات الجلسة
        async with session.get("https://ar.akinator.com/game") as resp:
            html = await resp.text()
            
        # استخراج uid و frontaddr
        uid_match = re.search(r"var uid_ext_session = '([^']+)'", html)
        frontaddr_match = re.search(r"var frontaddr = '([^']+)'", html)
        
        if not uid_match or not frontaddr_match:
            raise Exception("فشل في الحصول على معلومات الجلسة")
        
        uid = uid_match.group(1)
        frontaddr = frontaddr_match.group(1)
        
        # الحصول على سيرفر اللعبة
        server_match = re.search(r'"urlWs":"(https://[^"]+)"', html)
        if not server_match:
            raise Exception("فشل في الحصول على السيرفر")
        
        server = server_match.group(1)
        
        # بدء الجلسة
        url = f"https://ar.akinator.com/new_session?callback=jQuery&urlApiWs={server}&partner=1&childMod=false&player=website-desktop&uid_ext_session={uid}&frontaddr={frontaddr}&constraint=ETAT<>'AV'&soft_constraint=&question_filter="
        
        async with session.get(url) as resp:
            text = await resp.text()
            
        # استخراج JSON
        json_text = text[text.index('(')+1:text.rindex(')')]
        data = json.loads(json_text)
        
        if data.get("completion") != "OK":
            raise Exception("فشل في بدء اللعبة")
        
        params = data["parameters"]
        ident = params["identification"]
        step_info = params["step_information"]
        
        return {
            "session": ident["session"],
            "signature": ident["signature"],
            "uid": uid,
            "frontaddr": frontaddr,
            "server": server,
            "question": step_info["question"],
            "progression": step_info["progression"],
            "step": step_info["step"]
        }

async def send_answer(session_data, answer_id):
    """إرسال إجابة والحصول على السؤال التالي"""
    
    timestamp = int(time.time() * 1000)
    
    async with aiohttp.ClientSession() as session:
        url = f"https://ar.akinator.com/answer_api?callback=jQuery&urlApiWs={session_data['server']}&childMod=false&session={session_data['session']}&signature={session_data['signature']}&step={session_data['step']}&answer={answer_id}&frontaddr={session_data['frontaddr']}&question_filter="
        
        async with session.get(url) as resp:
            text = await resp.text()
        
        json_text = text[text.index('(')+1:text.rindex(')')]
        data = json.loads(json_text)
        
        if data.get("completion") != "OK":
            raise Exception(f"خطأ في الإجابة: {data.get('completion')}")
        
        params = data["parameters"]
        
        return {
            "question": params["question"],
            "progression": params["progression"],
            "step": params["step"]
        }

async def get_winner(session_data):
    """الحصول على التخمين النهائي"""
    
    timestamp = int(time.time() * 1000)
    
    async with aiohttp.ClientSession() as session:
        url = f"https://ar.akinator.com/list?callback=jQuery&childMod=false&session={session_data['session']}&signature={session_data['signature']}&step={session_data['step']}"
        
        async with session.get(url) as resp:
            text = await resp.text()
        
        json_text = text[text.index('(')+1:text.rindex(')')]
        data = json.loads(json_text)
        
        if data.get("completion") != "OK":
            raise Exception("فشل في الحصول على التخمين")
        
        elements = data["parameters"]["elements"]
        if elements:
            return elements[0]["element"]
        return None

@bot.on(events.NewMessage(pattern="/start"))
async def start(event):
    await event.reply(
        "🧞‍♂️ **مرحباً! أنا بوت أكيناتور**\n\n"
        "✨ فكر في شخصية (حقيقية أو خيالية)\n"
        "📝 سأطرح عليك أسئلة لأحاول تخمينها\n\n"
        "🎮 **أرسل /play لبدء اللعبة**"
    )

@bot.on(events.NewMessage(pattern="/play"))
async def play(event):
    chat_id = event.chat_id
    
    # حذف أي لعبة سابقة
    if chat_id in games_data:
        del games_data[chat_id]
    
    msg = await event.reply("🧞‍♂️ جاري التحضير...")
    
    try:
        game = await start_new_game()
        games_data[chat_id] = game
        
        await msg.edit(
            f"🧞‍♂️ **السؤال 1:**\n\n{game['question']}\n\n📊 التقدم: {game['progression']}%",
            buttons=buttons
        )
    except Exception as e:
        await msg.edit(f"❌ خطأ: {str(e)[:200]}")

@bot.on(events.CallbackQuery)
async def handle_answer(event):
    chat_id = event.chat_id
    answer_id = int(event.data.decode())
    
    if chat_id not in games_data:
        await event.answer("❌ لا توجد لعبة نشطة! أرسل /play", alert=True)
        return
    
    game = games_data[chat_id]
    
    try:
        result = await send_answer(game, answer_id)
        
        # تحديث البيانات
        game["question"] = result["question"]
        game["progression"] = result["progression"]
        game["step"] = result["step"]
        games_data[chat_id] = game
        
        # التحقق من التخمين
        if float(result["progression"]) >= 80:
            winner = await get_winner(game)
            
            if winner:
                text = f"🎉 **تخميني هو:**\n\n✨ **{winner['name']}**\n\n📝 {winner['description']}"
                
                if winner.get('absolute_picture_path'):
                    try:
                        await event.edit(text, file=winner['absolute_picture_path'])
                    except:
                        await event.edit(text)
                else:
                    await event.edit(text)
            else:
                await event.edit("❓ لم أستطع تخمين شخصيتك! ابدأ من جديد بـ /play")
            
            # حذف الجلسة
            del games_data[chat_id]
        else:
            # عرض السؤال التالي
            await event.edit(
                f"🧞‍♂️ **السؤال {int(result['step']) + 1}:**\n\n{result['question']}\n\n📊 التقدم: {result['progression']}%",
                buttons=buttons
            )
            
    except Exception as e:
        await event.answer(f"⚠️ خطأ: {str(e)[:100]}", alert=True)
        if chat_id in games_data:
            del games_data[chat_id]

@bot.on(events.NewMessage(pattern="/stop"))
async def stop(event):
    chat_id = event.chat_id
    if chat_id in games_data:
        del games_data[chat_id]
        await event.reply("✅ تم إنهاء اللعبة. أرسل /play للبدء من جديد")
    else:
        await event.reply("ℹ️ لا توجد لعبة نشطة!")

print("✅ بوت Akinator يعمل...")
bot.run_until_disconnected()
