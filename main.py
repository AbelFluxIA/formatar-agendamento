from flask import Flask, request, jsonify
import re
import json
import os

app = Flask(__name__)

@app.route('/formatar-agendamento', methods=['POST'])
def formatar_agendamento():
    try:
        # Pega os dados do corpo da requisição
        data = request.get_json()
        
        cpf = data.get('cpf', '')
        horarios = data.get('horarios', {})
        horario_escolhido = str(data.get('horario_escolhido', ''))

        # --- 1. TRATAMENTO DO CPF ---
        # Remove tudo que não for dígito
        cpf_limpo = re.sub(r'\D', '', str(cpf))

        # --- 2. TRATAMENTO DOS HORÁRIOS ---
        lista_horarios = horarios

        # Se a automação enviar o JSON como string, fazemos o parse
        if isinstance(horarios, str):
            try:
                lista_horarios = json.loads(horarios)
            except json.JSONDecodeError:
                return jsonify({"error": "O campo 'horarios' não é um JSON válido."}), 400

        # Verifica se a estrutura schedules existe
        if not lista_horarios or 'schedules' not in lista_horarios:
            return jsonify({"error": "JSON de horários inválido ou sem a chave 'schedules'."}), 400

        # --- 3. BUSCA DO HORÁRIO ESCOLHIDO ---
        dados_encontrados = None

        # Percorre cada dia disponível
        for dia in lista_horarios.get('schedules', []):
            avaliable_times = dia.get('AvaliableTimes', [])
            
            if avaliable_times:
                for slot in avaliable_times:
                    # LÓGICA DE COMPARAÇÃO:
                    # Verifica se a string "horario_escolhido" contém a Data e o horário de início
                    
                    data_no_slot = dia.get('Date', '') # ex: "2025-12-05"
                    hora_inicio_slot = slot.get('from', '') # ex: "16:00"

                    if data_no_slot and hora_inicio_slot:
                        if data_no_slot in horario_escolhido and hora_inicio_slot in horario_escolhido:
                            
                            # Montagem da data fixa solicitada: Data + T03:00:00.000Z
                            data_formatada_fixa = f"{data_no_slot}T03:00:00.000Z"

                            dados_encontrados = {
                                "from": slot.get('from'),
                                "to": slot.get('to'),
                                "date": data_formatada_fixa
                            }
                            break # Para o loop interno
            
            if dados_encontrados:
                break # Para o loop externo

        if not dados_encontrados:
            return jsonify({
                "error": "Horário escolhido não encontrado na lista de horários disponíveis.",
                "detalhe": "Certifique-se que a variável 'horario_escolhido' contém a data (AAAA-MM-DD) e a hora (HH:MM) correspondente."
            }), 404

        # --- 4. RESPOSTA FINAL ---
        resposta = {
            "cpf_formatado": cpf_limpo
        }
        # Adiciona os dados encontrados (from, to, date) ao dicionário de resposta
        resposta.update(dados_encontrados)

        return jsonify(resposta)

    except Exception as e:
        print(f"Erro: {e}")
        return jsonify({"error": "Erro interno no processamento."}), 500

if __name__ == '__main__':
    # Pega a porta do ambiente (obrigatório para Railway) ou usa 3000 como padrão
    port = int(os.environ.get("PORT", 3000))
    app.run(host='0.0.0.0', port=port)
