import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import threading
import time

TELEGRAM_TOKEN = "TOKEN_BOT_CUA_BAN"
RENDER_URL = "https://minizo-sevaapi.onrender.com"
BOT_SECRET = "BOT_SECRET_123"
ADMIN_ID = 123456789 # ID Telegram của bạn

def ping_loop():
    while True:
        try: requests.get(f"{RENDER_URL}/ping", timeout=10)
        except: pass
        time.sleep(300)

def call_api(action, payload):
    payload['action'] = action
    try:
        res = requests.post(f"{RENDER_URL}/api/bot", json=payload, headers={"X-Bot-Key": BOT_SECRET}, timeout=60)
        return res.json()
    except Exception as e:
        return {"status": "ERROR", "message": f"Lỗi: {e}"}

async def check_admin(update: Update):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Bạn không phải Admin!")
        return False
    return True

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update): return
    text = """📜 DANH SÁCH LỆNH:
/ping /taokey /vinhvien /xemkey /xoakey /xoacode
/resetmay /allmay /thongtin /kick /backlist
/xoabacklist /thongke /lockupdate /unlockupdate"""
    await update.message.reply_text(text)

async def cmd_ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update): return
    msg = await update.message.reply_text("⏳ Đang gọi Server...")
    try:
        res = requests.get(f"{RENDER_URL}/ping", timeout=60)
        if "ALIVE" in res.text: await msg.edit_text("✅ Server đã thức!")
        else: await msg.edit_text("⚠️ Lỗi Server.")
    except Exception as e: await msg.edit_text(f"❌ {e}")

async def cmd_taokey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update) or len(context.args) < 1: return await update.message.reply_text("Cú pháp: /taokey <giờ>")
    hours = int(context.args[0])
    key = f"MINIZO-{int(time.time())}"
    res = call_api('create_key', {"key_code": key, "hours": hours})
    await update.message.reply_text(f"✅ Key: `{key}`" if res['status']=='OK' else f"❌ {res['message']}", parse_mode='Markdown')

async def cmd_vinhvien(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update): return
    key = f"MINIZO-VIP-{int(time.time())}"
    res = call_api('create_key', {"key_code": key, "hours": 0})
    await update.message.reply_text(f"✅ Key VIP: `{key}`" if res['status']=='OK' else f"❌ {res['message']}", parse_mode='Markdown')

async def cmd_xemkey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update) or len(context.args) < 1: return await update.message.reply_text("Cú pháp: /xemkey <key>")
    res = call_api('get_key_info', {"key_code": context.args[0]})
    if res['status'] == 'OK':
        d = res['data']
        await update.message.reply_text(f"🔍 Key: {d[1]}\nMáy: {d[2]}\nHạn: {d[4]}\nTrạng thái: {d[5]}")
    else: await update.message.reply_text(f"❌ {res['message']}")

async def cmd_xoakey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update) or len(context.args) < 1: return await update.message.reply_text("Cú pháp: /xoakey <key>")
    res = call_api('delete_key', {"key_code": context.args[0]})
    await update.message.reply_text(f"🗑️ {res['message']}")

async def cmd_xoacode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update): return
    res = call_api('delete_all', {})
    await update.message.reply_text(f"🧹 {res['message']}")

async def cmd_resetmay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update) or len(context.args) < 1: return await update.message.reply_text("Cú pháp: /resetmay <key>")
    res = call_api('reset_device', {"key_code": context.args[0]})
    await update.message.reply_text(f"🔄 {res['message']}")

async def cmd_allmay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update): return
    res = call_api('all_devices', {})
    if res['status'] == 'OK':
        msg = "📱 MÁY:\n" + "\n".join([f"{i+1}. {d[1]} - `{d[0]}`" for i, d in enumerate(res['data'])])
        await update.message.reply_text(msg, parse_mode='Markdown')
    else: await update.message.reply_text(f"❌ {res['message']}")

async def cmd_thongtin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update) or len(context.args) < 1: return await update.message.reply_text("Cú pháp: /thongtin <số>")
    res = call_api('device_info', {"index": context.args[0]})
    if res['status'] == 'OK':
        d = res['data']
        await update.message.reply_text(f"📱 Máy: {d[1]}\nMã: {d[0]}\nIP: {d[2]}\nMạng: {d[3]}\nKey: {d[6]}")
    else: await update.message.reply_text(f"❌ {res['message']}")

async def cmd_kick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update) or len(context.args) < 1: return await update.message.reply_text("Cú pháp: /kick <mã_máy>")
    res = call_api('kick_device', {"device_id": context.args[0]})
    await update.message.reply_text(f"👢 {res['message']}")

async def cmd_backlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update) or len(context.args) < 1: return await update.message.reply_text("Cú pháp: /backlist <mã_máy>")
    res = call_api('blacklist', {"device_id": context.args[0]})
    await update.message.reply_text(f"🚫 {res['message']}")

async def cmd_xoabacklist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update) or len(context.args) < 1: return await update.message.reply_text("Cú pháp: /xoabacklist <mã_máy>")
    res = call_api('unblacklist', {"device_id": context.args[0]})
    await update.message.reply_text(f"✅ {res['message']}")

async def cmd_thongke(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update): return
    res = call_api('stats', {})
    await update.message.reply_text(f"📊 {res['message']}")

async def cmd_lockupdate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update): return
    res = call_api('lock_update', {"message": "Ứng dụng đang bảo trì, vui lòng quay lại sau!"})
    await update.message.reply_text(f"🔒 {res['message']}")

async def cmd_unlockupdate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update): return
    res = call_api('unlock_update', {})
    await update.message.reply_text(f"🔓 {res['message']}")

if __name__ == '__main__':
    threading.Thread(target=ping_loop, daemon=True).start()
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    commands = {
        "help": cmd_help, "ping": cmd_ping, "taokey": cmd_taokey, "vinhvien": cmd_vinhvien,
        "xemkey": cmd_xemkey, "xoakey": cmd_xoakey, "xoacode": cmd_xoacode, "resetmay": cmd_resetmay,
        "allmay": cmd_allmay, "thongtin": cmd_thongtin, "kick": cmd_kick, "backlist": cmd_backlist,
        "xoabacklist": cmd_xoabacklist, "thongke": cmd_thongke, "lockupdate": cmd_lockupdate, "unlockupdate": cmd_unlockupdate
    }
    for cmd, func in commands.items():
        app.add_handler(CommandHandler(cmd, func))
    print("Bot đang chạy full lệnh...")
    app.run_polling()
