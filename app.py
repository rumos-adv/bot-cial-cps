import os, time
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from openai import OpenAI

app = Flask(__name__)
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
ASSISTANT_ID = os.environ.get("ASSISTANT_ID")

# Memória das conversas
conversas = {}

@app.route("/", methods=['GET'])
def home():
    return "Bot Rumos Online", 200

@app.route("/webhook", methods=['POST'])
def whatsapp_bot():
    from_number = request.values.get('From', '')
    incoming_msg = request.values.get('Body', '').strip()
    
    # Comando para você limpar seus testes
    if incoming_msg.upper() == "RESETAR":
        if from_number in conversas:
            del conversas[from_number]
        resp = MessagingResponse()
        resp.message("Memória limpa, Rodrigo! Vamos recomeçar.")
        return str(resp)

    if from_number not in conversas:
        thread = client.beta.threads.create()
        conversas[from_number] = thread.id
    thread_id = conversas[from_number]

    client.beta.threads.messages.create(thread_id=thread_id, role="user", content=incoming_msg)
    run = client.beta.threads.runs.create(thread_id=thread_id, assistant_id=ASSISTANT_ID)

    # Loop de espera com segurança
    while run.status not in ["completed", "failed", "cancelled"]:
        time.sleep(1)
        run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)

    if run.status == "completed":
        messages = client.beta.threads.messages.list(thread_id=thread_id)
        answer = messages.data[0].content[0].text.value
    else:
        answer = "Desculpe, tive um pequeno problema técnico agora. Pode repetir a mensagem?"

    time.sleep(4) # Humanização
    resp = MessagingResponse()
    resp.message(answer)
    return str(resp)
