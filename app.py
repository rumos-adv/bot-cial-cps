import os, time, requests
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from openai import OpenAI

app = Flask(__name__)
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
ASSISTANT_ID = os.environ.get("ASSISTANT_ID")

conversas = {}

@app.route("/", methods=['GET'])
def home():
    return "Dra. Ana da Rumos Advocacia está Online!", 200 # Mantém o Render acordado

@app.route("/webhook", methods=['POST'])
def whatsapp_bot():
    from_number = request.values.get('From', '')
    num_media = int(request.values.get('NumMedia', 0))
    incoming_msg = request.values.get('Body', '').strip()
    
    # 1. TRATAMENTO DE ÁUDIO (WHISPER)
    if num_media > 0:
        media_url = request.values.get('MediaUrl0')
        mime_type = request.values.get('MediaContentType0')
        
        if 'audio' in mime_type:
            # Baixa o áudio do Twilio
            audio_data = requests.get(media_url).content
            file_extension = mime_type.split('/')[-1]
            file_name = f"temp_audio.{file_extension}"
            
            with open(file_name, 'wb') as f:
                f.write(audio_data)
            
            # Transcreve usando Whisper
            with open(file_name, 'rb') as audio_file:
                transcription = client.audio.transcriptions.create(
                    model="whisper-1", 
                    file=audio_file
                )
            incoming_msg = transcription.text
            os.remove(file_name) # Limpa o arquivo temporário

    # 2. COMANDO RESETAR
    if incoming_msg.upper() == "RESETAR":
        if from_number in conversas:
            del conversas[from_number]
        resp = MessagingResponse()
        resp.message("Memória limpa! Dra. Ana pronta para um novo atendimento.")
        return str(resp)

    # 3. GERENCIAMENTO DE THREAD E RESPOSTA
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

    time.sleep(4) # Humanização segura para o Twilio

    resp = MessagingResponse()
    resp.message(answer)
    return str(resp)
