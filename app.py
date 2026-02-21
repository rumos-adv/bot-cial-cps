import os, time
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from openai import OpenAI

app = Flask(__name__)
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
ASSISTANT_ID = os.environ.get("ASSISTANT_ID")

conversas = {}

# Rota para o Render não desligar o bot (Health Check)
@app.route("/", methods=['GET'])
def home():
    return "Bot Rumos Advocacia: Online e Operacional!", 200

@app.route("/webhook", methods=['POST'])
def whatsapp_bot():
    from_number = request.values.get('From', '')
    incoming_msg = request.values.get('Body', '')
    
    # 1. Gerencia a Thread (Memória)
    if from_number not in conversas:
        thread = client.beta.threads.create()
        conversas[from_number] = thread.id
    
    # Aqui estava o erro: agora usamos apenas 't_id'
    t_id = conversas[from_number]

    # 2. Envia a mensagem para a OpenAI
    client.beta.threads.messages.create(thread_id=t_id, role="user", content=incoming_msg)
    
    # 3. Inicia o Assistente
    run = client.beta.threads.runs.create(thread_id=t_id, assistant_id=ASSISTANT_ID)

    # 4. Aguarda a resposta (Polling)
    while run.status != "completed":
        time.sleep(0.5)
        run = client.beta.threads.runs.retrieve(thread_id=t_id, run_id=run.id)
        if run.status in ["failed", "cancelled", "expired"]:
            return "Erro no processamento", 500

    # 5. Pega o texto da resposta
    messages = client.beta.threads.messages.list(thread_id=t_id)
    answer = messages.data[0].content[0].text.value

    # Delay de humanização (4 segundos é o tempo ideal para o Twilio)
    time.sleep(4) 

    resp = MessagingResponse()
    resp.message(answer)
    return str(resp)
