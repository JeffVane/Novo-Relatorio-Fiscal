from db import connect_db

def popular_metas_2025():
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("PRAGMA foreign_keys = ON;")

    cursor.execute("""
        INSERT INTO metas_anuais (procedure_id, ano, meta_cfc, meta_crcdf)
        SELECT 
            id,
            2025,
            COALESCE(meta_cfc, 0),
            COALESCE(meta_crcdf, 0)
        FROM procedures
        WHERE name != 'CANCELADO'
        ON CONFLICT(procedure_id, ano) DO NOTHING;
    """)

    conn.commit()
    conn.close()
    print("✅ Metas de 2025 copiadas para a tabela metas_anuais com sucesso.")
