from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import os
import autogen
from openai import OpenAI
import time
import threading
import random

# Cargar variables de entorno
load_dotenv()
DEEPINFRA_TOKEN = os.getenv("DEEPINFRA_TOKEN")

app = Flask(__name__)

# Configuración del cliente OpenAI con DeepInfra
openai_client = OpenAI(
    api_key=DEEPINFRA_TOKEN,
    base_url="https://api.deepinfra.com/v1/openai",
)

# Tipos de agentes con personalidades más detalladas y naturales
AGENT_TYPES = {
    "comedia": {
        "nombre": "Comediante",
        "descripcion": "Especialista en humor y chistes",
        "prompt": "Eres un comediante divertido y espontáneo. Usas humor inteligente, ocasionalmente sarcástico, y te encanta hacer juegos de palabras. Respondes con expresividad, incluyendo emojis ocasionales, y mantienes un tono alegre y desenfadado. Tus respuestas son breves (máximo 2-3 frases) y naturales, como en una conversación real por chat.",
        "avatar": "😂"
    },
    "investigacion": {
        "nombre": "Investigador",
        "descripcion": "Analítico y orientado a datos",
        "prompt": "Eres un investigador curioso y analítico. Te gusta compartir datos interesantes, pero de forma casual y accesible. Haces preguntas reflexivas y ofreces perspectivas basadas en evidencia. Tus respuestas son concisas (máximo 2-3 frases) y conversacionales, evitando lenguaje académico excesivo. Usas un tono informativo pero amigable.",
        "avatar": "🔍"
    },
    "amor": {
        "nombre": "Romántico",
        "descripcion": "Especialista en temas del corazón",
        "prompt": "Eres un consejero romántico empático y cálido. Hablas sobre relaciones y emociones con sensibilidad y ocasionalmente usas metáforas sobre el amor. Tu estilo es cercano y comprensivo, con respuestas breves (2-3 frases máximo) que fluyen naturalmente. Ocasionalmente usas emojis de corazón y expresas emoción en tus mensajes.",
        "avatar": "❤️"
    },
    "filosofia": {
        "nombre": "Filósofo",
        "descripcion": "Reflexivo y contemplativo",
        "prompt": "Eres un filósofo accesible y contemplativo. Planteas preguntas sobre la existencia y significado de forma conversacional, no académica. Usas ejemplos cotidianos para ilustrar ideas profundas y ocasionalmente citas breves. Tus respuestas son cortas (2-3 frases) y fluidas, como en una conversación casual entre amigos reflexivos.",
        "avatar": "🧠"
    },
    "tecnologia": {
        "nombre": "Tecnólogo",
        "descripcion": "Apasionado por la innovación",
        "prompt": "Eres un entusiasta de la tecnología accesible y conversacional. Explicas conceptos técnicos de forma sencilla y práctica. Muestras emoción por innovaciones y tendencias digitales. Tus respuestas son breves (máximo 2-3 frases), directas y coloquiales, similares a una conversación por chat entre amigos tech. Ocasionalmente usas emojis relacionados con tecnología.",
        "avatar": "💻"
    },
    "viajero": {
        "nombre": "Viajero",
        "descripcion": "Explorador de culturas y lugares",
        "prompt": "Eres un viajero aventurero y cultural. Compartes experiencias de viaje, curiosidades culturales y recomendaciones con entusiasmo. Tu estilo es vivaz y expresivo, usando ocasionalmente palabras extranjeras. Tus mensajes son breves (2-3 frases) y espontáneos, como si estuvieras enviando mensajes desde un café en algún lugar exótico.",
        "avatar": "✈️"
    },
    "poeta": {
        "nombre": "Poeta",
        "descripcion": "Artista de las palabras",
        "prompt": "Eres un poeta contemporáneo y accesible. Tu lenguaje es ligeramente metafórico y evocador, pero siempre claro y conversacional. Expresas aprecio por la belleza y las emociones humanas. Tus respuestas son breves (2-3 frases), fluidas y naturales, como una conversación entre amigos artísticos, ocasionalmente inspiradas por lo cotidiano.",
        "avatar": "🖋️"
    }
}

# Almacén de conversaciones activas
active_conversations = {}

# Frases para transiciones naturales y respuestas variadas
TRANSICIONES = [
    "Mmm, interesante punto. ",
    "Buena observación. ",
    "Eso me hace pensar en... ",
    "Vaya, nunca lo había visto así. ",
    "Ya veo lo que dices. ",
    "Entiendo tu perspectiva. ",
    "Eso es fascinante. ",
    "Me gusta cómo piensas. ",
    "Ahora que lo mencionas... ",
    "",  # A veces sin transición para variar
]

def create_agent_with_autogen(agent_type, name):
    """Crea un agente usando AutoGen con la personalidad especificada"""
    # Configuración para DeepInfra
    config_list = [
        {
            "model": "mistralai/Mistral-Small-24B-Instruct-2501",
            "api_key": DEEPINFRA_TOKEN,
            "base_url": "https://api.deepinfra.com/v1/openai",
        }
    ]
    
    # Convertir la lista de configuración en el formato que espera AutoGen
    llm_config = {
        "config_list": config_list,
        "temperature": 0.8,  # Mayor temperatura para respuestas más variadas
    }
    
    # Personalidad basada en el tipo de agente
    system_message = AGENT_TYPES[agent_type]["prompt"]
    
    # Crear el agente con AutoGen, desactivando Docker
    agent = autogen.AssistantAgent(
        name=name,
        system_message=system_message,
        llm_config=llm_config,
        code_execution_config={"use_docker": False}  # Desactivar Docker
    )
    
    return agent

@app.route('/')
def index():
    return render_template('index.html', agent_types=AGENT_TYPES)

@app.route('/iniciar_conversacion', methods=['POST'])
def iniciar_conversacion():
    data = request.json
    agent1_type = data.get('agent1_type')
    agent2_type = data.get('agent2_type')
    tema = data.get('tema', 'Habla sobre un tema que te parezca interesante')
    
    # Verificar que los tipos de agentes existen
    if agent1_type not in AGENT_TYPES or agent2_type not in AGENT_TYPES:
        return jsonify({'error': 'Tipo de agente no válido'}), 400
    
    # Crear ID para esta conversación
    conversation_id = f"{agent1_type}_{agent2_type}_{int(time.time())}"
    
    # Nombres de los agentes
    agent1_name = AGENT_TYPES[agent1_type]['nombre']
    agent2_name = AGENT_TYPES[agent2_type]['nombre']
    
    try:
        # Crear los agentes con AutoGen
        agent1 = create_agent_with_autogen(agent1_type, agent1_name)
        agent2 = create_agent_with_autogen(agent2_type, agent2_name)
        
        # Crear un usuario proxy para iniciar la conversación
        user_proxy = autogen.UserProxyAgent(
            name="user_proxy",
            human_input_mode="NEVER",
            max_consecutive_auto_reply=0,
            code_execution_config={"use_docker": False}  # Desactivar Docker
        )
        
        # Almacenar los agentes y estado en la conversación activa
        active_conversations[conversation_id] = {
            "agent1": agent1,
            "agent2": agent2,
            "user_proxy": user_proxy,
            "messages": [],
            "ultimo_hablante": None,
            "agent1_type": agent1_type,
            "agent2_type": agent2_type,
            "agent1_name": agent1_name,
            "agent2_name": agent2_name,
            "last_activity": time.time(),
            "cancelada": False,
            "agent1_ha_hablado": True,  # El agente1 inicia la conversación, así que marcamos como ya hablado
            "agent2_ha_hablado": False  # El agente2 aún no ha hablado
        }
        
        # Generar el primer mensaje con un saludo
        mensaje_inicial = f"""Inicia una conversación sobre: {tema}. 
        Como es tu primer mensaje, puedes saludar brevemente e introducir el tema.
        Sé breve (máximo 2-3 frases) y conversacional, como en un chat real."""
        
        # Verificar si la conversación ha sido cancelada
        if active_conversations[conversation_id].get('cancelada', False):
            return jsonify({'error': 'Conversación cancelada'}), 400
            
        response = openai_client.chat.completions.create(
            model="mistralai/Mistral-Small-24B-Instruct-2501",
            messages=[
                {"role": "system", "content": AGENT_TYPES[agent1_type]['prompt']},
                {"role": "user", "content": mensaje_inicial}
            ],
            max_tokens=100
        )
        
        primer_mensaje = {
            "role": "agent1",
            "content": response.choices[0].message.content,
            "agent_name": agent1_name,
            "avatar": AGENT_TYPES[agent1_type]['avatar']
        }
        
        active_conversations[conversation_id]["messages"].append(primer_mensaje)
        active_conversations[conversation_id]["ultimo_hablante"] = "agent1"
        
        return jsonify({
            'conversation_id': conversation_id,
            'messages': [primer_mensaje],
            'agent1_name': agent1_name,
            'agent2_name': agent2_name,
            'agent1_type': agent1_type,
            'agent2_type': agent2_type,
            'agent1_avatar': AGENT_TYPES[agent1_type]['avatar'],
            'agent2_avatar': AGENT_TYPES[agent2_type]['avatar']
        })
    
    except Exception as e:
        print(f"Error en iniciar_conversacion: {str(e)}")
        
        # Método de respaldo usando OpenAI directamente
        response = openai_client.chat.completions.create(
            model="mistralai/Mistral-Small-24B-Instruct-2501",
            messages=[
                {"role": "system", "content": AGENT_TYPES[agent1_type]['prompt']},
                {"role": "user", "content": f"Inicia una conversación sobre: {tema}. Puedes saludar brevemente. Sé breve y natural."}
            ],
            max_tokens=100
        )
        
        primer_mensaje = {
            "role": "agent1",
            "content": response.choices[0].message.content,
            "agent_name": agent1_name,
            "avatar": AGENT_TYPES[agent1_type]['avatar']
        }
        
        # Crear la conversación con método básico sin AutoGen
        active_conversations[conversation_id] = {
            "messages": [primer_mensaje],
            "ultimo_hablante": "agent1",
            "agent1_type": agent1_type,
            "agent2_type": agent2_type,
            "agent1_name": agent1_name,
            "agent2_name": agent2_name,
            "last_activity": time.time(),
            "using_fallback": True,  # Marcar que estamos usando el método de respaldo
            "cancelada": False,
            "agent1_ha_hablado": True,
            "agent2_ha_hablado": False
        }
        
        return jsonify({
            'conversation_id': conversation_id,
            'messages': [primer_mensaje],
            'agent1_name': agent1_name,
            'agent2_name': agent2_name,
            'agent1_type': agent1_type,
            'agent2_type': agent2_type,
            'agent1_avatar': AGENT_TYPES[agent1_type]['avatar'],
            'agent2_avatar': AGENT_TYPES[agent2_type]['avatar']
        })

@app.route('/continuar_conversacion', methods=['POST'])
def continuar_conversacion():
    data = request.json
    conversation_id = data.get('conversation_id')
    
    if conversation_id not in active_conversations:
        return jsonify({'error': 'Conversación no encontrada'}), 404
    
    # Verificar si la conversación ha sido cancelada
    if active_conversations[conversation_id].get('cancelada', False):
        return jsonify({'error': 'Conversación cancelada'}), 400
    
    # Actualizar timestamp de actividad
    active_conversations[conversation_id]["last_activity"] = time.time()
    
    # Obtener información de la conversación
    conv_data = active_conversations[conversation_id]
    ultimo_hablante = conv_data["ultimo_hablante"]
    mensajes = conv_data["messages"]
    
    # Determinar quién habla ahora
    if ultimo_hablante == "agent1":
        current_speaker_role = "agent2"
        other_speaker_role = "agent1"
        current_speaker_type = conv_data["agent2_type"]
        current_speaker_name = conv_data["agent2_name"]
        current_speaker_avatar = AGENT_TYPES[current_speaker_type]['avatar']
        other_speaker_name = conv_data["agent1_name"]
        is_first_message = not conv_data.get("agent2_ha_hablado", False)
    else:
        current_speaker_role = "agent1"
        other_speaker_role = "agent2"
        current_speaker_type = conv_data["agent1_type"]
        current_speaker_name = conv_data["agent1_name"]
        current_speaker_avatar = AGENT_TYPES[current_speaker_type]['avatar']
        other_speaker_name = conv_data["agent2_name"]
        is_first_message = not conv_data.get("agent1_ha_hablado", True)  # agent1 ya habló en el primer mensaje
    
    try:
        # Construir un formato de conversación claro
        transcript = "HISTORIAL DE CONVERSACIÓN HASTA AHORA:\n\n"
        
        # Añadir todos los mensajes previos como un guion/transcript
        for idx, msg in enumerate(mensajes):
            speaker = conv_data["agent1_name"] if msg["role"] == "agent1" else conv_data["agent2_name"]
            transcript += f"{speaker}: {msg['content']}\n\n"
        
        # Instrucciones adaptadas según si es el primer mensaje o no
        if is_first_message:
            system_instructions = f"""
{AGENT_TYPES[current_speaker_type]['prompt']}

INSTRUCCIONES:
1. Este es tu PRIMER mensaje en esta conversación con {other_speaker_name}.
2. Puedes saludar brevemente y presentarte si lo deseas.
3. Responde al tema o punto planteado por {other_speaker_name}.
4. SÉ BREVE - máximo 2-3 frases cortas.
5. MANTÉN tu personalidad definida.

Estás conversando con {other_speaker_name}.
"""
            user_instruction = f"\nEs tu primer mensaje como {current_speaker_name}. Puedes saludar brevemente y luego responder al comentario de {other_speaker_name}."
        else:
            system_instructions = f"""
{AGENT_TYPES[current_speaker_type]['prompt']}

INSTRUCCIONES:
1. NO SALUDES - Ya has saludado anteriormente.
2. NO PREGUNTES "¿Cómo estás?" o similares - La conversación ya está en curso.
3. NO REPITAS ideas o temas ya mencionados.
4. CONTINÚA la conversación naturalmente desde donde quedó.
5. SÉ BREVE - máximo 2-3 frases cortas.
6. MANTÉN tu personalidad, pero no la menciones explícitamente.

Estás conversando con {other_speaker_name}.
"""
            user_instruction = f"\nContinúa la conversación como {current_speaker_name}. Responde directamente al último comentario de {other_speaker_name} sin saludar nuevamente."

        # Verificar si la conversación ha sido cancelada
        if active_conversations[conversation_id].get('cancelada', False):
            return jsonify({'error': 'Conversación cancelada'}), 400
            
        # Obtener respuesta con el formato apropiado según si es primer mensaje o no
        response = openai_client.chat.completions.create(
            model="mistralai/Mistral-Small-24B-Instruct-2501",
            messages=[
                {"role": "system", "content": system_instructions},
                {"role": "user", "content": transcript + user_instruction}
            ],
            max_tokens=100,
            temperature=0.75
        )
        
        nuevo_contenido = response.choices[0].message.content
        
        # Limpiar cualquier formato no deseado o prefijos
        for prefix in [f"{current_speaker_name}:", "Yo:", f"{current_speaker_role}:", "Respuesta:", "R:"]:
            if nuevo_contenido.startswith(prefix):
                nuevo_contenido = nuevo_contenido[len(prefix):].strip()
                break
        
        # Limpiar saludos repetidos si NO es el primer mensaje
        if not is_first_message:
            saludos = ["Hola", "Saludos", "Buenos días", "Buenas tardes", "Buenas noches", "Hey", "Hi", "Hello"]
            for saludo in saludos:
                if nuevo_contenido.startswith(saludo):
                    # Eliminar el saludo y cualquier carácter siguiente (espacio, puntuación)
                    idx = len(saludo)
                    while idx < len(nuevo_contenido) and (nuevo_contenido[idx].isspace() or nuevo_contenido[idx] in ",.!"):
                        idx += 1
                    nuevo_contenido = nuevo_contenido[idx:].strip()
                    if nuevo_contenido and nuevo_contenido[0].islower():
                        nuevo_contenido = nuevo_contenido[0].upper() + nuevo_contenido[1:]
                    break
        
        # Crear el nuevo mensaje
        nuevo_mensaje = {
            'role': current_speaker_role,
            'content': nuevo_contenido,
            'agent_name': current_speaker_name,
            'avatar': current_speaker_avatar
        }
        
        # Verificar si la conversación ha sido cancelada antes de guardar
        if not active_conversations[conversation_id].get('cancelada', False):
            # Actualizar que el agente ha hablado
            if current_speaker_role == "agent1":
                conv_data["agent1_ha_hablado"] = True
            else:
                conv_data["agent2_ha_hablado"] = True
                
            # Añadir el mensaje a la conversación
            conv_data["messages"].append(nuevo_mensaje)
            conv_data["ultimo_hablante"] = current_speaker_role
        
        return jsonify(nuevo_mensaje)
    
    except Exception as e:
        print(f"Error en continuar_conversacion: {str(e)}")
        
        # Método de respaldo también mejorado
        try:
            # Instrucciones según si es primer mensaje o no
            if is_first_message:
                system_fallback = f"{AGENT_TYPES[current_speaker_type]['prompt']}\n\nEste es tu primer mensaje, puedes saludar brevemente."
                prompt_instruction = f"{other_speaker_name} dijo: {mensajes[-1]['content']}\n\nResponde como {current_speaker_name}. Puedes saludar brevemente ya que es tu primer mensaje."
            else:
                system_fallback = f"{AGENT_TYPES[current_speaker_type]['prompt']}\n\nNO SALUDES NUEVAMENTE. Continúa la conversación directamente."
                prompt_instruction = f"{other_speaker_name} dijo: {mensajes[-1]['content']}\n\nResponde como {current_speaker_name} sin saludar otra vez."
            
            response = openai_client.chat.completions.create(
                model="mistralai/Mistral-Small-24B-Instruct-2501",
                messages=[
                    {"role": "system", "content": system_fallback},
                    {"role": "user", "content": prompt_instruction}
                ],
                max_tokens=100,
                temperature=0.7
            )
            
            nuevo_contenido = response.choices[0].message.content
            
            # Limpiar prefijos
            for prefix in [f"{current_speaker_name}:", "Yo:", f"{current_speaker_role}:", "Respuesta:", "R:"]:
                if nuevo_contenido.startswith(prefix):
                    nuevo_contenido = nuevo_contenido[len(prefix):].strip()
                    break
            
            # Limpiar saludos solo si NO es el primer mensaje
            if not is_first_message:
                saludos = ["Hola", "Saludos", "Buenos días", "Buenas tardes", "Buenas noches", "Hey", "Hi", "Hello"]
                for saludo in saludos:
                    if nuevo_contenido.startswith(saludo):
                        idx = len(saludo)
                        while idx < len(nuevo_contenido) and (nuevo_contenido[idx].isspace() or nuevo_contenido[idx] in ",.!"):
                            idx += 1
                        nuevo_contenido = nuevo_contenido[idx:].strip()
                        if nuevo_contenido and nuevo_contenido[0].islower():
                            nuevo_contenido = nuevo_contenido[0].upper() + nuevo_contenido[1:]
                        break
            
            # Crear el nuevo mensaje
            nuevo_mensaje = {
                'role': current_speaker_role,
                'content': nuevo_contenido,
                'agent_name': current_speaker_name,
                'avatar': current_speaker_avatar
            }
            
            # Añadir el mensaje a la conversación solo si no está cancelada
            if not active_conversations[conversation_id].get('cancelada', False):
                # Actualizar que el agente ha hablado
                if current_speaker_role == "agent1":
                    conv_data["agent1_ha_hablado"] = True
                else:
                    conv_data["agent2_ha_hablado"] = True
                    
                conv_data["messages"].append(nuevo_mensaje)
                conv_data["ultimo_hablante"] = current_speaker_role
            
            return jsonify(nuevo_mensaje)
        
        except Exception as backup_error:
            print(f"Error en respaldo de continuar_conversación: {str(backup_error)}")
            
            # Mensaje genérico de respaldo que continúa la conversación
            mensaje_respaldo = "Interesante punto. Me gustaría saber más sobre tu perspectiva en esto."
            if is_first_message:
                mensaje_respaldo = f"¡Hola! {mensaje_respaldo}"
                
            return jsonify({
                'role': current_speaker_role,
                'content': mensaje_respaldo,
                'agent_name': current_speaker_name,
                'avatar': current_speaker_avatar
            })
        
@app.route('/cancelar_solicitud', methods=['POST'])
def cancelar_solicitud():
    """Cancela cualquier solicitud en curso para una conversación específica"""
    data = request.json
    conversation_id = data.get('conversation_id')
    
    if conversation_id in active_conversations:
        # Marcar la conversación como cancelada
        active_conversations[conversation_id]['cancelada'] = True
        print(f"Conversación {conversation_id} marcada como cancelada")
    
    return jsonify({'success': True})

@app.route('/descargar_conversacion', methods=['POST'])
def descargar_conversacion():
    data = request.json
    conversation_id = data.get('conversation_id')
    
    if conversation_id not in active_conversations:
        return jsonify({'error': 'Conversación no encontrada'}), 404
    
    # Obtener mensajes de la conversación
    conv_data = active_conversations[conversation_id]
    mensajes = conv_data["messages"]
    
    # Formatear la conversación para descargar
    texto_conversacion = f"Conversación entre {conv_data['agent1_name']} y {conv_data['agent2_name']}\n\n"
    
    for msg in mensajes:
        texto_conversacion += f"{msg['agent_name']}: {msg['content']}\n\n"
    
    return jsonify({'texto': texto_conversacion})

# Limpiar conversaciones antiguas periódicamente
@app.before_request
def check_first_request():
    if not hasattr(app, '_got_first_request'):
        app._got_first_request = True
        
        def clean_old_conversations():
            while True:
                current_time = time.time()
                to_remove = []
                
                for conv_id, conv_data in active_conversations.items():
                    # Eliminar conversaciones de más de 1 hora o marcadas como canceladas
                    if (conv_data.get("last_activity", current_time) + 3600 < current_time or 
                        conv_data.get("cancelada", False)):
                        to_remove.append(conv_id)
                
                for conv_id in to_remove:
                    try:
                        del active_conversations[conv_id]
                        print(f"Conversación {conv_id} eliminada")
                    except:
                        pass
                
                time.sleep(1800)  # Revisar cada 30 minutos
        
        # Iniciar hilo de limpieza
        t = threading.Thread(target=clean_old_conversations)
        t.daemon = True
        t.start()

if __name__ == '__main__':
    app.run(debug=True)