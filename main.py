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
        
        # Pega os inputs
        cpf = data.get('cpf', '')
        horarios = data.get('horarios', []) 
        
        # Converte para string e remove espaços em branco das pontas
        raw_horario = data.get('horario_escolhido', '')
        horario_escolhido = str(raw_horario).strip()

        # --- 1. TRATAMENTO DO CPF ---
        cpf_limpo = re.sub(r'\D', '', str(cpf))

        # --- 2. SMART PARSER DE DATA (A SOLUÇÃO) ---
        dt_obj = None
        
        # Lista de formatos que vamos tentar aceitar
        formatos_aceitos = [
            "%d/%m/%Y %H:%M",       # 13/12/2025 10:00 (O ideal)
            "%d/%m/%Y %H:%M:%S",    # 13/12/2025 10:00:00 (Com segundos)
            "%Y-%m-%d %H:%M",       # 2025-12-13 10:00 (Formato ISO/Banco)
            "%Y-%m-%d %H:%M:%S",    # 2025-12-13 10:00:00
            "%Y-%m-%dT%H:%M:%S",    # ISO estrito com T
        ]

        for fmt in formatos_aceitos:
            try:
                dt_obj = datetime.strptime(horario_escolhido, fmt)
                break # Se funcionou, para de tentar
            except ValueError:
                continue # Se falhou, tenta o próximo

        # Se depois de tentar tudo, dt_obj ainda for None, retorna erro mostrando O QUE VEIO
        if dt_obj is None:
            return jsonify({
                "error": "Formato de data desconhecido.",
                "recebido": horario_escolhido, # <--- AQUI VAMOS DESCOBRIR A VERDADE
                "tipo_recebido": str(type(raw_horario)),
                "esperado": "DD/MM/AAAA HH:MM"
            }), 400

        # Se deu certo, padroniza para a busca
        target_date_iso = dt_obj.strftime("%Y-%m-%d") # "2025-12-13"
        target_time = dt_obj.strftime("%H:%M")        # "10:00"

        # --- 3. TRATAMENTO DOS HORÁRIOS ---
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
            data_do_json = dia.get('Date', '')

            # Se a data não bater, pula
            if data_do_json != target_date_iso:
                continue

            avaliable_times = dia.get('AvaliableTimes', [])
            
            for slot in avaliable_times:
                hora_slot_raw = slot.get('from', '')
                # Pega só os 5 primeiros caracteres (10:00)
                hora_slot_clean = hora_slot_raw[:5]

                if hora_slot_clean == target_time:
                    # Monta resposta
                    data_formatada_fixa = f"{data_do_json}T03:00:00.000Z"
                    
                    dados_encontrados = {
                        "from": slot.get('from')[:5], # Força 10:00
                        "to": slot.get('to')[:5],     # Força 11:00
                        "date": data_formatada_fixa
                    }
                    break 
            
            if dados_encontrados:
                break

        if not dados_encontrados:
            return jsonify({
                "error": "Horário não encontrado na grade.",
                "data_buscada": target_date_iso,
                "hora_buscada": target_time
            }), 404

        # --- 5. RESPOSTA FINAL ---
        resposta = {
            "cpf_formatado": cpf_limpo
        }
        resposta.update(dados_encontrados)

        return jsonify(resposta)

    except Exception as e:
        print(f"Erro CRÍTICO: {e}")
        return jsonify({"error": "Erro interno no servidor.", "log": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 3000))
    app.run(host='0.0.0.0', port=port)
