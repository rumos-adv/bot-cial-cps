import os, time
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from openai import OpenAI

app = Flask(__name__)
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
ASSISTANT_ID = os.environ.get("ASSISTANT_ID")

# O segredo da memória está aqui:
conversas = {}

@app.route("/webhook", methods=['POST'])
def whatsapp_bot():
    from_number = request.values.get('From', '')
    incoming_msg = request.values.get('Body', '')
    
    # Se for um número novo, cria uma Thread. Se já existe, recupera a antiga.
    if from_number not in conversas:
        thread = client.beta.threads.create()
        conversas[from_number] = thread.id
    
    thread_id = conversas[from_number]

    # Adiciona a sua mensagem à conversa existente
    client.beta.threads.messages.create(thread_id=thread_id, role="user", content=incoming_msg)

    # Manda a IA pensar
    run = client.beta.threads.runs.create(thread_id=thread_id, assistant_id=ASSISTANT_ID)

    while run.status != "completed":
        time.sleep(0.5)
        run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)

    # Pega a resposta e envia de volta
    messages = client.beta.threads.messages.list(thread_id=thread_id)
    answer = messages.data[0].content[0].text.value

    resp = MessagingResponse()
    resp.message(answer)
    return str(resp)
