import os
import sqlite3

caminho = r'\\192.168.0.120\Teste\Banco\application.db'

if not os.path.exists(caminho):
    print("⚠️ Banco de dados não encontrado. Verifique conexão com a rede ou permissões.")
else:
    conn = sqlite3.connect(caminho)
    print("✅ Conectado com sucesso.")
