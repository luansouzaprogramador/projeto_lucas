from flask import Flask, request, jsonify, render_template, redirect, url_for
import requests
from datetime import datetime
import os

app = Flask(__name__)
chamados = []
TOKEN = os.getenv('WHATSAPP_TOKEN', 'seu_token_padrao')
TELEFONE_ID = os.getenv('TELEFONE_ID', 'seu_telefone_id_padrao')
VERIFY_TOKEN = os.getenv('VERIFY_TOKEN', 'provac@2025')


def extrair_mensagem(data):
    entry = data.get("entry", [{}])[0]
    changes = entry.get("changes", [{}])[0]
    value = changes.get("value", {})
    messages = value.get("messages", [])
    return messages[0] if messages else None


def encontrar_chamado_aberto(numero):
    for chamado in chamados:
        if chamado["numero"] == numero and chamado["status"] == "Aberto":
            return chamado
    return None


@app.route("/webhook", methods=["GET"])
def verify():
    if request.args.get("hub.mode") and request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge")
    return "Erro de verificação", 403


@app.route("/webhook", methods=["POST"])
def receive_message():
    data = request.get_json()
    if not (mensagem := extrair_mensagem(data)):
        print(f"Evento não processado: {data}")
        return jsonify({"status": "ignored"}), 200

    numero = mensagem["from"]
    texto = mensagem.get("text", {}).get("body", "")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    chamado = encontrar_chamado_aberto(numero)

    if chamado:
        nova_msg = {"texto": texto, "data": timestamp}
        chamado["historico"].append(nova_msg)
        chamado["data_ultima"] = timestamp
        print(f"Mensagem adicionada ao chamado #{chamado['id']}")
    else:
        novo_chamado = {
            "id": len(chamados) + 1,
            "numero": numero,
            "status": "Aberto",
            "data_abertura": timestamp,
            "data_ultima": timestamp,
            "historico": [{"texto": texto, "data": timestamp}]
        }
        chamados.append(novo_chamado)
        print(f"Novo chamado #{novo_chamado['id']} criado")
        enviar_template(numero)

    return jsonify({"status": "ok"}), 200


def enviar_template(numero):
    url = f"https://graph.facebook.com/v23.0/{TELEFONE_ID}/messages"
    headers = {"Authorization": f"Bearer {TOKEN}",
               "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "template",
        "template": {"name": "hello_world", "language": {"code": "en_US"}}
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        print(f"Template enviado para {numero}.")
    except requests.exceptions.RequestException as e:
        print(f"Erro ao enviar template: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Detalhes: {e.response.text}")


@app.route("/")
def index():
    return redirect(url_for('listar_chamados'))


@app.route("/chamados")
def listar_chamados():
    return render_template("chamados/index.html", chamados=chamados)


@app.route("/chamados/<int:id>/fechar", methods=["POST"])
def fechar_chamado(id):
    for chamado in chamados:
        if chamado["id"] == id:
            chamado["status"] = "Fechado"
            return redirect(url_for('listar_chamados'))
    return "Chamado não encontrado", 404


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
