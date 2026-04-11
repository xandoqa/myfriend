from tkinter import *
from tkinter import scrolledtext, messagebox, font
from datetime import datetime
import json
import os 

class Aplication:
    def __init__(self, master=None):
        self.master = master
        self.conversation_history = [] #não salva em disco


        #placeholders para módulos futuros
        self.classifier = None
        self.responder = None
        self.nlp = None

        self.setup_ui()
        self.load_knowledge_base()
        self.add_welcome_message()

    
    def setup_ui(self):
        