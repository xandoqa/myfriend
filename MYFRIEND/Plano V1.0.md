assistente conversacional de orientação psicológica inicial

---

## Visão geral da arquitetura do MyFriend

Antes do passo a passo, veja como o sistema se encaixa todo junto:---

## Fase 0 — Configuração do ambiente (faça isso primeiro, tudo depende disso)
![[myfriend_architecture.svg|671]]
**Linguagem:** Python 3.11+. Só Python. Não precisa aprender outra coisa para a v1.0.

Instale o Python em python.org, marque a opção "Add to PATH" no instalador. Depois instale o VS Code como editor.

Abra o terminal e rode:

```bash
python --version        # confirma que está instalado
pip install virtualenv  # gerenciador de ambientes
```

Crie a pasta do projeto e o ambiente virtual:

```bash
mkdir myfriend
cd myfriend
python -m venv venv
venv\Scripts\activate      # Windows
pip install nltk spacy customtkinter sqlite3-api pyinstaller requests
```

---

## Fase 1 — Git e repositório (configure agora, antes de escrever qualquer código)

Sim, você precisa do Git. É obrigatório — é o que salva seu histórico, permite voltar atrás se algo quebrar, e é o que você vai entregar como projeto.

```bash
git init
git config --global user.name "Alexandre Rodrigues Costa"
git config --global user.email "seu@email.com"
```

Crie um arquivo `.gitignore` na raiz com:

```
venv/
__pycache__/
*.pyc
*.exe
dist/
build/
.env
```

Crie uma conta no GitHub (gratuita), crie um repositório chamado `myfriend`, e conecte:

```bash
git remote add origin https://github.com/seu-usuario/myfriend.git
git add .
git commit -m "inicial: estrutura do projeto"
git push -u origin main
```

A partir daí, sempre que terminar uma funcionalidade, rode:

```bash
git add .
git commit -m "descreva o que você fez"
git push
```

---

## Fase 2 — Estrutura de pastas (defina isso antes de escrever código)

Organize o projeto assim desde o início:

```
myfriend/
├── main.py              ← ponto de entrada
├── ui/
│   └── interface.py     ← tela com Tkinter/CustomTkinter
├── core/
│   ├── nlp.py           ← processamento de linguagem
│   ├── classifier.py    ← classifica o que o usuário disse
│   └── responder.py     ← gera a resposta
├── database/
│   ├── db.py            ← conexão e queries SQLite
│   └── myfriend.db      ← arquivo do banco (gerado automaticamente)
├── knowledge/
│   └── psych_data.json  ← sua base de conhecimento
├── utils/
│   └── helpers.py       ← funções auxiliares
├── requirements.txt
└── README.md
```

---

## Fase 3 — Banco de dados (SQLite — sem servidor, arquivo local)

Você vai usar SQLite. É um arquivo `.db` que fica dentro da pasta do projeto — não precisa instalar nada, não precisa de servidor, funciona offline, e vem embutido no Python.

O que guardar no banco:

```sql
-- Tabela de conversas (histórico)
CREATE TABLE conversas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    usuario_input TEXT,
    sistema_resposta TEXT,
    categoria TEXT
);

-- Tabela de conhecimento psicológico
CREATE TABLE conhecimento (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    categoria TEXT,        -- ex: "ansiedade", "depressão", "autoestima"
    palavra_chave TEXT,
    resposta TEXT,
    fonte TEXT
);

-- Tabela de encaminhamentos
CREATE TABLE encaminhamentos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo TEXT,
    mensagem TEXT,
    nivel_urgencia INTEGER
);
```

Em Python, a conexão fica assim:

```python
import sqlite3

def conectar():
    conn = sqlite3.connect("database/myfriend.db")
    conn.row_factory = sqlite3.Row
    return conn
```

---

## Fase 4 — Base de conhecimento (de onde vêm os dados)

Aqui está a parte mais importante do seu documento: você precisou definir de onde vem o conteúdo psicológico. As opções são, em ordem de viabilidade:

**Opção A — Você mesmo popula (recomendada para v1.0).** Leia materiais de psicologia (DSM, livros universitários, artigos do CFP — Conselho Federal de Psicologia) e escreve os conteúdos manualmente em JSON. Depois importa pro banco. Isso garante controle e confiabilidade.

```json
[
  {
    "categoria": "ansiedade",
    "palavras_chave": ["ansioso", "ansiedade", "preocupado", "nervoso", "medo"],
    "resposta": "Parece que você está passando por momentos de ansiedade. Isso é muito comum e tem formas de lidar. Gostaria de explorar isso mais?",
    "fonte": "Manual de Psicologia Clínica, Cap. 4"
  }
]
```

**Opção B — Web scraping (para v1.1).** Use `requests` + `BeautifulSoup` para coletar textos de sites confiáveis (CFP, ABEP, PubMed).

**Opção C — API de IA (para versões futuras).** Conecta na API do OpenAI ou usa um modelo local com `ollama`. Isso é a integração de ML de verdade que o documento menciona.

Para a v1.0, fique na Opção A. Popule o banco manualmente com pelo menos 10 categorias e 5 respostas por categoria.

---

## Fase 5 — Lógica de NLP (o "cérebro" do sistema)

Esta é a parte de Machine Learning do projeto. Para a v1.0, você vai usar técnicas simples e eficazes:

```python
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords

nltk.download('punkt')
nltk.download('stopwords')

def preprocessar(texto):
    tokens = word_tokenize(texto.lower(), language='portuguese')
    stop = set(stopwords.words('portuguese'))
    return [t for t in tokens if t.isalpha() and t not in stop]

def classificar(texto, conhecimento):
    tokens = preprocessar(texto)
    melhor_categoria = None
    maior_score = 0

    for item in conhecimento:
        palavras_chave = item['palavras_chave']
        score = sum(1 for t in tokens if t in palavras_chave)
        if score > maior_score:
            maior_score = score
            melhor_categoria = item

    return melhor_categoria
```

Isso já é ML na prática: tokenização, remoção de stopwords, matching por frequência. Para a v1.1, você pode evoluir para TF-IDF com `sklearn` ou um modelo de embeddings com `sentence-transformers`.

---

## Fase 6 — Interface gráfica

Use CustomTkinter — é Tkinter moderno, visual limpo, simples de aprender:

```python
import customtkinter as ctk

class MyFriendApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("MyFriend")
        self.geometry("700x500")

        self.chat_area = ctk.CTkTextbox(self, state="disabled")
        self.chat_area.pack(fill="both", expand=True, padx=20, pady=10)

        self.input_frame = ctk.CTkFrame(self)
        self.input_frame.pack(fill="x", padx=20, pady=10)

        self.entrada = ctk.CTkEntry(self.input_frame, placeholder_text="Como você está se sentindo?")
        self.entrada.pack(side="left", fill="x", expand=True)

        self.btn_enviar = ctk.CTkButton(self.input_frame, text="Enviar", command=self.enviar)
        self.btn_enviar.pack(side="right", padx=5)

    def enviar(self):
        texto = self.entrada.get()
        # chama a lógica de NLP aqui
        self.entrada.delete(0, "end")
```

---

## Fase 7 — Empacotamento como .exe

Quando o código estiver pronto, use PyInstaller:

```bash
pip install pyinstaller
pyinstaller --onefile --windowed main.py --name MyFriend
```

O arquivo `.exe` aparece em `dist/MyFriend.exe`. Esse é o executável final que qualquer pessoa pode rodar no Windows sem ter Python instalado.

---

## Fase 8 — Ordem exata de execução (o seu sprint)

Sem tempo? Siga esta ordem e não pule etapas:

1. Instalar Python, VS Code, Git — 1h
2. Criar repositório no GitHub, estrutura de pastas — 30min
3. Criar o banco SQLite e as tabelas — 1h
4. Popular o JSON de conhecimento com pelo menos 5 categorias — 2–4h (é o maior trabalho)
5. Importar o JSON pro banco com um script Python — 1h
6. Implementar o `nlp.py` com tokenização e classificação — 2h
7. Implementar o `responder.py` que pega a resposta do banco — 1h
8. Criar a interface gráfica com CustomTkinter — 2–3h
9. Conectar interface + lógica + banco — 1–2h
10. Testar, ajustar respostas, tratar casos sem resposta — 2h
11. Empacotar com PyInstaller — 30min
12. Commit final e tag de versão no Git: `git tag v1.0` — 10min

Total estimado: 15–20 horas de trabalho focado.

---

## O que deixar para a v1.1 (não faça agora)

APIs externas (Google, Wikipedia), modelo de ML treinado, login de usuário, histórico persistente entre sessões, e qualquer coisa que envolva servidor. Tudo isso é v1.1. Foque em entregar a v1.0 funcionando.

Se quiser, me fala qual fase você quer atacar primeiro e eu escrevo o código completo dessa parte.