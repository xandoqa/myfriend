# ui/interface.py
import tkinter as tk
from tkinter import scrolledtext, messagebox, font
from datetime import datetime
import json
import os

class Application:
    def __init__(self, master=None):
        self.master = master
        self.conversation_history = []  # Para contexto (não salva em disco)
        
        # Placeholders para módulos futuros
        self.classifier = None
        self.responder = None
        self.nlp = None
        
        self.setup_ui()
        self.load_knowledge_base()
        self.add_welcome_message()
    
    def setup_ui(self):
        """Configura toda a interface do usuário"""
        self.master.title("MyFriend - Psychological Support Assistant")
        self.master.geometry("1366x768")
        self.master.configure(bg="#2c3e50")
        
        # Frame principal
        main_frame = tk.Frame(self.master, bg="#2c3e50")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Header com título
        header_frame = tk.Frame(main_frame, bg="#34495e", height=80)
        header_frame.pack(fill=tk.X, pady=(0, 20))
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(
            header_frame, 
            text="🧠 MyFriend - Seu Assistente Psicológico", 
            font=("Arial", 20, "bold"),
            bg="#34495e",
            fg="#ecf0f1"
        )
        title_label.pack(pady=20)
        
        # Disclaimer ético (importante!)
        disclaimer = tk.Label(
            main_frame,
            text="⚠️ IMPORTANTE: Este é um assistente de apoio inicial. Em casos de emergência, procure ajuda profissional (CVV: 188)",
            font=("Arial", 10),
            bg="#2c3e50",
            fg="#e74c3c"
        )
        disclaimer.pack(pady=(0, 10))
        
        # Área de chat (com scroll)
        self.chat_area = scrolledtext.ScrolledText(
            main_frame,
            wrap=tk.WORD,
            font=("Segoe UI", 11),
            bg="#ecf0f1",
            fg="#2c3e50",
            height=25,
            relief=tk.FLAT,
            padx=15,
            pady=15
        )
        self.chat_area.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        self.chat_area.config(state=tk.DISABLED)
        
        # Configurar estilos de texto
        self.chat_area.tag_config("user", font=("Segoe UI", 11, "bold"), foreground="#2980b9", spacing=5)
        self.chat_area.tag_config("bot", font=("Segoe UI", 11, "bold"), foreground="#27ae60", spacing=5)
        self.chat_area.tag_config("system", font=("Segoe UI", 10, "italic"), foreground="#7f8c8d", spacing=5)
        self.chat_area.tag_config("user_msg", font=("Segoe UI", 11), foreground="#2c3e50", spacing=3, lmargin1=20)
        self.chat_area.tag_config("bot_msg", font=("Segoe UI", 11), foreground="#34495e", spacing=3, lmargin1=20)
        
        # Frame de entrada
        input_frame = tk.Frame(main_frame, bg="#2c3e50")
        input_frame.pack(fill=tk.X)
        
        # Barra de entrada de texto
        self.search_entry = tk.Entry(
            input_frame,
            font=("Segoe UI", 13),
            bg="#ecf0f1",
            fg="#2c3e50",
            relief=tk.FLAT,
            highlightthickness=2,
            highlightcolor="#3498db",
            highlightbackground="#bdc3c7"
        )
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10), ipady=8)
        
        # Botão enviar
        self.send_button = tk.Button(
            input_frame,
            text="Enviar ➤",
            font=("Segoe UI", 12, "bold"),
            bg="#3498db",
            fg="white",
            relief=tk.FLAT,
            padx=25,
            cursor="hand2",
            command=self.send_message
        )
        self.send_button.pack(side=tk.RIGHT)
        
        # Botão limpar conversa
        self.clear_button = tk.Button(
            input_frame,
            text="🗑️ Limpar",
            font=("Segoe UI", 10),
            bg="#95a5a6",
            fg="white",
            relief=tk.FLAT,
            padx=15,
            cursor="hand2",
            command=self.clear_chat
        )
        self.clear_button.pack(side=tk.RIGHT, padx=(0, 10))
        
        # Vincular Enter à função send_message
        self.search_entry.bind("<Return>", lambda event: self.send_message())
        
        # Focar no campo de entrada
        self.search_entry.focus()
    
    def load_knowledge_base(self):
        """Carrega a base de conhecimento (simulada por enquanto)"""
        # Isso será substituído pelo db.py depois
        self.knowledge = {
            "saudacoes": ["oi", "olá", "opa", "hey", "e aí"],
            "tristeza": ["triste", "deprimido", "pra baixo", "desanimado"],
            "ansiedade": ["ansioso", "nervoso", "preocupado", "medo"],
            "alegria": ["feliz", "alegre", "contente", "bom"],
            "despedida": ["tchau", "até logo", "sair", "fechar"]
        }
    
    def add_welcome_message(self):
        """Adiciona mensagem de boas-vindas"""
        welcome_text = (
            "Olá! 👋 Eu sou o MyFriend, seu assistente de apoio psicológico.\n\n"
            "Estou aqui para:\n"
            "• Ouvir o que você tem a dizer\n"
            "• Oferecer apoio inicial baseado em princípios psicológicos\n"
            "• Recomendar ajuda profissional quando necessário\n\n"
            "Como você está se sentindo hoje? 💙\n\n"
            "---\n"
            "💡 Lembre-se: não substituo um psicólogo profissional."
        )
        self.add_bot_message(welcome_text)
    
    def add_user_message(self, message):
        """Adiciona mensagem do usuário à área de chat"""
        self.chat_area.config(state=tk.NORMAL)
        timestamp = datetime.now().strftime("%H:%M")
        
        self.chat_area.insert(tk.END, f"\nVocê [{timestamp}]:\n", "user")
        self.chat_area.insert(tk.END, f"{message}\n\n", "user_msg")
        
        self.chat_area.see(tk.END)
        self.chat_area.config(state=tk.DISABLED)
        
        # Salvar no histórico (para contexto)
        self.conversation_history.append({"role": "user", "message": message, "timestamp": timestamp})
    
    def add_bot_message(self, message):
        """Adiciona mensagem do bot à área de chat"""
        self.chat_area.config(state=tk.NORMAL)
        timestamp = datetime.now().strftime("%H:%M")
        
        self.chat_area.insert(tk.END, f"\nMyFriend [{timestamp}]:\n", "bot")
        self.chat_area.insert(tk.END, f"{message}\n\n", "bot_msg")
        
        self.chat_area.see(tk.END)
        self.chat_area.config(state=tk.DISABLED)
        
        # Salvar no histórico
        self.conversation_history.append({"role": "assistant", "message": message, "timestamp": timestamp})
    
    def add_system_message(self, message):
        """Adiciona mensagem do sistema (disclaimers, avisos)"""
        self.chat_area.config(state=tk.NORMAL)
        self.chat_area.insert(tk.END, f"\n{message}\n\n", "system")
        self.chat_area.see(tk.END)
        self.chat_area.config(state=tk.DISABLED)
    
    def classify_intent(self, user_input):
        """
        Classifica a intenção do usuário.
        FUTURO: Isso será substituído pelo classifier.py com ML
        """
        user_input_lower = user_input.lower()
        
        # Classificação simples baseada em palavras-chave
        if any(word in user_input_lower for word in self.knowledge["despedida"]):
            return "despedida"
        elif any(word in user_input_lower for word in self.knowledge["tristeza"]):
            return "tristeza"
        elif any(word in user_input_lower for word in self.knowledge["ansiedade"]):
            return "ansiedade"
        elif any(word in user_input_lower for word in self.knowledge["alegria"]):
            return "alegria"
        elif any(word in user_input_lower for word in self.knowledge["saudacoes"]):
            return "saudacao"
        else:
            return "geral"
    
    def get_response(self, user_input, intent):
        """
        Gera resposta baseada na intenção classificada.
        FUTURO: Isso será substituído pelo responder.py com lógica mais avançada
        """
        responses = {
            "despedida": [
                "Foi um prazer conversar com você! 💙\n\nLembre-se: cuidar da saúde mental é muito importante. Se precisar, estou aqui.\n\nAté logo! 👋"
            ],
            "tristeza": [
                "Sinto muito que você esteja se sentindo assim. 😔\n\n" +
                "Quer conversar mais sobre o que está te deixando triste? Estou aqui para ouvir sem julgamentos.\n\n" +
                "Lembre-se que sentimentos são temporários, mesmo quando parecem intensos."
            ],
            "ansiedade": [
                "A ansiedade pode ser realmente desconfortável. 🫂\n\n" +
                "Vamos tentar uma técnica de respiração juntos?\n" +
                "• Inspire profundamente por 4 segundos\n" +
                "• Segure por 4 segundos\n" +
                "• Expire lentamente por 4 segundos\n\n" +
                "Repita 3 vezes. Como você se sente agora?"
            ],
            "alegria": [
                "Que bom saber que você está se sentindo bem! 😊\n\n" +
                "É importante celebrar esses momentos. O que tem contribuído para essa felicidade?"
            ],
            "saudacao": [
                "Olá! Como posso ajudá-lo hoje? 😊\n\n" +
                "Estou aqui para conversar sobre o que você estiver sentindo."
            ],
            "geral": [
                "Obrigado por compartilhar. 🫂\n\n" +
                "Pode me contar mais sobre isso? Quanto mais você falar, melhor posso entender e ajudar.\n\n" +
                "Lembre-se que você não está sozinho nessa jornada."
            ]
        }
        
        import random
        response = random.choice(responses.get(intent, responses["geral"]))
        
        # Sempre incluir recomendação de ajuda profissional quando apropriado
        if intent in ["tristeza", "ansiedade", "geral"]:
            response += "\n\n---\n💙 **Lembrete importante:** Se estiver passando por momentos muito difíceis, considere buscar ajuda profissional. O CVV oferece apoio gratuito pelo telefone 188."
        
        return response
    
    def send_message(self):
        """Processa e envia a mensagem do usuário"""
        user_input = self.search_entry.get().strip()
        
        if not user_input:
            return
        
        # Limpar entrada
        self.search_entry.delete(0, tk.END)
        
        # Adicionar mensagem do usuário ao chat
        self.add_user_message(user_input)
        
        # Classificar intenção (futuro: usar classifier.py)
        intent = self.classify_intent(user_input)
        
        # Gerar resposta (futuro: usar responder.py)
        response = self.get_response(user_input, intent)
        
        # Adicionar resposta do bot
        self.add_bot_message(response)
        
        # Se for despedida, fechar após alguns segundos
        if intent == "despedida":
            self.master.after(3000, self.master.quit)
    
    def clear_chat(self):
        """Limpa o histórico de conversa (mas mantém boas-vindas)"""
        if messagebox.askyesno("Limpar conversa", "Tem certeza que deseja limpar todo o histórico da conversa?"):
            self.chat_area.config(state=tk.NORMAL)
            self.chat_area.delete(1.0, tk.END)
            self.chat_area.config(state=tk.DISABLED)
            self.conversation_history = []
            self.add_welcome_message()

def main():
    root = tk.Tk()
    app = Application(root)
    root.mainloop()

if __name__ == "__main__":
    main()