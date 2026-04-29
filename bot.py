import asyncio
import aiohttp
import json
import time
import random
from telethon import TelegramClient, events, Button

# ========== بياناتك ==========
API_ID = 23032698
API_HASH = "99ad65a5fcd38203621cb20acd2aaba5"
BOT_TOKEN = "7068624335:AAHagvK1fby2WpnulcN1akudmRTfhIJ42-4"
# ===========================

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

# خوادم بديلة
SERVERS = [
    "https://srv3.akinator.com:9279/ws",
    "https://srv4.akinator.com:9369/ws", 
    "https://srv5.akinator.com:9397/ws",
    "https://srv6.akinator.com:9398/ws",
    "https://srv7.akinator.com:9399/ws",
    "https://srv8.akinator.com:9400/ws",
    "https://srv9.akinator.com:9401/ws",
]

async def start_new_game():
    """بدء لعبة جديدة باستخدام API مباشر"""
    
    # استخدام خادم عشوائي
    server = random.choice(SERVERS)
    
    # إنشاء معرف جلسة عشوائي
    session_id = random.randint(1000000, 9999999)
    signature = random.randint(100000, 999999)
    
    async with aiohttp.ClientSession() as session:
        # رابط بدء اللعبة
        url = f"https://ar.akinator.com/new_session?callback=callback&urlApiWs={server}&partner=1&childMod=false&player=website-desktop&uid_ext_session={session_id}&frontaddr=&constraint=ETAT<>'AV'&soft_constraint=&question_filter="
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "*/*",
            "Referer": "https://ar.akinator.com/",
            "X-Requested-With": "XMLHttpRequest"
        }
        
        try:
            async with session.get(url, headers=headers) as resp:
                text = await resp.text()
                
            # استخراج JSON من callback
            import re
            json_match = re.search(r'callback\((.*)\)', text)
            if json_match:
                json_text = json_match.group(1)
                data = json.loads(json_text)
            else:
                # محاولة مباشرة
                data = json.loads(text)
            
            if data.get("completion") == "KO":
                raise Exception("الخادم مشغول، حاول مرة أخرى")
            
            if data.get("completion") != "OK":
                raise Exception(f"خطأ: {data.get('completion')}")
            
            params = data["parameters"]
            ident = params["identification"]
            step_info = params["step_information"]
            
            return {
                "session": ident["session"],
                "signature": ident["signature"],
                "server": server,
                "question": step_info["question"],
                "progression": step_info["progression"],
                "step": step_info["step"]
            }
            
        except Exception as e:
            raise Exception(f"فشل الاتصال: {str(e)}")

async def send_answer(session_data, answer_id):
    """إرسال إجابة"""
    
    async with aiohttp.ClientSession() as session:
        url = f"https://ar.akinator.com/answer_api?callback=callback&urlApiWs={session_data['server']}&childMod=false&session={session_data['session']}&signature={session_data['signature']}&step={session_data['step']}&answer={answer_id}&frontaddr=&question_filter="
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "*/*",
            "Referer": "https://ar.akinator.com/",
            "X-Requested-With": "XMLHttpRequest"
        }
        
        async with session.get(url, headers=headers) as resp:
            text = await resp.text()
        
        import re
        json_match = re.search(r'callback\((.*)\)', text)
        if json_match:
            json_text = json_match.group(1)
            data = json.loads(json_text)
        else:
            data = json.loads(text)
        
        if data.get("completion") != "OK":
            raise Exception(f"خطأ: {data.get('completion')}")
        
        params = data["parameters"]
        
        return {
            "question": params["question"],
            "progression": params["progression"],
            "step": params["step"]
        }

async def get_winner(session_data):
    """الحصول على التخمين"""
    
    async with aiohttp.ClientSession() as session:
        url = f"https://ar.akinator.com/list?callback=callback&childMod=false&session={session_data['session']}&signature={session_data['signature']}&step={session_data['step']}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "*/*",
            "Referer": "https://ar.akinator.com/",
            "X-Requested-With": "XMLHttpRequest"
        }
        
        async with session.get(url, headers=headers) as resp:
            text = await resp.text()
        
        import re
        json_match = re.search(r'callback\((.*)\)', text)
        if json_match:
            json_text = json_match.group(1)
            data = json.loads(json_text)
        else:
            data = json.loads(text)
        
        if data.get("completion") != "OK":
            return None
        
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
        await msg.edit(f"❌ خطأ:\n{str(e)[:300]}")

@bot.on(events.CallbackQuery)
async def handle_answer(event):
    chat_id = event.chat_id
    answer_id = int(event.data.decode())
    
    if chat_id not in games_data:
        await event.answer("❌ لا توجد لعبة! أرسل /play", alert=True)
        return
    
    game = games_data[chat_id]
    
    try:
        result = await send_answer(game, answer_id)
        
        game["question"] = result["question"]
        game["progression"] = result["progression"]
        game["step"] = result["step"]
        games_data[chat_id] = game
        
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
                await event.edit("❓ لم أستطع التخمين! ابدأ بـ /play")
            
            del games_data[chat_id]
        else:
            await event.edit(
                f"🧞‍♂️ **السؤال {int(result['step']) + 1}:**\n\n{result['question']}\n\n📊 التقدم: {result['progression']}%",
                buttons=buttons
            )
            
    except Exception as e:
        await event.answer(f"⚠️ خطأ: {str(e)[:80]}", alert=True)
        if chat_id in games_data:
            del games_data[chat_id]

@bot.on(events.NewMessage(pattern="/stop"))
async def stop(event):
    chat_id = event.chat_id
    if chat_id in games_data:
        del games_data[chat_id]
        await event.reply("✅ تم إنهاء اللعبة")
    else:
        await event.reply("ℹ️ لا توجد لعبة نشطة!")

print("✅ بوت Akinator يعمل...")
bot.run_until_disconnected()
