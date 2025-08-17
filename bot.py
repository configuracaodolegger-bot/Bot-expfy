from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from aiohttp import web
import os

# ======================
# CONFIGURAÇÃO
# ======================
TOKEN = "8494152099:AAHhUweW8W9A0R3y_w2Gz2iV5Te0atNmSmc"
LINK_GRUPO = "https://t.me/+RWq8E624d6E3MzEx"
VALOR = 17.90

# URL do webhook no Render (substituir após deploy)
WEBHOOK_URL = "https://bot-expfy.onrender.com"

# Chave secreta definida por você para validar o webhook
WEBHOOK_KEY = "minha_chave_123"

# Registro de usuários
usuarios = {}  # user_id -> {"username": str, "confirmado": bool, "pix_link": str, "chat_id": int}

# Inicializa bot
tg_app = Application.builder().token(TOKEN).build()

# ======================
# FUNÇÃO PIX FICTÍCIO
# ======================
def gerar_pix(user_id: int, valor: float):
    qr_fake = "https://via.placeholder.com/200.png?text=QR+Test"
    link_fake = "https://expfy.com/fake-link"
    return qr_fake, link_fake

# ======================
# COMANDOS TELEGRAM
# ======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"👋 Olá {update.effective_user.first_name}!\n"
        "Conteúdo hot 🔥😈🍑\n"
        "Digite /comprar para gerar seu Pix fictício e entrar no grupo."
    )

async def comprar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    chat_id = update.message.chat_id

    if user_id in usuarios and usuarios[user_id].get("confirmado"):
        await update.message.reply_text("✅ Você já foi confirmado e tem acesso ao grupo.")
        return

    qr_code_url, link_pagamento = gerar_pix(user_id, VALOR)
    usuarios[user_id] = {
        "username": user.username,
        "confirmado": False,
        "pix_link": link_pagamento,
        "chat_id": chat_id
    }

    await update.message.reply_photo(
        photo=qr_code_url,
        caption=f"💰 Pague {VALOR:.2f} via Pix fictício\n"
                f"TXID: {user_id}\n\n"
                "Aguarde a confirmação automática do pagamento..."
    )

# ======================
# WEBHOOK SIMULADO
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
            await tg_app.bot.send_message(
                chat_id=chat_id,
                text=f"✅ Pagamento fictício confirmado!\nAqui está seu acesso ao grupo: {LINK_GRUPO}"
            )
    return web.Response(text="OK")

# ======================
# HANDLERS TELEGRAM
# ======================
tg_app.add_handler(CommandHandler("start", start))
tg_app.add_handler(CommandHandler("comprar", comprar))

# ======================
# RODA BOT + WEBHOOK
# ======================
if __name__ == "__main__":
    app = web.Application()
    app.router.add_post(f"/{TOKEN}", expfy_webhook)
    PORT = int(os.environ.get("PORT", 10000))
    print(f"Bot rodando no Render! Webhook URL: {WEBHOOK_URL}/{TOKEN}")
    tg_app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_path=f"/{TOKEN}",
        webhook_url=f"{WEBHOOK_URL}/{TOKEN}",
        app=app
    )

