from flask import Flask, request, jsonify
from datetime import datetime
import re
import json
import os

app = Flask(__name__)

# --- HELPER: DETECÇÃO DE GÊNERO EFICIENTE (VIBE CODING) ---
def estimar_genero(nome_completo):
    """
    Detecta F ou M baseado no primeiro nome.
    Otimizado para PT-BR com tratamento de exceções comuns.
    Custo computacional: O(1).
    """
    if not nome_completo or not isinstance(nome_completo, str):
        return "M" # Fallback padrão seguro

    # Pega o primeiro nome e normaliza
    primeiro_nome = nome_completo.strip().split(' ')[0].lower()
    
    # Exceções comuns no Brasil (Nomes femininos que NÃO terminam em 'a')
    excecoes_fem = {
        'beatriz', 'liz', 'thais', 'raquel', 'ester', 'simone', 'michelle', 
        'kelly', 'gaby', 'isabel', 'maite', 'nicole', 'alice', 'clarice', 
        'inês', 'luz', 'ingrid', 'miriam', 'rute', 'isis'
    }
    
    # Exceções comuns no Brasil (Nomes masculinos que terminam em 'a')
    excecoes_masc = {
        'luca', 'ubirajara', 'joshua', 'akira', 'mustafa', 'mika', 'sasha'
    }

    if primeiro_nome in excecoes_fem:
        return "F"
    if primeiro_nome in excecoes_masc:
        return "M"
    
    # Regra Geral: Terminou em 'a' é F, caso contrário M
    return "F" if primeiro_nome.endswith('a') else "M"


@app.route('/formatar-agendamento', methods=['POST'])
def formatar_agendamento():
    try:
        data = request.get_json()
        
        # Pega os inputs
        cpf = data.get('cpf', '')
        horarios = data.get('horarios', [])
        nome = data.get('nome', '') # <--- NOVO INPUT
        
        # Converte para string e remove espaços em branco das pontas
        raw_horario = data.get('horario_escolhido', '')
        horario_escolhido = str(raw_horario).strip()

        # --- 1. TRATAMENTO DO CPF ---
        cpf_limpo = re.sub(r'\D', '', str(cpf))

        # --- 2. SMART PARSER DE DATA ---
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
                break 
            except ValueError:
                continue 

        if dt_obj is None:
            return jsonify({
                "error": "Formato de data desconhecido.",
                "recebido": horario_escolhido,
                "tipo_recebido": str(type(raw_horario)),
                "esperado": "DD/MM/AAAA HH:MM"
            }), 400

        # Se deu certo, padroniza para a busca
        target_date_iso = dt_obj.strftime("%Y-%m-%d") 
        target_time = dt_obj.strftime("%H:%M")        

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

            if data_do_json != target_date_iso:
                continue

            avaliable_times = dia.get('AvaliableTimes', [])
            
            for slot in avaliable_times:
                hora_slot_raw = slot.get('from', '')
                hora_slot_clean = hora_slot_raw[:5]

                if hora_slot_clean == target_time:
                    data_formatada_fixa = f"{data_do_json}T03:00:00.000Z"
                    
                    dados_encontrados = {
                        "from": slot.get('from')[:5], 
                        "to": slot.get('to')[:5],     
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

        # --- 5. LÓGICA DE SEXO ---
        sexo_detectado = estimar_genero(nome) # <--- PROCESSAMENTO EFICIENTE

        # --- 6. RESPOSTA FINAL ---
        resposta = {
            "cpf_formatado": cpf_limpo,
            "sexo": sexo_detectado # <--- INSERÇÃO NA RESPOSTA
        }
        resposta.update(dados_encontrados)

        return jsonify(resposta)

    except Exception as e:
        print(f"Erro CRÍTICO: {e}")
        return jsonify({"error": "Erro interno no servidor.", "log": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 3000))
    app.run(host='0.0.0.0', port=port)
