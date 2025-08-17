from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import requests
from aiohttp import web
import os
import asyncio

# ======================
# CONFIGURAÇÃO
# ======================
TOKEN = "8494152099:AAHhUweW8W9A0R3y_w2Gz2iV5Te0atNmSmc"
LINK_GRUPO = "https://t.me/+RWq8E624d6E3MzEx"
PIX_CHAVE = "65996282966"
VALOR = 17.90
EXPFY_API_KEY = "sk_7746ecdd7f20b11a1d9c5265a7ecb2c5d34411f506e3446125b4fe830379e7c4"
WEBHOOK_URL = "https://bot-expfy.onrender.com"
WEBHOOK_KEY = "minha_chave_123"

usuarios = {}  # user_id -> {"username": str, "confirmado": bool, "pix_link": str, "chat_id": int}

tg_app = Application.builder().token(TOKEN).build()

# ======================
# GERAR PIX
# ======================
def gerar_pix(user_id: int, valor: float):
    payload = {
        "chave": PIX_CHAVE,
        "valor": valor,
        "txid": str(user_id),
        "descricao": "Acesso ao grupo exclusivo",
        "webhook_url": f"{WEBHOOK_URL}/expfy_webhook",
        "webhook_secret": WEBHOOK_KEY
    }
    headers = {"Authorization": f"Bearer {EXPFY_API_KEY}"}
    r = requests.post("https://api.expfy.com/v1/pix", json=payload, headers=headers)
    if r.status_code == 200:
        data = r.json()
        return data.get("qr_code_url"), data.get("link_pagamento")
    return None, None

# ======================
# COMANDOS TELEGRAM
# ======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"👋 Olá {update.effective_user.first_name}!\n"
        "Conteúdo hot 🔥😈🍑\n"
        "Digite /comprar para gerar seu Pix e entrar no grupo."
    )

async def comprar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    chat_id = update.message.chat_id

    if user_id in usuarios and usuarios[user_id]["confirmado"]:
        await update.message.reply_text("✅ Você já foi confirmado e tem acesso ao grupo.")
        return

    qr, link = gerar_pix(user_id, VALOR)
    if qr and link:
        usuarios[user_id] = {"username": user.username, "confirmado": False, "pix_link": link, "chat_id": chat_id}
        await update.message.reply_photo(
            photo=qr,
            caption=f"💰 Pague {VALOR:.2f} via Pix\nChave: {PIX_CHAVE}\nTXID: {user_id}\n\nAguarde a confirmação automática..."
        )
    else:
        await update.message.reply_text("❌ Não foi possível gerar o Pix.")

# ======================
# WEBHOOK EXPFY
# ======================
async def expfy_webhook(request):
    secret_received = request.headers.get("X-Secret-Key", "")
    if secret_received != WEBHOOK_KEY:
        return web.Response(status=403, text="Invalid secret")

    data = await request.json()
    txid = data.get("txid")
    status = data.get("status")

    if txid and status == "PAID":
        user_id = int(txid)
        if user_id in usuarios and not usuarios[user_id]["confirmado"]:
            usuarios[user_id]["confirmado"] = True
            chat_id = usuarios[user_id]["chat_id"]
            await tg_app.bot.send_message(chat_id=chat_id, text=f"✅ Pagamento confirmado!\nAcesso: {LINK_GRUPO}")
    return web.Response(text="OK")

# ======================
# HANDLERS TELEGRAM
# ======================
tg_app.add_handler(CommandHandler("start", start))
tg_app.add_handler(CommandHandler("comprar", comprar))

# ======================
# RODA SERVIDOR AIOHTTP + BOT
# ======================
async def main():
    runner = web.AppRunner(web.Application())
    app = runner.app
    app.router.add_post("/expfy_webhook", expfy_webhook)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.environ.get("PORT", 10000)))
    await site.start()
    print("Servidor rodando!")

    # Inicializa bot polling no background (modo webhook do Telegram será via setWebhook)
    await tg_app.initialize()
    await tg_app.start()
    print("Bot do Telegram iniciado!")

    # Mantém o loop rodando
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
