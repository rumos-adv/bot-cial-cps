import os, time, requests
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from openai import OpenAI

app = Flask(__name__)
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
ASSISTANT_ID = os.environ.get("ASSISTANT_ID")

# Memória das conversas para o bot não ter "amnésia"
conversas = {}

# --- ROTA DE SAÚDE (Mantém o Render Online) ---
@app.route("/", methods=['GET'])
def home():
    return "Dra. Ana está Online e Operacional!", 200

# --- WEBHOOK PRINCIPAL (WhatsApp + OpenAI) ---
@app.route("/webhook", methods=['POST'])
def whatsapp_bot():
    from_number = request.values.get('From', '')
    incoming_msg = request.values.get('Body', '').strip()
    media_url = request.values.get('MediaUrl0') # Link do áudio se houver

    # 1. WHISPER: TRANSCREVE ÁUDIO EM TEXTO AUTOMATICAMENTE
    if media_url:
        try:
            audio_data = requests.get(media_url).content
            with open("temp_audio.ogg", "wb") as f:
                f.write(audio_data)
            
            with open("temp_audio.ogg", "rb") as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1", 
                    file=audio_file
                )
            incoming_msg = transcript.text # O áudio vira texto para a Dra. Ana ler
            os.remove("temp_audio.ogg")
        except:
            incoming_msg = "[Erro ao processar áudio]"

    # 2. COMANDO RESETAR: LIMPA A MEMÓRIA DO SEU NÚMERO
    if incoming_msg.upper() == "RESETAR":
        if from_number in conversas:
            del conversas[from_number]
        resp = MessagingResponse()
        resp.message("Memória limpa, Rodrigo! Dra. Ana está pronta para um novo teste.")
        return str(resp)

    # 3. CONEXÃO COM O ASSISTENTE (THREAD E RUN)
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

    # 4. FINALIZAÇÃO COM DELAY DE 1 SEGUNDO (EVITA TIMEOUT)
    time.sleep(1) 

    resp = MessagingResponse()
    resp.message(answer)
    return str(resp)
