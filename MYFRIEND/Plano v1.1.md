

---
![[Pasted image 20260328092058.png]]
## Passo 1 — Atualizar as dependências

Abra o terminal dentro da pasta do projeto com o ambiente virtual ativado (`venv\Scripts\activate`) e rode:

```bash
pip install scikit-learn wikipedia-api bcrypt customtkinter requests
pip freeze > requirements.txt
```

O que cada um faz: `scikit-learn` é a biblioteca de ML que vai classificar o texto do usuário. `wikipedia-api` busca informações externas. `bcrypt` criptografa senhas. O resto você já conhece da v1.0.

---

## Passo 2 — Nova estrutura de pastas

A v1.1 adiciona novos arquivos. A estrutura completa fica assim:

```
myfriend/
├── main.py
├── ui/
│   ├── interface.py        ← tela principal (atualizada)
│   └── login_screen.py     ← NOVO: tela de login
├── core/
│   ├── nlp.py              ← atualizado com TF-IDF
│   ├── classifier.py       ← atualizado com sklearn
│   ├── responder.py        ← atualizado com fallback API
│   └── external_search.py  ← NOVO: busca Wikipedia
├── auth/
│   └── auth.py             ← NOVO: login e senha
├── database/
│   ├── db.py               ← atualizado com novas tabelas
│   └── myfriend.db
├── knowledge/
│   └── psych_data.json
├── utils/
│   └── helpers.py
├── requirements.txt
└── README.md
```

---

## Passo 3 — Banco de dados atualizado (5 tabelas)

Abra `database/db.py` e substitua tudo pelo código abaixo. Cada linha tem um comentário explicando o que faz:

```python
import sqlite3
import os

# Pega o caminho da pasta onde este arquivo está
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "myfriend.db")

def conectar():
    # Conecta ao banco. Se o arquivo .db não existir, o SQLite cria automaticamente
    conn = sqlite3.connect(DB_PATH)
    # row_factory faz as linhas retornarem como dicionários (mais fácil de usar)
    conn.row_factory = sqlite3.Row
    return conn

def criar_tabelas():
    conn = conectar()
    cursor = conn.cursor()

    # TABELA 1: usuários — guarda login e senha criptografada
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            username  TEXT UNIQUE NOT NULL,
            senha_hash TEXT NOT NULL,
            criado_em TEXT DEFAULT (datetime('now'))
        )
    """)

    # TABELA 2: sessões — cada vez que o usuário abre o app, é uma sessão nova
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessoes (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            iniciada_em TEXT DEFAULT (datetime('now')),
            encerrada_em TEXT,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        )
    """)

    # TABELA 3: mensagens — cada mensagem trocada, ligada a uma sessão
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mensagens (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            sessao_id   INTEGER NOT NULL,
            remetente   TEXT NOT NULL,  -- 'usuario' ou 'sistema'
            conteudo    TEXT NOT NULL,
            categoria   TEXT,
            timestamp   TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (sessao_id) REFERENCES sessoes(id)
        )
    """)

    # TABELA 4: base de conhecimento psicológico
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conhecimento (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            categoria    TEXT NOT NULL,
            palavras_chave TEXT NOT NULL,  -- lista separada por vírgula
            resposta     TEXT NOT NULL,
            fonte        TEXT
        )
    """)

    # TABELA 5: cache de buscas externas — evita chamar a API repetidamente
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cache_externo (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            query      TEXT UNIQUE NOT NULL,
            resultado  TEXT NOT NULL,
            buscado_em TEXT DEFAULT (datetime('now'))
        )
    """)

    conn.commit()
    conn.close()
    print("Banco de dados pronto.")

# Quando este arquivo for executado diretamente, cria as tabelas
if __name__ == "__main__":
    criar_tabelas()
```

Para criar o banco, rode no terminal:

```bash
python database/db.py
```

---

## Passo 4 — Sistema de login (`auth/auth.py`)

Crie o arquivo `auth/auth.py`. Este módulo cuida de registrar usuários e verificar senhas:

```python
import bcrypt
from database.db import conectar

def registrar_usuario(username, senha):
    """
    Cadastra um novo usuário.
    bcrypt transforma a senha em um hash — nunca guardamos a senha real.
    """
    # encode("utf-8") converte texto para bytes, que o bcrypt precisa
    senha_bytes = senha.encode("utf-8")

    # gensalt() gera um "tempero" aleatório que torna o hash único
    # mesmo que dois usuários tenham a mesma senha, os hashes serão diferentes
    salt = bcrypt.gensalt()

    # hashpw() aplica o algoritmo bcrypt e retorna o hash
    senha_hash = bcrypt.hashpw(senha_bytes, salt)

    conn = conectar()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO usuarios (username, senha_hash) VALUES (?, ?)",
            (username, senha_hash.decode("utf-8"))
            # decode("utf-8") converte bytes de volta para texto para salvar no banco
        )
        conn.commit()
        return True, "Usuário criado com sucesso!"
    except Exception:
        # Se o username já existe (UNIQUE), cai aqui
        return False, "Esse nome de usuário já existe."
    finally:
        conn.close()

def fazer_login(username, senha):
    """
    Verifica se a senha digitada corresponde ao hash guardado no banco.
    Retorna (True, usuario_id) se correto, ou (False, None) se errado.
    """
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, senha_hash FROM usuarios WHERE username = ?",
        (username,)
    )
    usuario = cursor.fetchone()
    conn.close()

    if usuario is None:
        return False, None  # usuário não existe

    # checkpw() compara a senha digitada com o hash guardado
    senha_correta = bcrypt.checkpw(
        senha.encode("utf-8"),
        usuario["senha_hash"].encode("utf-8")
    )

    if senha_correta:
        return True, usuario["id"]
    return False, None

def iniciar_sessao(usuario_id):
    """Cria uma nova sessão para o usuário que acabou de logar."""
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO sessoes (usuario_id) VALUES (?)",
        (usuario_id,)
    )
    sessao_id = cursor.lastrowid  # pega o ID da linha recém-inserida
    conn.commit()
    conn.close()
    return sessao_id

def encerrar_sessao(sessao_id):
    """Marca a sessão como encerrada quando o usuário fecha o app."""
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE sessoes SET encerrada_em = datetime('now') WHERE id = ?",
        (sessao_id,)
    )
    conn.commit()
    conn.close()
```

---

## Passo 5 — Modelo de ML com TF-IDF (`core/nlp.py`)

Este é o coração da v1.1. Substitua o `nlp.py` pelo código abaixo. TF-IDF é uma técnica que mede quão importante uma palavra é num texto — palavras raras que aparecem muito numa frase ganham peso maior:

```python
import json
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from database.db import conectar

# Variáveis globais — o modelo é carregado uma vez e reutilizado
_vectorizer = None  # o objeto que aprende o vocabulário
_matriz_tfidf = None  # a representação matemática de todos os textos
_conhecimento = []  # lista de dicionários com as respostas

def carregar_modelo():
    """
    Carrega os dados do banco e treina o TF-IDF.
    Deve ser chamado uma vez quando o app inicia.
    """
    global _vectorizer, _matriz_tfidf, _conhecimento

    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM conhecimento")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("AVISO: base de conhecimento vazia. Popule a tabela 'conhecimento'.")
        return

    # Monta a lista de textos que o TF-IDF vai analisar
    # Cada item é: palavras-chave + categoria (juntas formam o "documento")
    textos = []
    for row in rows:
        texto = f"{row['palavras_chave']} {row['categoria']}"
        textos.append(texto)
        _conhecimento.append(dict(row))

    # TfidfVectorizer aprende o vocabulário e converte textos em vetores numéricos
    # analyzer='word' olha para palavras, ngram_range=(1,2) considera pares de palavras também
    _vectorizer = TfidfVectorizer(
        analyzer='word',
        ngram_range=(1, 2),
        min_df=1  # inclui palavras que aparecem em pelo menos 1 documento
    )

    # fit_transform() faz duas coisas: aprende o vocabulário (fit) e transforma (transform)
    _matriz_tfidf = _vectorizer.fit_transform(textos)
    print(f"Modelo TF-IDF treinado com {len(textos)} categorias.")

def classificar(texto_usuario):
    """
    Recebe o texto do usuário e retorna o item de conhecimento mais parecido.
    Usa similaridade de cosseno — mede o ângulo entre dois vetores.
    Quanto mais próximo de 1.0, mais parecidos são os textos.
    """
    if _vectorizer is None or _matriz_tfidf is None:
        return None

    # Transforma o texto do usuário no mesmo formato vetorial
    # transform() (sem fit) usa o vocabulário já aprendido
    vetor_usuario = _vectorizer.transform([texto_usuario.lower()])

    # Calcula a similaridade entre o texto do usuário e TODOS os textos da base
    # cosine_similarity retorna um array de valores entre 0 e 1
    similaridades = cosine_similarity(vetor_usuario, _matriz_tfidf).flatten()

    # Pega o índice do valor mais alto (o texto mais parecido)
    indice_melhor = np.argmax(similaridades)
    score = similaridades[indice_melhor]

    # Se o score for muito baixo (abaixo de 0.15), o sistema não entendeu
    THRESHOLD = 0.15
    if score < THRESHOLD:
        return None

    return _conhecimento[indice_melhor]

def salvar_mensagem(sessao_id, remetente, conteudo, categoria=None):
    """Salva uma mensagem no banco para o histórico."""
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO mensagens (sessao_id, remetente, conteudo, categoria)
           VALUES (?, ?, ?, ?)""",
        (sessao_id, remetente, conteudo, categoria)
    )
    conn.commit()
    conn.close()

def buscar_historico(usuario_id, limite=20):
    """
    Retorna as últimas mensagens do usuário em todas as sessões.
    Útil para mostrar o histórico na tela.
    """
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT m.remetente, m.conteudo, m.timestamp, m.categoria
        FROM mensagens m
        JOIN sessoes s ON m.sessao_id = s.id
        WHERE s.usuario_id = ?
        ORDER BY m.timestamp DESC
        LIMIT ?
    """, (usuario_id, limite))
    mensagens = cursor.fetchall()
    conn.close()
    return [dict(m) for m in mensagens]
```

---

## Passo 6 — Busca externa com Wikipedia (`core/external_search.py`)

Crie o arquivo `core/external_search.py`:

```python
import wikipediaapi
from database.db import conectar

# Inicializa o cliente da Wikipedia em português
# o user_agent é obrigatório pela política da Wikipedia
wiki = wikipediaapi.Wikipedia(
    language='pt',
    user_agent='MyFriend/1.1 (projeto universitario)'
)

def buscar_no_cache(query):
    """
    Antes de chamar a Wikipedia, verifica se já buscamos isso antes.
    Isso economiza tempo e evita chamadas desnecessárias à internet.
    """
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT resultado FROM cache_externo WHERE query = ?",
        (query,)
    )
    resultado = cursor.fetchone()
    conn.close()
    return resultado["resultado"] if resultado else None

def salvar_no_cache(query, resultado):
    """Salva o resultado no banco para uso futuro."""
    conn = conectar()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO cache_externo (query, resultado) VALUES (?, ?)",
            (query, resultado)
        )
        conn.commit()
    except Exception:
        # Se a query já existe no cache (UNIQUE), ignora o erro
        pass
    finally:
        conn.close()

def buscar_wikipedia(termo):
    """
    Busca um termo na Wikipedia e retorna um resumo de 3 frases.
    Primeiro verifica o cache local para não fazer chamadas repetidas.
    """
    # 1. Tenta o cache primeiro
    cache = buscar_no_cache(termo)
    if cache:
        return cache

    # 2. Busca na Wikipedia
    try:
        pagina = wiki.page(termo)

        if not pagina.exists():
            return None

        # Pega o resumo completo e corta nas 3 primeiras frases
        resumo = pagina.summary
        frases = resumo.split('. ')
        resultado = '. '.join(frases[:3]) + '.'

        # 3. Salva no cache para a próxima vez
        salvar_no_cache(termo, resultado)

        return resultado

    except Exception as e:
        print(f"Erro ao buscar Wikipedia: {e}")
        return None

def buscar_por_categoria(categoria):
    """
    Converte uma categoria psicológica em um termo de busca da Wikipedia.
    Por exemplo, 'ansiedade' vira 'Transtorno de ansiedade'.
    """
    # Mapeamento de categorias do sistema para termos da Wikipedia
    mapa_busca = {
        "ansiedade": "Transtorno de ansiedade",
        "depressao": "Depressão (psicologia)",
        "autoestima": "Autoestima",
        "estresse": "Estresse psicológico",
        "panico": "Transtorno de pânico",
        "solidao": "Solidão",
        "burnout": "Burnout",
        "trauma": "Trauma psicológico",
    }

    # Usa o mapa ou a própria categoria como fallback
    termo = mapa_busca.get(categoria, categoria)
    return buscar_wikipedia(termo)
```

---

## Passo 7 — Responder com fallback para API (`core/responder.py`)

Substitua `core/responder.py`:

```python
from core.nlp import classificar, salvar_mensagem
from core.external_search import buscar_por_categoria

MENSAGEM_PROFISSIONAL = (
    "\n\n⚠️ Lembre-se: este sistema oferece orientação inicial. "
    "Para acompanhamento adequado, procure um psicólogo ou profissional de saúde mental."
)

def gerar_resposta(texto_usuario, sessao_id):
    """
    Pipeline completo de resposta:
    1. Classifica o texto com ML
    2. Se encontrou categoria → responde com a base local
    3. Se não encontrou → busca na Wikipedia
    4. Se nem isso → resposta padrão
    5. Sempre salva no banco e adiciona aviso profissional
    """

    # PASSO 1: tenta classificar com o modelo TF-IDF
    resultado = classificar(texto_usuario)

    if resultado:
        # PASSO 2: encontrou na base local
        categoria = resultado["categoria"]
        resposta_base = resultado["resposta"]

        # Tenta enriquecer com informação da Wikipedia
        info_extra = buscar_por_categoria(categoria)

        if info_extra:
            resposta = (
                f"{resposta_base}\n\n"
                f"📚 Contexto adicional: {info_extra}"
            )
        else:
            resposta = resposta_base

    else:
        # PASSO 3: não classificou — tenta buscar na Wikipedia diretamente
        # Usa as primeiras palavras do texto como query
        palavras = texto_usuario.split()[:3]
        query = " ".join(palavras)
        info_wiki = buscar_por_categoria(query)

        if info_wiki:
            resposta = (
                f"Não encontrei isso na minha base interna, mas encontrei algo relevante:\n\n"
                f"{info_wiki}"
            )
            categoria = "busca_externa"
        else:
            # PASSO 4: fallback final
            resposta = (
                "Entendo que você está passando por algo difícil. "
                "Poderia me contar um pouco mais sobre o que está sentindo? "
                "Estou aqui para ouvir."
            )
            categoria = "sem_classificacao"

    # PASSO 5: sempre adiciona o aviso de busca profissional
    resposta_final = resposta + MENSAGEM_PROFISSIONAL

    # PASSO 6: salva as duas mensagens no banco (usuário + sistema)
    salvar_mensagem(sessao_id, "usuario", texto_usuario, categoria)
    salvar_mensagem(sessao_id, "sistema", resposta_final, categoria)

    return resposta_final
```

---

## Passo 8 — Tela de login (`ui/login_screen.py`)

Crie o arquivo `ui/login_screen.py`:

```python
import customtkinter as ctk
from auth.auth import fazer_login, registrar_usuario

class TelaLogin(ctk.CTkToplevel):
    """
    Janela de login que aparece antes da tela principal.
    CTkToplevel é uma janela secundária do CustomTkinter.
    """
    def __init__(self, parent, callback_sucesso):
        super().__init__(parent)
        self.title("MyFriend — Login")
        self.geometry("400x500")
        self.resizable(False, False)

        # callback_sucesso é uma função passada pela janela principal
        # ela é chamada quando o login funciona, passando usuario_id e username
        self.callback_sucesso = callback_sucesso

        self._construir_ui()

    def _construir_ui(self):
        # Título
        ctk.CTkLabel(
            self, text="MyFriend", font=("Arial", 28, "bold")
        ).pack(pady=(40, 5))

        ctk.CTkLabel(
            self, text="Assistente de orientação psicológica",
            font=("Arial", 12), text_color="gray"
        ).pack(pady=(0, 30))

        # Campo usuário
        ctk.CTkLabel(self, text="Usuário").pack(anchor="w", padx=40)
        self.campo_usuario = ctk.CTkEntry(
            self, placeholder_text="Digite seu usuário", width=320
        )
        self.campo_usuario.pack(padx=40, pady=(0, 15))

        # Campo senha
        ctk.CTkLabel(self, text="Senha").pack(anchor="w", padx=40)
        self.campo_senha = ctk.CTkEntry(
            self, placeholder_text="Digite sua senha",
            show="*",  # show="*" esconde os caracteres (modo senha)
            width=320
        )
        self.campo_senha.pack(padx=40, pady=(0, 20))

        # Mensagem de erro (fica invisível até ser necessária)
        self.label_erro = ctk.CTkLabel(
            self, text="", text_color="red", font=("Arial", 11)
        )
        self.label_erro.pack(pady=(0, 10))

        # Botão Entrar
        ctk.CTkButton(
            self, text="Entrar", width=320, height=40,
            command=self._tentar_login
        ).pack(padx=40)

        # Separador
        ctk.CTkLabel(self, text="— ou —", text_color="gray").pack(pady=10)

        # Botão Criar conta
        ctk.CTkButton(
            self, text="Criar conta", width=320, height=40,
            fg_color="transparent", border_width=1,
            command=self._criar_conta
        ).pack(padx=40)

    def _tentar_login(self):
        username = self.campo_usuario.get().strip()
        senha = self.campo_senha.get()

        if not username or not senha:
            self.label_erro.configure(text="Preencha usuário e senha.")
            return

        sucesso, usuario_id = fazer_login(username, senha)

        if sucesso:
            # Fecha a tela de login e avisa a janela principal
            self.destroy()
            self.callback_sucesso(usuario_id, username)
        else:
            self.label_erro.configure(text="Usuário ou senha incorretos.")

    def _criar_conta(self):
        username = self.campo_usuario.get().strip()
        senha = self.campo_senha.get()

        if len(username) < 3:
            self.label_erro.configure(text="Usuário precisa ter ao menos 3 caracteres.")
            return
        if len(senha) < 6:
            self.label_erro.configure(text="Senha precisa ter ao menos 6 caracteres.")
            return

        sucesso, msg = registrar_usuario(username, senha)

        if sucesso:
            self.label_erro.configure(text_color="green", text=f"{msg} Agora faça login.")
        else:
            self.label_erro.configure(text_color="red", text=msg)
```

---

## Passo 9 — Interface principal atualizada (`ui/interface.py`)

Substitua `ui/interface.py` inteiro:

```python
import customtkinter as ctk
from core.responder import gerar_resposta
from core.nlp import carregar_modelo, buscar_historico
from auth.auth import iniciar_sessao, encerrar_sessao
from ui.login_screen import TelaLogin

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class MyFriendApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("MyFriend v1.1")
        self.geometry("800x600")
        self.minsize(600, 400)

        # Estado interno do app
        self.usuario_id = None
        self.username = None
        self.sessao_id = None

        # Carrega o modelo ML antes de qualquer coisa
        carregar_modelo()

        # Constrói a interface principal (começa vazia/bloqueada)
        self._construir_interface()

        # Abre a tela de login por cima
        # after(100, ...) espera 100ms para a janela principal abrir primeiro
        self.after(100, self._abrir_login)

    def _construir_interface(self):
        # Barra superior com nome do usuário e botão de histórico
        self.barra_topo = ctk.CTkFrame(self, height=50, corner_radius=0)
        self.barra_topo.pack(fill="x", side="top")

        self.label_usuario = ctk.CTkLabel(
            self.barra_topo, text="Não autenticado",
            font=("Arial", 13)
        )
        self.label_usuario.pack(side="left", padx=20, pady=10)

        self.btn_historico = ctk.CTkButton(
            self.barra_topo, text="Ver histórico", width=130,
            command=self._mostrar_historico
        )
        self.btn_historico.pack(side="right", padx=10, pady=8)

        # Área de chat (onde as mensagens aparecem)
        self.area_chat = ctk.CTkTextbox(
            self, state="disabled", font=("Arial", 13),
            wrap="word"  # quebra linha nas palavras, não no meio delas
        )
        self.area_chat.pack(fill="both", expand=True, padx=15, pady=(10, 0))

        # Frame da entrada de texto
        frame_entrada = ctk.CTkFrame(self, corner_radius=0)
        frame_entrada.pack(fill="x", padx=15, pady=10)

        self.campo_entrada = ctk.CTkEntry(
            frame_entrada,
            placeholder_text="Como você está se sentindo hoje?",
            font=("Arial", 13), height=40
        )
        self.campo_entrada.pack(side="left", fill="x", expand=True, padx=(0, 10))

        # Bind: pressionar Enter também envia a mensagem
        self.campo_entrada.bind("<Return>", lambda e: self._enviar())

        self.btn_enviar = ctk.CTkButton(
            frame_entrada, text="Enviar", width=100, height=40,
            command=self._enviar
        )
        self.btn_enviar.pack(side="right")

    def _abrir_login(self):
        # Cria a tela de login passando o callback de sucesso
        TelaLogin(self, self._on_login_sucesso)

    def _on_login_sucesso(self, usuario_id, username):
        """Chamado pela tela de login quando o login é bem-sucedido."""
        self.usuario_id = usuario_id
        self.username = username

        # Cria uma nova sessão no banco
        self.sessao_id = iniciar_sessao(usuario_id)

        # Atualiza a barra do topo
        self.label_usuario.configure(text=f"Olá, {username}")

        # Mensagem de boas-vindas no chat
        self._adicionar_mensagem(
            "MyFriend",
            f"Olá, {username}! Sou o MyFriend. "
            "Estou aqui para te ouvir e oferecer orientação inicial. "
            "Como você está se sentindo hoje?"
        )

    def _enviar(self):
        # Bloqueia envio se não estiver logado
        if not self.sessao_id:
            return

        texto = self.campo_entrada.get().strip()
        if not texto:
            return

        # Exibe a mensagem do usuário
        self._adicionar_mensagem(self.username, texto)
        self.campo_entrada.delete(0, "end")

        # Gera e exibe a resposta (pode demorar um pouco pela Wikipedia)
        resposta = gerar_resposta(texto, self.sessao_id)
        self._adicionar_mensagem("MyFriend", resposta)

    def _adicionar_mensagem(self, remetente, texto):
        """Adiciona uma mensagem na área de chat."""
        self.area_chat.configure(state="normal")
        self.area_chat.insert("end", f"\n{remetente}:\n{texto}\n")
        self.area_chat.configure(state="disabled")
        # Rola para o final automaticamente
        self.area_chat.see("end")

    def _mostrar_historico(self):
        """Abre uma janela com o histórico de conversas do usuário."""
        if not self.usuario_id:
            return

        janela = ctk.CTkToplevel(self)
        janela.title("Histórico de conversas")
        janela.geometry("600x400")

        area = ctk.CTkTextbox(janela, state="disabled", font=("Arial", 12))
        area.pack(fill="both", expand=True, padx=15, pady=15)

        mensagens = buscar_historico(self.usuario_id, limite=30)

        area.configure(state="normal")
        if not mensagens:
            area.insert("end", "Nenhuma conversa anterior encontrada.")
        else:
            # As mensagens vêm do banco em ordem DESC, então invertemos
            for msg in reversed(mensagens):
                area.insert(
                    "end",
                    f"[{msg['timestamp']}] {msg['remetente'].upper()}:\n{msg['conteudo']}\n\n"
                )
        area.configure(state="disabled")

    def on_closing(self):
        """Chamado quando o usuário fecha a janela."""
        if self.sessao_id:
            encerrar_sessao(self.sessao_id)
        self.destroy()
```

---

## Passo 10 — Ponto de entrada (`main.py`)

Substitua `main.py`:

```python
from database.db import criar_tabelas
from ui.interface import MyFriendApp

def main():
    # Garante que o banco e as tabelas existem antes de tudo
    criar_tabelas()

    # Cria e inicia o app
    app = MyFriendApp()

    # Quando a janela fechar, chama o método que encerra a sessão
    app.protocol("WM_DELETE_WINDOW", app.on_closing)

    # mainloop() é o loop principal da interface gráfica
    # o programa fica aqui até o usuário fechar a janela
    app.mainloop()

if __name__ == "__main__":
    main()
```

---

## Passo 11 — Popular a base de conhecimento

Crie o script `database/popular_conhecimento.py` e rode ele uma única vez:

```python
import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import conectar, criar_tabelas

DADOS = [
    {
        "categoria": "ansiedade",
        "palavras_chave": "ansioso ansiedade preocupado nervoso medo tensão inquieto angustiado",
        "resposta": "Percebo que você está passando por momentos de ansiedade. Isso é muito comum e existem formas de lidar. Técnicas de respiração profunda e mindfulness podem ajudar no imediato. Gostaria de explorar mais sobre o que está causando essa sensação?",
        "fonte": "CID-11 / DSM-5"
    },
    {
        "categoria": "depressao",
        "palavras_chave": "triste tristeza deprimido sem energia cansado desmotivado vazio chorar choro",
        "resposta": "O que você está descrevendo soa como algo muito pesado de carregar. Sentimentos de tristeza persistente merecem atenção. Você não precisa enfrentar isso sozinho. Quero entender melhor como você está se sentindo.",
        "fonte": "CID-11 / DSM-5"
    },
    {
        "categoria": "autoestima",
        "palavras_chave": "autoestima inseguro insegurança confiança não me amo me odeio me sinto feio fracasso",
        "resposta": "A autoestima é construída ao longo do tempo e pode ser trabalhada. Perceber esses pensamentos já é um primeiro passo importante. Você consegue identificar alguma situação específica que desencadeia esses sentimentos?",
        "fonte": "Psicologia cognitivo-comportamental"
    },
    {
        "categoria": "estresse",
        "palavras_chave": "estressado estresse trabalho pressão sobrecarga esgotado não aguento mais muita coisa",
        "resposta": "O estresse crônico pode afetar tanto a mente quanto o corpo. É importante reconhecer os sinais que ele dá. Você tem conseguido reservar algum momento para si mesmo ao longo do dia?",
        "fonte": "OMS — Saúde Mental no Trabalho"
    },
    {
        "categoria": "solidao",
        "palavras_chave": "sozinho solidão isolado sem amigos ninguém me entende abandonado",
        "resposta": "Sentir-se sozinho é uma das experiências mais difíceis que existem. Isso que você está sentindo é válido. Às vezes o isolamento pode nos fazer ver a realidade de forma distorcida. Quer me contar mais sobre essa sensação?",
        "fonte": "Psicologia humanista"
    },
    {
        "categoria": "burnout",
        "palavras_chave": "burnout esgotamento esgotado trabalho exausto não consigo mais cansaço crônico",
        "resposta": "O burnout é reconhecido pela OMS como um fenômeno ocupacional sério. O que você descreve sugere que seu corpo e mente precisam de atenção urgente. Estabelecer limites e buscar apoio profissional são passos fundamentais.",
        "fonte": "OMS — CID-11"
    },
    {
        "categoria": "panico",
        "palavras_chave": "pânico ataque coração acelerado sufocando sufocar tremendo tremer não consigo respirar",
        "resposta": "Um ataque de pânico pode ser muito assustador, mas não é perigoso fisicamente. Se estiver acontecendo agora: respire devagar pelo nariz contando até 4, segure por 4, solte pela boca em 6. Isso ativa o sistema nervoso parassimpático e ajuda a diminuir a intensidade.",
        "fonte": "Protocolo de intervenção em crise — APA"
    },
    {
        "categoria": "relacionamento",
        "palavras_chave": "relacionamento namoro namorado namorada brigar briga separar término amor cônjuge",
        "resposta": "Problemas em relacionamentos podem causar muito sofrimento. Comunicação clara e respeito mútuo são pilares importantes. Você consegue identificar qual é o principal ponto de conflito?",
        "fonte": "Terapia de casal — Gottman Institute"
    },
    {
        "categoria": "luto",
        "palavras_chave": "luto perda morte morreu faleceu perdi saudade ausência",
        "resposta": "O luto é uma das experiências mais profundas da vida humana. Não existe um tempo certo para superar uma perda — cada pessoa vive esse processo de forma única. Você não precisa ser forte o tempo todo. Como você está cuidando de si nesse momento?",
        "fonte": "Modelos de luto — Kübler-Ross / Worden"
    },
    {
        "categoria": "sono",
        "palavras_chave": "insônia dormir não consigo dormir acordando pesadelo sono ruim cansado sem dormir",
        "resposta": "A privação de sono afeta diretamente o humor, a concentração e o bem-estar geral. Alguns hábitos simples podem ajudar: evitar telas 1 hora antes de dormir, manter um horário regular e criar um ambiente escuro e fresco. Isso tem durado há quanto tempo?",
        "fonte": "Higiene do sono — AASM"
    },
]

def popular():
    criar_tabelas()
    conn = conectar()
    cursor = conn.cursor()

    # Limpa dados antigos para evitar duplicatas
    cursor.execute("DELETE FROM conhecimento")

    for item in DADOS:
        cursor.execute(
            """INSERT INTO conhecimento (categoria, palavras_chave, resposta, fonte)
               VALUES (?, ?, ?, ?)""",
            (item["categoria"], item["palavras_chave"], item["resposta"], item["fonte"])
        )

    conn.commit()
    conn.close()
    print(f"{len(DADOS)} categorias inseridas com sucesso!")

if __name__ == "__main__":
    popular()
```

Rode no terminal:

```bash
python database/popular_conhecimento.py
```

---

## Passo 12 — Gerar o .exe

Com tudo funcionando, empacote:

```bash
pyinstaller --onefile --windowed --name MyFriend main.py
```

O executável estará em `dist/MyFriend.exe`.

---

## Passo 13 — Git: salve tudo

```bash
git add .
git commit -m "v1.1: login, historico, TF-IDF, Wikipedia API"
git tag v1.1
git push
git push --tags
```

---

## Ordem exata de execução — copie e cole no terminal

```bash
# 1. Ativar ambiente
venv\Scripts\activate

# 2. Instalar dependências
pip install scikit-learn wikipedia-api bcrypt customtkinter requests
pip freeze > requirements.txt

# 3. Criar banco e tabelas
python database/db.py

# 4. Popular a base de conhecimento
python database/popular_conhecimento.py

# 5. Rodar o app
python main.py

# 6. Quando estiver pronto, gerar o .exe
pyinstaller --onefile --windowed --name MyFriend main.py
```

Se travar em qualquer passo, me manda a mensagem de erro exata que eu resolvo na hora.