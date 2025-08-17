def gerar_pix(user_id: int, valor: float):
    payload = {
        "amount": valor,
        "description": "Acesso ao Grupo VIP",
        "customer": {
            "name": f"User {user_id}",
            "document": "103.049.271-98"  # CPF mantido
        },
        "external_id": str(user_id),
        "callback_url": f"{WEBHOOK_URL}/expfy_webhook"
    }
    headers = {
        "X-Public-Key": EXPFY_PUBLIC_KEY,
        "X-Secret-Key": EXPFY_SECRET_KEY,
        "Content-Type": "application/json"
    }
    try:
        print("🔹 Enviando requisição para Expfy...")
        print("Payload:", payload)
        r = requests.post("https://expfypay.com/api/v1/payments", json=payload, headers=headers, timeout=10)
        print("Status HTTP:", r.status_code)
        print("Resposta da API:", r.text)
        if r.status_code == 200:
            data = r.json()
            qr = data.get("pix_qr_code_url")
            pix_code = data.get("pix_code") or data.get("link_pagamento")
            if qr and pix_code:
                print("✅ Pix gerado com sucesso!")
            else:
                print("⚠️ Pix não retornado na resposta.")
            return qr, pix_code
        else:
            print("❌ Erro na API da Expfy:", r.status_code, r.text)
            return None, None
    except Exception as e:
        print("❌ Exception ao gerar Pix:", e)
        return None, None
