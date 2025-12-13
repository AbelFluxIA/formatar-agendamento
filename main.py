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
        horarios = data.get('horarios', []) # Default para lista vazia
        horario_escolhido = str(data.get('horario_escolhido', ''))

        # --- 1. TRATAMENTO DO CPF ---
        # Remove tudo que não for dígito
        cpf_limpo = re.sub(r'\D', '', str(cpf))

        # --- 2. TRATAMENTO DOS HORÁRIOS (FIXED) ---
        lista_dias = horarios

        # Se a automação enviar o JSON como string, fazemos o parse
        if isinstance(horarios, str):
            try:
                lista_dias = json.loads(horarios)
            except json.JSONDecodeError:
                return jsonify({"error": "O campo 'horarios' não é um JSON válido."}), 400

        # NORMALIZAÇÃO DA ESTRUTURA
        # O problema ocorria aqui. Agora tratamos Listas e Dicionários.
        schedules_para_processar = []

        if isinstance(lista_dias, list):
            # CASO 1: O input é uma lista direta (Seu caso atual)
            schedules_para_processar = lista_dias
        elif isinstance(lista_dias, dict) and 'schedules' in lista_dias:
            # CASO 2: O input é um objeto com a chave 'schedules' (Legado)
            schedules_para_processar = lista_dias['schedules']
        else:
            # Se não for nenhum dos dois, retorna erro
            return jsonify({"error": "Formato de horários inválido. Esperava uma lista ou objeto com 'schedules'."}), 400

        # --- 3. BUSCA DO HORÁRIO ESCOLHIDO ---
        dados_encontrados = None

        # Percorre a lista normalizada
        for dia in schedules_para_processar:
            avaliable_times = dia.get('AvaliableTimes', [])
            
            if avaliable_times:
                for slot in avaliable_times:
                    # LÓGICA DE COMPARAÇÃO:
                    # Verifica se a string "horario_escolhido" contém a Data e o horário de início
                    
                    data_no_slot = dia.get('Date', '') # ex: "2025-12-15"
                    hora_inicio_slot = slot.get('from', '') # ex: "14:00"

                    if data_no_slot and hora_inicio_slot:
                        # Validação robusta: garante que ambos estão na string de escolha
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
        # Log do erro real no console para debug
        print(f"Erro CRÍTICO no servidor: {e}")
        return jsonify({"error": "Erro interno no processamento."}), 500

if __name__ == '__main__':
    # Pega a porta do ambiente (obrigatório para Railway) ou usa 3000 como padrão
    port = int(os.environ.get("PORT", 3000))
    app.run(host='0.0.0.0', port=port)
