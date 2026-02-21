import os, time, random
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from openai import OpenAI

app = Flask(__name__)
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
ASSISTANT_ID = os.environ.get("ASSISTANT_ID")

# Memória para não esquecer o contexto
conversas = {}

@app.route("/webhook", methods=['POST'])
def whatsapp_bot():
    from_number = request.values.get('From', '')
    incoming_msg = request.values.get('Body', '')
    
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

    # --- EFEITO DE HUMANIZAÇÃO ---
    # Calculamos um delay baseado no tamanho da resposta (ex: 1 segundo a cada 50 caracteres)
    # mas limitamos para não estourar o tempo do Twilio.
    tempo_leitura = len(answer) / 50 
    delay_final = min(max(tempo_leitura, 3), 10) # No mínimo 3s, no máximo 10s
    time.sleep(delay_final) 
    # -----------------------------

    resp = MessagingResponse()
    resp.message(answer)
    return str(resp)
