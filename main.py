from flask import Flask, request, jsonify
from datetime import datetime
import re
import json
import os

app = Flask(__name__)

@app.route('/formatar-agendamento', methods=['POST'])
def formatar_agendamento():
    try:
        data = request.get_json()
        
        cpf = data.get('cpf', '')
        horarios = data.get('horarios', []) 
        horario_escolhido = str(data.get('horario_escolhido', '')).strip() # Remove espaços extras

        # --- 1. TRATAMENTO DO CPF ---
        cpf_limpo = re.sub(r'\D', '', str(cpf))

        # --- 2. TRATAMENTO E PARSE DO INPUT "HORARIO_ESCOLHIDO" ---
        # Entrada esperada: "13/12/2025 10:00"
        # Precisamos separar data e hora e converter a data para YYYY-MM-DD para bater com o JSON
        
        target_date_iso = "" # Vai virar "2025-12-13"
        target_time = ""     # Vai virar "10:00"

        try:
            # Tenta fazer o parse da data brasileira
            dt_obj = datetime.strptime(horario_escolhido, "%d/%m/%Y %H:%M")
            target_date_iso = dt_obj.strftime("%Y-%m-%d") # Converte para 2025-12-13
            target_time = dt_obj.strftime("%H:%M")        # Garante 10:00
        except ValueError:
            # Se falhar o parse, retorna erro claro
            return jsonify({
                "error": "Formato de 'horario_escolhido' inválido.",
                "detalhe": "Envie no formato 'DD/MM/AAAA HH:MM' (ex: 13/12/2025 10:00)"
            }), 400

        # --- 3. NORMALIZAÇÃO DA ESTRUTURA DOS HORÁRIOS ---
        lista_dias = horarios
        if isinstance(horarios, str):
            try:
                lista_dias = json.loads(horarios)
            except json.JSONDecodeError:
                return jsonify({"error": "O campo 'horarios' não é um JSON válido."}), 400

        schedules_para_processar = []
        if isinstance(lista_dias, list):
            schedules_para_processar = lista_dias
        elif isinstance(lista_dias, dict) and 'schedules' in lista_dias:
            schedules_para_processar = lista_dias['schedules']
        else:
            return jsonify({"error": "Estrutura de horários inválida."}), 400

        # --- 4. BUSCA E FORMATAÇÃO ---
        dados_encontrados = None

        for dia in schedules_para_processar:
            # Pega a data do JSON (ex: "2025-12-13")
            data_do_json = dia.get('Date', '')

            # OTIMIZAÇÃO: Se a data do dia não for a data escolhida, nem olha os horários
            if data_do_json != target_date_iso:
                continue

            avaliable_times = dia.get('AvaliableTimes', [])
            
            for slot in avaliable_times:
                # Pega o horário de início do slot (ex: "10:00" ou "10:00:00")
                hora_slot_raw = slot.get('from', '')
                
                # Normaliza para comparar apenas os 5 primeiros caracteres (HH:MM)
                # Isso resolve problemas se o JSON vier "10:00:00"
                hora_slot_clean = hora_slot_raw[:5] 

                # COMPARAÇÃO EXATA
                if hora_slot_clean == target_time:
                    
                    # Monta a resposta exatamente como você pediu
                    # Data Fixa com T03...
                    data_formatada_fixa = f"{data_do_json}T03:00:00.000Z"
                    
                    # Garante output HH:MM cortando a string [:5]
                    hora_inicio_final = slot.get('from', '')[:5]
                    hora_fim_final = slot.get('to', '')[:5]

                    dados_encontrados = {
                        "from": hora_inicio_final, # Retorna ex: "10:00"
                        "to": hora_fim_final,      # Retorna ex: "11:00"
                        "date": data_formatada_fixa
                    }
                    break 
            
            if dados_encontrados:
                break

        if not dados_encontrados:
            return jsonify({
                "error": "Horário não encontrado.",
                "detalhe": f"Não encontramos o horário {target_time} na data {target_date_iso}."
            }), 404

        # --- 5. RESPOSTA FINAL ---
        resposta = {
            "cpf_formatado": cpf_limpo
        }
        resposta.update(dados_encontrados)

        return jsonify(resposta)

    except Exception as e:
        print(f"Erro CRÍTICO: {e}")
        return jsonify({"error": "Erro interno no processamento."}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 3000))
    app.run(host='0.0.0.0', port=port)
