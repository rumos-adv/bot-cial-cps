import os, time
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from openai import OpenAI

app = Flask(__name__)
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
ASSISTANT_ID = os.environ.get("ASSISTANT_ID")

conversas = {}

# --- ISSO RESOLVE O "PORT SCAN TIMEOUT" ---
@app.route("/", methods=['GET'])
def home():
    return "Bot da Rumos Advocacia está Online!", 200
# ------------------------------------------

@app.route("/webhook", methods=['POST'])
def whatsapp_bot():
    from_number = request.values.get('From', '')
    incoming_msg = request.values.get('Body', '')
    
    if from_number not in conversas:
        thread = client.beta.threads.create()
        conversas[from_number] = thread.id
    thread_id = conversas[from_number]

    client.beta.threads.messages.create(thread_id=thread_id, role="user", content=incoming_msg)
    run = client.beta.threads.runs.create(thread_id=thread_id, assistant_id=ASSISTANT_ID)

    while run.status != "completed":
        time.sleep(0.5)
        run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)

    messages = client.beta.threads.messages.list(thread_id=thread_id)
    answer = messages.data[0].content[0].text.value

    # Delay de humanização de 4 segundos (Seguro para o limite do Twilio)
    time.sleep(4) 

    resp = MessagingResponse()
    resp.message(answer)
    return str(resp)
