import os, time, requests, sys
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from openai import OpenAI

app = Flask(__name__)
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
ASSISTANT_ID = os.environ.get("ASSISTANT_ID")

conversas = {}

@app.route("/", methods=['GET'])
def home():
    return "Dra. Ana está Online!", 200

@app.route("/webhook", methods=['POST'])
def whatsapp_bot():
    from_number = request.values.get('From', '')
    incoming_msg = request.values.get('Body', '').strip()
    media_url = request.values.get('MediaUrl0')

    # 1. WHISPER COM FOCO EM PORTUGUÊS
    if media_url:
        try:
            audio_data = requests.get(media_url).content
            with open("temp_audio.ogg", "wb") as f:
                f.write(audio_data)
            with open("temp_audio.ogg", "rb") as audio_file:
                # Adicionamos 'language="pt"' para o Whisper ser mais preciso
                transcript = client.audio.transcriptions.create(
                    model="whisper-1", 
                    file=audio_file,
                    language="pt" 
                )
            incoming_msg = transcript.text
            print(f"O CLIENTE DISSE NO ÁUDIO: {incoming_msg}", flush=True)
            os.remove("temp_audio.ogg")
        except Exception as e:
            print(f"ERRO NO ÁUDIO: {e}", flush=True)
            incoming_msg = "[Erro ao processar áudio]"

    if incoming_msg.upper() == "RESETAR":
        if from_number in conversas:
            del conversas[from_number]
        resp = MessagingResponse()
        resp.message("Memória limpa! Dra. Ana pronta para recomeçar.")
        return str(resp)

    # 2. LÓGICA DO ASSISTENTE
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

    # --- AGORA VOCÊ VAI VER TUDO NO LOG ---
    print(f"DRA. ANA RESPONDEU: {answer}", flush=True)

    time.sleep(1) 
    resp = MessagingResponse()
    resp.message(answer)
    return str(resp)
