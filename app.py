import os, time, requests, json
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from openai import OpenAI

app = Flask(__name__)
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
ASSISTANT_ID = os.environ.get("ASSISTANT_ID")
TWILIO_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
MAKE_URL = os.environ.get("MAKE_WEBHOOK_URL") # Nova chave!

conversas = {}

@app.route("/webhook", methods=['POST'])
def whatsapp_bot():
    from_number = request.values.get('From', '')
    incoming_msg = request.values.get('Body', '').strip()
    media_url = request.values.get('MediaUrl0')

    # 1. TRATAMENTO DE ÁUDIO (Manteve a correção anterior)
    if media_url:
        try:
            response = requests.get(media_url, auth=(TWILIO_SID, TWILIO_TOKEN), allow_redirects=True)
            if response.status_code == 200:
                with open("temp_audio.ogg", "wb") as f: f.write(response.content)
                with open("temp_audio.ogg", "rb") as audio_file:
                    transcript = client.audio.transcriptions.create(model="whisper-1", file=audio_file, language="pt")
                incoming_msg = transcript.text
                print(f"ÁUDIO TRANSCRITO: {incoming_msg}", flush=True)
                os.remove("temp_audio.ogg")
        except Exception as e:
            print(f"ERRO ÁUDIO: {e}", flush=True)

    # 2. GESTÃO DE THREADS
    if from_number not in conversas:
        thread = client.beta.threads.create()
        conversas[from_number] = thread.id
    thread_id = conversas[from_number]

    # 3. ENVIO PARA O ASSISTENTE
    client.beta.threads.messages.create(thread_id=thread_id, role="user", content=incoming_msg)
    run = client.beta.threads.runs.create(thread_id=thread_id, assistant_id=ASSISTANT_ID)

    # 4. MONITORAMENTO E "FUNCTION CALLING"
    while True:
        while run.status in ["queued", "in_progress"]:
            time.sleep(1)
            run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)

        if run.status == "requires_action":
            # Aqui a mágica acontece: capturamos os dados do lead
            tool_calls = run.required_action.submit_tool_outputs.tool_calls
            tool_outputs = []

            for tool_call in tool_calls:
                if tool_call.function.name == "cadastrar_lead_bancario":
                    dados_lead = json.loads(tool_call.function.arguments)
                    dados_lead['telefone'] = from_number # Adiciona o zap do cliente automaticamente
                    
                    # Envia para o Make.com
                    try:
                        requests.post(MAKE_URL, json=dados_lead)
                        print(f"LEAD ENVIADO AO MAKE: {dados_lead['nome_cliente']}", flush=True)
                    except:
                        print("ERRO AO ENVIAR PARA O MAKE", flush=True)
                    
                    tool_outputs.append({
                        "tool_call_id": tool_call.id,
                        "output": "sucesso"
                    })

            run = client.beta.threads.runs.submit_tool_outputs(
                thread_id=thread_id, run_id=run.id, tool_outputs=tool_outputs
            )
        elif run.status == "completed":
            break
        else:
            break

    # 5. RESPOSTA FINAL AO WHATSAPP
    answer = client.beta.threads.messages.list(thread_id=thread_id).data[0].content[0].text.value
    resp = MessagingResponse()
    resp.message(answer)
    return str(resp)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
