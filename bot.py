from telegram import Update
from telegram.ext import Application, CommandHandler
from aiohttp import web
import requests
import os
import asyncio

# ======================
# CONFIGURAÇÃO VIA ENV
# ======================
TOKEN = os.environ.get("TOKEN")
LINK_GRUPO = os.environ.get("LINK_GRUPO")
PIX_CHAVE = os.environ.get("PIX_CHAVE")
VALOR = float(os.environ.get("VALOR", "17.90"))
EXPFY_API_KEY = os.environ.get("EXPFY_API_KEY")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
WEBHOOK_KEY = os.environ.get("WEBHOOK_KEY")

usuarios = {}  # user_id -> {"username": str, "confirmado": bool, "pix_link": str, "chat_id": int}

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
        "webhook_url": f"{WEBHOOK_URL}/expfy_webhook",
        "webhook_secret": WEBHOOK_KEY
    }
    headers = {"Authorization": f"Bearer {EXPFY_API_KEY}"}
    try:
        r = requests.post("https://api.expfy.com/v1/pix", json=payload, headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json()
            return data.get("qr_code_url"), data.get("link_pagamento")
    except Exception as e:
        print("Erro ao gerar Pix:", e)
    return None, None

# ======================
# COMANDOS TELEGRAM
# ======================
async def start(update: Update, context):
    await update.message.reply_text(
        f"👋 Olá {update.effective_user.first_name}!\nDigite /comprar para gerar seu Pix e entrar no grupo."
    )

async def comprar(update: Update, context):
    user_id = update.effective_user.id
    chat_id = update.message.chat_id

    if user_id in usuarios and usuarios[user_id]["confirmado"]:
        await update.message.reply_text("✅ Você já foi confirmado e tem acesso ao grupo.")
        return

    qr_code, link_pagamento = gerar_pix(user_id, VALOR)
    if qr_code and link_pagamento:
        usuarios[user_id] = {
            "username": update.effective_user.username,
            "confirmado": False,
            "pix_link": link_pagamento,
            "chat_id": chat_id
        }
        await update.message.reply_photo(
            photo=qr_code,
            caption=f"💰 Pague {VALOR:.2f} via Pix\nChave: {PIX_CHAVE}\nTXID: {user_id}\n\n"
                    "Aguarde a confirmação automática do pagamento..."
        )
    else:
        await update.message.reply_text("❌ Não foi possível gerar o Pix.")

# ======================
# WEBHOOK EXPFY
# ======================
async def expfy_webhook(request):
    if request.headers.get("X-Secret-Key", "") != WEBHOOK_KEY:
        return web.Response(status=403, text="Invalid secret")

    data = await request.json()
    txid = data.get("txid")
    if txid and data.get("status") == "PAID":
        user_id = int(txid)
        if user_id in usuarios and not usuarios[user_id]["confirmado"]:
            usuarios[user_id]["confirmado"] = True
            await tg_app.bot.send_message(
                chat_id=usuarios[user_id]["chat_id"],
                text=f"✅ Pagamento confirmado!\nAcesso ao grupo: {LINK_GRUPO}"
            )

    return web.Response(text="OK")

# ======================
# WEBHOOK TELEGRAM
# ======================
async def telegram_webhook(request):
    data = await request.json()
    update = Update.de_json(data, tg_app.bot)
    await tg_app.update_queue.put(update)
    return web.Response(text="OK")

# ======================
# HANDLERS
# ======================
tg_app.add_handler(CommandHandler("start", start))
tg_app.add_handler(CommandHandler("comprar", comprar))

# ======================
# RODA BOT + WEBHOOK
# ======================
async def main():
    app = web.Application()
    app.router.add_post("/expfy_webhook", expfy_webhook)
    app.router.add_post(f"/{TOKEN}", telegram_webhook)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.environ.get("PORT", 10000)))
    await site.start()

    await tg_app.initialize()
    await tg_app.start()

    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
