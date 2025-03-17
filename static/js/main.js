document.addEventListener('DOMContentLoaded', function() {
    // Estado de la aplicación
    const state = {
        agent1: null,
        agent2: null,
        mensajes: [],
        ultimoHablante: null,
        agent1Name: '',
        agent2Name: '',
        agent1Avatar: '',
        agent2Avatar: '',
        isTyping: false,
        conversationId: null,
        soundEnabled: true,
        currentRequest: null, // Para almacenar la solicitud actual que podría necesitar cancelarse
        typingSoundPlaying: false
    };
    
    // Elementos del DOM
    const setupPanel = document.getElementById('setup-panel');
    const chatContainer = document.getElementById('chat-container');
    const chatMessages = document.getElementById('chat-messages');
    const startBtn = document.getElementById('start-btn');
    const continueBtn = document.getElementById('continue-btn');
    const resetBtn = document.getElementById('reset-btn');
    const backBtn = document.getElementById('back-btn');
    const chatTitle = document.getElementById('chat-title');
    const temaInput = document.getElementById('tema-input');
    const soundToggleBtn = document.querySelector('.sound-toggle');
    
    // Sonidos con volumen reducido
    const messageSound = new Audio('/static/sounds/message.mp3');
    messageSound.volume = 0.3; // Reducir volumen al 30%
    
    const typingSound = new Audio('/static/sounds/typing.mp3');
    typingSound.volume = 0.2; // Reducir volumen al 20%
    typingSound.loop = true; // Hacer que se repita mientras escribe
    
    // Añadir botón de descarga a los controles del chat
    const chatControls = document.querySelector('.chat-controls');
    const downloadBtn = document.createElement('button');
    downloadBtn.id = 'download-btn';
    downloadBtn.className = 'download-btn';
    downloadBtn.innerHTML = '<i class="fas fa-download"></i> Descargar';
    chatControls.appendChild(downloadBtn);
    
    // Configuración del botón de sonido
    if (soundToggleBtn) {
        soundToggleBtn.addEventListener('click', function() {
            state.soundEnabled = !state.soundEnabled;
            
            // Actualizar icono según estado
            this.innerHTML = state.soundEnabled 
                ? '<i class="fas fa-volume-up"></i>' 
                : '<i class="fas fa-volume-mute"></i>';
            
            // Detener todos los sonidos si se desactiva
            if (!state.soundEnabled) {
                messageSound.pause();
                messageSound.currentTime = 0;
                typingSound.pause();
                typingSound.currentTime = 0;
            }
            
            showNotification(state.soundEnabled ? 'Sonido activado' : 'Sonido desactivado');
        });
    }
    
    // Función para seleccionar un agente - CORREGIDA
    window.selectAgent = function(position, type) {
        // Determinar qué columna corresponde a qué agente (solución del problema)
        const column = document.querySelector(position === 'agent1' ? 
                       '.agent-column:first-child' : 
                       '.agent-column:last-child');
        
        if (!column) return;
        
        // Remover selección previa en la columna correcta
        column.querySelectorAll('.agent-option.selected').forEach(el => {
            el.classList.remove('selected');
        });
        
        // Añadir selección nueva en la columna correcta
        const selectedOption = column.querySelector(`.agent-option[data-type="${type}"]`);
        if (selectedOption) {
            selectedOption.classList.add('selected');
        }
        
        // Actualizar estado
        state[position] = type;
        
        // Habilitar botón si ambos agentes están seleccionados
        startBtn.disabled = !(state.agent1 && state.agent2);
        
        // Mostrar feedback visual de selección
        if (state[position]) {
            showNotification(`${position === 'agent1' ? 'Agente 1' : 'Agente 2'} seleccionado: ${selectedOption.querySelector('.agent-name').textContent}`);
        }
    };
    
    // Iniciar conversación
    startBtn.addEventListener('click', function() {
        if (!state.agent1 || !state.agent2) return;
        
        // Limpiar mensajes anteriores y reiniciar estado
        chatMessages.innerHTML = '';
        state.mensajes = [];
        state.ultimoHablante = null;
        state.conversationId = null;
        
        // Mostrar indicador de carga
        setupPanel.classList.add('hidden');
        chatContainer.classList.remove('hidden');
        chatTitle.textContent = 'Cargando conversación...';
        
        // Mostrar que está escribiendo...
        showTypingIndicator('agent1');
        
        // Reproducir sonido de escritura
        if (state.soundEnabled) {
            playTypingSound();
        }
        
        // Llamar al backend para iniciar la conversación
        state.currentRequest = fetch('/iniciar_conversacion', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                agent1_type: state.agent1,
                agent2_type: state.agent2,
                tema: temaInput.value.trim() || undefined
            }),
        })
        .then(response => response.json())
        .then(data => {
            // Guardar datos de la conversación
            state.mensajes = data.messages;
            state.agent1Name = data.agent1_name;
            state.agent2Name = data.agent2_name;
            state.agent1 = data.agent1_type;
            state.agent2 = data.agent2_type;
            state.agent1Avatar = data.agent1_avatar;
            state.agent2Avatar = data.agent2_avatar;
            state.ultimoHablante = 'agent1';
            state.conversationId = data.conversation_id;
            
            // Detener sonido de escritura
            stopTypingSound();
            
            // Remover indicador de escritura
            removeTypingIndicator();
            
            // Actualizar título
            chatTitle.textContent = `${state.agent1Name} vs ${state.agent2Name}`;
            
            // Mostrar mensajes con efecto de escritura
            displayMessages();
            
            // Limpiar la request actual
            state.currentRequest = null;
            
            // Mostrar notificación de éxito
            showNotification('Conversación iniciada correctamente');
        })
        .catch(error => {
            // Solo mostrar error si no fue cancelado a propósito
            if (error.name !== 'AbortError') {
                console.error('Error al iniciar conversación:', error);
                chatTitle.textContent = 'Error al cargar la conversación';
                showNotification('Error al iniciar la conversación', true);
            }
            
            // Detener sonido de escritura
            stopTypingSound();
            
            // Remover indicador de escritura
            removeTypingIndicator();
            
            // Limpiar la request actual
            state.currentRequest = null;
        });
    });
    
    // Continuar conversación
    continueBtn.addEventListener('click', function() {
        if (state.isTyping) return; // Evitar múltiples clics durante la escritura
        
        const agentType = state.ultimoHablante === 'agent1' ? 'agent2' : 'agent1';
        state.isTyping = true;
        
        // Mostrar indicador de escritura
        showTypingIndicator(agentType);
        
        // Reproducir sonido de escritura
        if (state.soundEnabled) {
            playTypingSound();
        }
        
        // Llamar al backend para continuar la conversación
        state.currentRequest = fetch('/continuar_conversacion', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                conversation_id: state.conversationId,
                ultimo_hablante: state.ultimoHablante
            }),
        })
        .then(response => response.json())
        .then(data => {
            // Remover indicador de escritura
            removeTypingIndicator();
            
            // Detener sonido de escritura
            stopTypingSound();
            
            // Agregar mensaje a la lista
            state.mensajes.push(data);
            state.ultimoHablante = data.role;
            
            // Mostrar el nuevo mensaje con efecto de escritura
            displayMessage(data);
            
            state.isTyping = false;
            state.currentRequest = null;
        })
        .catch(error => {
            // Solo mostrar error si no fue cancelado a propósito
            if (error.name !== 'AbortError') {
                console.error('Error al continuar conversación:', error);
                showNotification('Error al continuar la conversación', true);
            }
            
            // Detener sonido de escritura
            stopTypingSound();
            
            // Remover indicador de escritura
            removeTypingIndicator();
            
            state.isTyping = false;
            state.currentRequest = null;
        });
    });
    
    // Resetear conversación
    resetBtn.addEventListener('click', function() {
        // Cancelar cualquier solicitud en curso
        cancelCurrentRequest();
        
        // Detener sonidos
        stopTypingSound();
        
        // Limpiar chat
        chatContainer.classList.add('hidden');
        setupPanel.classList.remove('hidden');
        chatMessages.innerHTML = '';
        
        // Reiniciar estado
        state.mensajes = [];
        state.ultimoHablante = null;
        state.conversationId = null;
        state.isTyping = false;
    });
    
    // Botón de regreso
    backBtn.addEventListener('click', function() {
        // Cancelar cualquier solicitud en curso
        cancelCurrentRequest();
        
        // Detener sonidos
        stopTypingSound();
        
        // Ocultar chat y mostrar setup
        chatContainer.classList.add('hidden');
        setupPanel.classList.remove('hidden');
        
        // Mantener estado para poder volver a la conversación
    });
    
    // Botón de descarga
    downloadBtn.addEventListener('click', function() {
        if (!state.conversationId) return;
        
        fetch('/descargar_conversacion', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                conversation_id: state.conversationId
            }),
        })
        .then(response => response.json())
        .then(data => {
            // Crear un enlace temporal para descargar el texto
            const element = document.createElement('a');
            const file = new Blob([data.texto], {type: 'text/plain'});
            element.href = URL.createObjectURL(file);
            element.download = `Conversacion_${state.agent1Name}_${state.agent2Name}.txt`;
            
            // Simular clic para descargar
            document.body.appendChild(element);
            element.click();
            document.body.removeChild(element);
            
            showNotification('Conversación descargada');
        })
        .catch(error => {
            console.error('Error al descargar conversación:', error);
            showNotification('Error al descargar la conversación', true);
        });
    });
    
    // Mostrar todos los mensajes en el chat
    function displayMessages() {
        chatMessages.innerHTML = '';
        state.mensajes.forEach(message => {
            displayMessage(message);
        });
    }
    
    // Mostrar un mensaje individual con efecto de escritura
    function displayMessage(message) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${message.role}`;
        
        // Agregar nombre del agente con avatar
        const nameSpan = document.createElement('div');
        nameSpan.className = 'agent-name';
        
        // Añadir avatar
        const avatarSpan = document.createElement('span');
        avatarSpan.className = 'avatar';
        avatarSpan.textContent = message.role === 'agent1' ? state.agent1Avatar : state.agent2Avatar;
        nameSpan.appendChild(avatarSpan);
        
        // Añadir nombre
        const nameText = document.createTextNode(message.agent_name);
        nameSpan.appendChild(nameText);
        
        messageDiv.appendChild(nameSpan);
        
        // Contenedor para el texto del mensaje
        const textDiv = document.createElement('div');
        textDiv.className = 'message-text';
        messageDiv.appendChild(textDiv);
        
        // Agregar hora
        const now = new Date();
        const timeStr = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;
        messageDiv.setAttribute('data-time', timeStr);
        
        // Añadir mensaje al chat
        chatMessages.appendChild(messageDiv);
        
        // Reproducir sonido al mostrar el mensaje
        if (state.soundEnabled) {
            messageSound.play();
        }
        
        // Scroll al final
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        // Efecto de escritura gradual
        const text = message.content;
        let index = 0;
        
        function typeNextChar() {
            if (index < text.length) {
                const char = document.createElement('span');
                char.className = 'char';
                char.textContent = text[index];
                textDiv.appendChild(char);
                
                index++;
                
                // Velocidad variable para efecto más natural de WhatsApp
                // Pausa en puntuación y final de palabras, más rápido en medio de palabras
                const isPunctuation = ['.', ',', '!', '?', ';', ':'].includes(text[index - 1]);
                const isEndOfWord = text[index] === ' ' || index === text.length;
                
                let delay;
                if (isPunctuation) {
                    delay = Math.random() * 300 + 200; // Pausa larga tras puntuación (200-500ms)
                } else if (isEndOfWord) {
                    delay = Math.random() * 100 + 50;  // Pausa media al final de palabras (50-150ms)
                } else {
                    delay = Math.random() * 20 + 10;   // Pausa corta entre letras (10-30ms)
                }
                
                setTimeout(typeNextChar, delay);
                
                // Scroll mientras escribe
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }
        }
        
        // Comenzar a escribir con un pequeño retraso inicial para que se muestren los tres puntos
        setTimeout(typeNextChar, 800);
    }
    
    // Mostrar indicador de escritura
    function showTypingIndicator(agentType) {
        // Remover indicador previo si existe
        removeTypingIndicator();
        
        const indicator = document.createElement('div');
        indicator.className = `typing-indicator ${agentType}`;
        indicator.id = 'typing-indicator';
        
        for (let i = 0; i < 3; i++) {
            const dot = document.createElement('div');
            dot.className = 'typing-dot';
            indicator.appendChild(dot);
        }
        
        chatMessages.appendChild(indicator);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    // Remover indicador de escritura
    function removeTypingIndicator() {
        const indicator = document.getElementById('typing-indicator');
        if (indicator) {
            indicator.remove();
        }
    }
    
    // Reproducir sonido de escritura
    function playTypingSound() {
        if (!state.typingSoundPlaying && state.soundEnabled) {
            typingSound.currentTime = 0;
            typingSound.play();
            state.typingSoundPlaying = true;
        }
    }
    
    // Detener sonido de escritura
    function stopTypingSound() {
        if (state.typingSoundPlaying) {
            typingSound.pause();
            typingSound.currentTime = 0;
            state.typingSoundPlaying = false;
        }
    }
    
    // Cancelar solicitud en curso
    function cancelCurrentRequest() {
        if (state.currentRequest && state.currentRequest.abort) {
            try {
                state.currentRequest.abort();
            } catch (e) {
                console.log('No se pudo cancelar la solicitud');
            }
        }
        state.currentRequest = null;
    }
    
    // Mostrar notificación
    function showNotification(message, isError = false) {
        // Crear elemento de notificación
        const notification = document.createElement('div');
        notification.className = 'notification';
        notification.textContent = message;
        
        if (isError) {
            notification.style.backgroundColor = '#f44336';
        }
        
        document.body.appendChild(notification);
        
        // Mostrar con animación
        setTimeout(() => {
            notification.classList.add('show');
        }, 10);
        
        // Ocultar después de 3 segundos
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => {
                notification.remove();
            }, 300);
        }, 3000);
    }
    
    // Detectar cuando el usuario hace scroll para mostrar el botón de "ir abajo"
    chatMessages.addEventListener('scroll', function() {
        const scrollBottom = chatMessages.scrollHeight - chatMessages.clientHeight - chatMessages.scrollTop;
        if (scrollBottom > 100) {
            // Si estamos lejos del fondo, mostrar un botón para ir abajo
            if (!document.getElementById('scroll-bottom-btn')) {
                const scrollBtn = document.createElement('div');
                scrollBtn.id = 'scroll-bottom-btn';
                scrollBtn.innerHTML = '⬇️';
                scrollBtn.style.position = 'absolute';
                scrollBtn.style.bottom = '80px';
                scrollBtn.style.right = '20px';
                scrollBtn.style.backgroundColor = 'var(--accent-color)';
                scrollBtn.style.color = 'white';
                scrollBtn.style.width = '40px';
                scrollBtn.style.height = '40px';
                scrollBtn.style.borderRadius = '50%';
                scrollBtn.style.display = 'flex';
                scrollBtn.style.justifyContent = 'center';
                scrollBtn.style.alignItems = 'center';
                scrollBtn.style.cursor = 'pointer';
                scrollBtn.style.boxShadow = '0 2px 5px rgba(0,0,0,0.2)';
                scrollBtn.style.zIndex = '10';
                scrollBtn.style.opacity = '0';
                scrollBtn.style.transition = 'opacity 0.3s ease';
                
                scrollBtn.addEventListener('click', function() {
                    chatMessages.scrollTop = chatMessages.scrollHeight;
                    scrollBtn.style.opacity = '0';
                    setTimeout(() => {
                        scrollBtn.remove();
                    }, 300);
                });
                
                chatContainer.appendChild(scrollBtn);
                setTimeout(() => {
                    scrollBtn.style.opacity = '1';
                }, 10);
            }
        } else {
            // Si estamos cerca del fondo, ocultar el botón
            const scrollBtn = document.getElementById('scroll-bottom-btn');
            if (scrollBtn) {
                scrollBtn.style.opacity = '0';
                setTimeout(() => {
                    scrollBtn.remove();
                }, 300);
            }
        }
    });
});