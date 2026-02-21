import os, time
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from openai import OpenAI

app = Flask(__name__)
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
ASSISTANT_ID = os.environ.get("ASSISTANT_ID")

# Memória do bot (fica logo no início)
conversas = {}

# --- ROTA DE SAÚDE (Para o Render não desligar o bot) ---
@app.route("/", methods=['GET'])
def home():
    return "Serviço da Rumos Advocacia está Online!", 200

# --- WEBHOOK PRINCIPAL (Onde a mágica acontece) ---
@app.route("/webhook", methods=['POST'])
def whatsapp_bot():
    from_number = request.values.get('From', '')
    incoming_msg = request.values.get('Body', '').strip()
    
    # --- COMANDO SECRETO PARA SEUS TESTES ---
    # Se você digitar exatamente RESETAR, o bot esquece seu número
    if incoming_msg.upper() == "RESETAR":
        if from_number in conversas:
            del conversas[from_number]
        resp = MessagingResponse()
        resp.message("Memória limpa, Rodrigo! Podemos recomeçar o teste do zero.")
        return str(resp)

    # 1. Gerenciamento de Memória (Thread)
    if from_number not in conversas:
        thread = client.beta.threads.create()
        conversas[from_number] = thread.id
    thread_id = conversas[from_number]

    # 2. Envio para OpenAI
    client.beta.threads.messages.create(thread_id=thread_id, role="user", content=incoming_msg)
    run = client.beta.threads.runs.create(thread_id=thread_id, assistant_id=ASSISTANT_ID)

    while run.status != "completed":
        time.sleep(0.5)
        run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)

    # 3. Captura da Resposta
    messages = client.beta.threads.messages.list(thread_id=thread_id)
    answer = messages.data[0].content[0].text.value

    # 4. Humanização (4 segundos de espera)
    time.sleep(4) 

    resp = MessagingResponse()
    resp.message(answer)
    return str(resp)
