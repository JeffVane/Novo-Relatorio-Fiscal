import sqlite3

def converter_pesos_para_inteiros():
    conn = sqlite3.connect("application.db")
    cursor = conn.cursor()

    try:
        # 1. Criar nova tabela com coluna INTEGER
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS weights_temp (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                procedure_id INTEGER UNIQUE NOT NULL,
                weight INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (procedure_id) REFERENCES procedures(id) ON DELETE CASCADE
            )
        ''')

        # 2. Copiar os dados convertendo os pesos para inteiro
        cursor.execute("SELECT id, procedure_id, weight FROM weights")
        for id_, proc_id, weight in cursor.fetchall():
            peso_inteiro = int(round(weight))
            cursor.execute('''
                INSERT OR REPLACE INTO weights_temp (id, procedure_id, weight)
                VALUES (?, ?, ?)
            ''', (id_, proc_id, peso_inteiro))

        # 3. Remover a tabela antiga
        cursor.execute("DROP TABLE weights")

        # 4. Renomear a tabela nova
        cursor.execute("ALTER TABLE weights_temp RENAME TO weights")

        conn.commit()
        print("[✔] Coluna 'weight' convertida com sucesso para INTEGER.")
    except Exception as e:
        print(f"[ERRO] Falha na conversão: {e}")
    finally:
        conn.close()

# Executar o código
converter_pesos_para_inteiros()
