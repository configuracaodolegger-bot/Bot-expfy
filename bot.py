from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import requests
from aiohttp import web
import os

# ======================
# CONFIGURAÇÃO
# ======================
TOKEN = "8494152099:AAHhUweW8W9A0R3y_w2Gz2iV5Te0atNmSmc"
LINK_GRUPO = "https://t.me/+RWq8E624d6E3MzEx"
PIX_CHAVE = "65996282966"
VALOR = 17.90

# API Key da Expfy
EXPFY_API_KEY = "sk_7746ecdd7f20b11a1d9c5265a7ecb2c5d34411f506e3446125b4fe830379e7c4"

# URL do webhook no Render (substituir após deploy)
WEBHOOK_URL = "https://bot-expfy.onrender.com"

# Chave secreta definida por você para validar o webhook
WEBHOOK_KEY = "minha_chave_123"

# Registro de usuários
usuarios = {}  # user_id -> {"username": str, "confirmado": bool, "pix_link": str, "chat_id": int}

# Inicializa bot
tg_app = Application.builder().token(TOKEN).build()

# ======================
# GERAR PIX VIA EXPFY
# ======================
def gerar_pix(user_id: int, valor: float):
    payload = {
        "chave": PIX_CHAVE,
        "valor": valor,
        "txid": str(user_id),
        "descricao": "Acesso ao grupo exclusivo",
        "webhook_url": WEBHOOK_URL,
        "webhook_secret": WEBHOOK_KEY
    }
    headers = {"Authorization": f"Bearer {EXPFY_API_KEY}"}
    response = requests.post("https://api.expfy.com/v1/pix", json=payload, headers=headers)
    if response.status_code == 200:
        data = response.json()
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

    if user_id in usuarios and usuarios[user_id].get("confirmado"):
        await update.message.reply_text("✅ Você já foi confirmado e tem acesso ao grupo!")
        return

    qr_code_url, link_pagamento = gerar_pix(user_id, VALOR)
    if qr_code_url and link_pagamento:
        usuarios[user_id] = {
            "username": user.username,
            "confirmado": False,
            "pix_link": link_pagamento,
            "chat_id": chat_id
        }

        await update.message.reply_photo(
            photo=qr_code_url,
            caption=f"💰 Pague {VALOR:.2f} via Pix\n"
                    f"Chave: {PIX_CHAVE}\n"
                    f"TXID: {user_id}\n\n"
                    "Aguarde a confirmação automática do pagamento..."
        )
    else:
        await update.message.reply_text("❌ Não foi possível gerar o Pix. Tente novamente mais tarde.")

# ======================
# WEBHOOK EXPFY PAY
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
                text=f"✅ Pagamento confirmado!\nAqui está seu acesso ao grupo: {LINK_GRUPO}"
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
    app.router.add_post("/webhook", expfy_webhook)
    PORT = int(os.environ.get("PORT", 10000))
    web.run_app(app, port=PORT)
