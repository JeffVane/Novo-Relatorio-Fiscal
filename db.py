import sqlite3


# --------------------------------
# Conexão com o banco de dados
# --------------------------------

def connect_db():
    """Conecta ao banco de dados SQLite e retorna a conexão."""
    return sqlite3.connect(r'\\192.168.0.120\BancoSiaFisk\application.db')


# --------------------------------
# Criação de tabelas
# --------------------------------

def create_tables():
    """Cria as tabelas necessárias no banco de dados."""
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS procedures (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        meta_cfc INTEGER DEFAULT 0,
        meta_crcdf INTEGER DEFAULT 0
    );
''')


    # 🔹 Criar tabela de pesos para procedimentos
    cursor.execute('''
            CREATE TABLE IF NOT EXISTS weights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                procedure_id INTEGER UNIQUE NOT NULL,
                weight REAL NOT NULL DEFAULT 1,
                FOREIGN KEY (procedure_id) REFERENCES procedures(id) ON DELETE CASCADE
            );
        ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS agendamentos_procedimentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_conclusao TEXT,
            numero_agendamento TEXT,
            fiscal TEXT,
            tipo_registro TEXT,
            numero_registro TEXT,
            nome TEXT,
            procedimento TEXT,
            quantidade INTEGER
        );
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS agendamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_conclusao TEXT,
            numero_agendamento TEXT,
            fiscal TEXT,
            tipo_registro TEXT,
            numero_registro TEXT,
            nome TEXT
        );
    ''')

    # Criar tabela de usuários (se não existir)
    cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'visitante',
                is_admin INTEGER DEFAULT 0,  -- 0 = Usuário comum, 1 = Admin
                is_fiscal INTEGER DEFAULT 0 -- 0 =Não é Fiscal, 1 = Fiscal   
            );
        ''')

    cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_permissions (
                user_id INTEGER,
                tab_name TEXT NOT NULL,
                allowed INTEGER DEFAULT 1,  -- 1 = Pode ver a aba, 0 = Não pode
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
        ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS grupos_procedimentos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome_grupo TEXT NOT NULL
    );
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS grupo_itens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            grupo_id INTEGER NOT NULL,
            procedimento_id INTEGER NOT NULL,
            FOREIGN KEY (grupo_id) REFERENCES grupos_procedimentos(id),
            FOREIGN KEY (procedimento_id) REFERENCES procedures(id)
        );
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT NOT NULL,
            acao TEXT NOT NULL,
            detalhes TEXT,
            data_hora TEXT NOT NULL DEFAULT (DATETIME('now', 'localtime'))
        );
    ''')

    conn.commit()
    conn.close()
def set_user_permissions(user_id, permissions):
    """ Define as permissões do usuário no banco de dados """
    try:
        conn = connect_db()
        cursor = conn.cursor()

        # Verifica se o usuário existe antes de definir permissões
        cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
        if not cursor.fetchone():
            raise ValueError(f"Usuário com ID {user_id} não encontrado!")

        # Remover permissões antigas antes de inserir as novas
        cursor.execute("DELETE FROM user_permissions WHERE user_id = ?", (user_id,))

        # Inserir novas permissões
        for tab_name, allowed in permissions.items():
            cursor.execute(
                "INSERT INTO user_permissions (user_id, tab_name, allowed) VALUES (?, ?, ?)",
                (user_id, tab_name, int(allowed))
            )

        conn.commit()
        conn.close()
        print(f"[DEBUG] Permissões definidas com sucesso para user_id={user_id}: {permissions}")

    except Exception as e:
        print(f"[ERROR] Falha ao definir permissões: {str(e)}")


# --------------------------------
# Funções para a tabela "weights"
# --------------------------------
def add_or_update_weight(procedure_name, weight):
    """Adiciona ou atualiza o peso de um procedimento pelo nome."""
    try:
        conn = connect_db()
        cursor = conn.cursor()

        # 🔹 Buscar o ID do procedimento pelo nome
        cursor.execute("SELECT id FROM procedures WHERE name = ?", (procedure_name,))
        result = cursor.fetchone()

        if not result:
            print(f"[ERROR] Procedimento '{procedure_name}' não encontrado!")
            return False

        procedure_id = result[0]

        # 🔹 Verificar se o peso já existe para esse procedimento
        cursor.execute("SELECT weight FROM weights WHERE procedure_id = ?", (procedure_id,))
        existing_weight = cursor.fetchone()

        if existing_weight:
            # 🔹 Atualizar o peso existente
            cursor.execute("UPDATE weights SET weight = ? WHERE procedure_id = ?", (weight, procedure_id))
            print(f"[INFO] Peso atualizado para o procedimento '{procedure_name}': {weight}")
        else:
            # 🔹 Inserir um novo peso
            cursor.execute("INSERT INTO weights (procedure_id, weight) VALUES (?, ?)", (procedure_id, weight))
            print(f"[INFO] Peso inserido para o procedimento '{procedure_name}': {weight}")

        conn.commit()
        conn.close()
        return True

    except Exception as e:
        print(f"[ERROR] Erro ao adicionar ou atualizar peso: {e}")
        return False

def get_weights():
    """Retorna todos os pesos cadastrados para os procedimentos."""
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT p.name, w.weight 
            FROM procedures p
            LEFT JOIN weights w ON p.id = w.procedure_id
            ORDER BY p.name ASC
        ''')

        weights = {row[0]: row[1] if row[1] is not None else 1.0 for row in cursor.fetchall()}  # Padrão 1.0 se nulo
        conn.close()
        return weights

    except Exception as e:
        print(f"[ERROR] Erro ao obter os pesos: {e}")
        return {}

def ensure_meta_columns():
    """Adiciona as colunas de metas à tabela procedures se ainda não existirem."""
    try:
        conn = connect_db()
        cursor = conn.cursor()

        # Verificar e adicionar coluna meta_cfc
        cursor.execute("PRAGMA table_info(procedures)")
        columns = [col[1] for col in cursor.fetchall()]

        if "meta_cfc" not in columns:
            cursor.execute("ALTER TABLE procedures ADD COLUMN meta_cfc INTEGER DEFAULT 0")
            print("[INFO] Coluna meta_cfc adicionada à tabela procedures.")

        if "meta_crcdf" not in columns:
            cursor.execute("ALTER TABLE procedures ADD COLUMN meta_crcdf INTEGER DEFAULT 0")
            print("[INFO] Coluna meta_crcdf adicionada à tabela procedures.")

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[ERRO] Falha ao adicionar colunas de meta: {e}")




def get_user_id(username):
    """ Obtém o ID do usuário pelo nome """
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()

    if user:
        print(f"[DEBUG] ID do usuário '{username}': {user[0]}")
        return user[0]
    else:
        print(f"[ERROR] Usuário '{username}' não encontrado no banco de dados!")
        return None  # 🔹 Retorna None se o usuário não for encontrado


def get_user_permissions(user_id):
    """ Retorna as permissões do usuário no formato { 'Atribuir': True, 'Relatório de Atribuições': False, ... } """
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("SELECT tab_name, allowed FROM user_permissions WHERE user_id = ?", (user_id,))
    rows = cursor.fetchall()

    permissions = {row[0]: bool(row[1]) for row in rows}

    conn.close()
    print(f"[DEBUG] Permissões carregadas do banco: {permissions}")  # Debug para verificar se está vindo certo
    return permissions



# --------------------------------
# Funções para usuários
# --------------------------------
import sqlite3
from PyQt5.QtWidgets import QMessageBox


def add_user(username, password, is_admin=0, is_fiscal=0):
    """ Adiciona um novo usuário ao banco de dados e cria uma tabela específica para seus procedimentos. """
    conn = connect_db()
    cursor = conn.cursor()
    try:
        print(f"[DEBUG] Tentando adicionar usuário: {username}, Admin: {is_admin}, Fiscal: {is_fiscal}")

        # Inserir o usuário na tabela principal de usuários
        cursor.execute("INSERT INTO users (username, password, is_admin, is_fiscal) VALUES (?, ?, ?, ?)",
                       (username, password, int(is_admin), int(is_fiscal)))  # ✅ Convertendo para inteiro
        conn.commit()

        # Criar uma tabela específica para esse usuário com nome dinâmico
        sanitized_username = username.replace(" ", "_").lower()  # Evita espaços e caracteres problemáticos
        table_name = f"procedimentos_{sanitized_username}"

        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS {table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data_conclusao TEXT,
                numero_agendamento TEXT,
                fiscal TEXT,
                tipo_registro TEXT,
                numero_registro TEXT,
                nome TEXT,
                procedimento TEXT,
                quantidade INTEGER
            )
        ''')

        conn.commit()
        print(f"[DEBUG] Usuário {username} adicionado e tabela '{table_name}' criada!")

    except sqlite3.IntegrityError:
        print(f"[ERROR] O usuário '{username}' já existe!")
        raise
    except Exception as e:
        print(f"[ERROR] Erro ao adicionar usuário: {str(e)}")
        raise
    finally:
        conn.close()

def add_meta_columns_to_procedures():
    conn = connect_db()
    cursor = conn.cursor()

    try:
        # Verifica se as colunas já existem antes de tentar adicionar
        cursor.execute("PRAGMA table_info(procedures)")
        colunas = [col[1] for col in cursor.fetchall()]

        if 'meta_cfc' not in colunas:
            cursor.execute("ALTER TABLE procedures ADD COLUMN meta_cfc INTEGER DEFAULT 0")
            print("[INFO] Coluna 'meta_cfc' adicionada com sucesso.")

        if 'meta_crcdf' not in colunas:
            cursor.execute("ALTER TABLE procedures ADD COLUMN meta_crcdf INTEGER DEFAULT 0")
            print("[INFO] Coluna 'meta_crcdf' adicionada com sucesso.")

        conn.commit()
    except Exception as e:
        print(f"[ERRO] Falha ao adicionar colunas: {e}")
    finally:
        conn.close()

def check_login(username, password):
    """ Verifica login e retorna os dados do usuário se válido. """
    conn = connect_db()
    cursor = conn.cursor()

    # Buscar os campos is_admin, is_fiscal e role
    cursor.execute("SELECT id, is_admin, is_fiscal, role FROM users WHERE username = ? AND password = ?", (username, password))
    user = cursor.fetchone()

    conn.close()

    if user:
        is_admin = bool(user[1])
        is_fiscal = bool(user[2])
        is_visitor = user[3] == "visitante"  # 🔹 Aqui garantimos que o visitante seja corretamente identificado

        print(f"[DEBUG] Usuário autenticado: {username}, Admin: {is_admin}, Fiscal: {is_fiscal}, Visitante: {is_visitor}")

        return {
            "id": user[0],
            "username": username,
            "is_admin": is_admin,
            "is_fiscal": is_fiscal,
            "is_visitor": is_visitor
        }

    print(f"[ERROR] Login inválido para usuário: {username}")
    return None



def get_users():
    """Retorna uma lista de usuários cadastrados."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM users")
    users = [row[0] for row in cursor.fetchall()]
    conn.close()
    return users


# --------------------------------
# Funções para Procedimentos
# --------------------------------

def add_procedure(name, description):
    """Adiciona um novo procedimento."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO procedures (name, description) VALUES (?, ?)', (name, description))
    conn.commit()
    conn.close()

def registrar_log(usuario, acao, detalhes=""):
    """Registra uma ação no log com data e hora."""
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO logs (usuario, acao, detalhes)
            VALUES (?, ?, ?)
        ''', (usuario, acao, detalhes))
        conn.commit()
        conn.close()
        print(f"[LOG] {usuario} - {acao} - {detalhes}")
    except Exception as e:
        print(f"[ERRO LOG] Falha ao registrar log: {e}")



def get_procedures():
    """Consulta a tabela 'procedures' e retorna uma lista de procedimentos únicos"""
    try:
        conn = sqlite3.connect(r'\\192.168.0.120\public\Bancodeteste\application.db')
        cursor = conn.cursor()

        query = "SELECT DISTINCT id, name FROM procedures"
        cursor.execute(query)

        rows = cursor.fetchall()
        procedures = [{"id": row[0], "name": row[1]} for row in rows]

        conn.close()

        print(f"Procedimentos carregados: {procedures}")  # Debug para verificar se há duplicação
        return procedures

    except Exception as e:
        print(f"Erro ao obter procedimentos: {e}")
        return []





def update_procedure(id, name, description):
    """Atualiza um procedimento existente."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE procedures SET name = ?, description = ? WHERE id = ?', (name, description, id))
    conn.commit()
    conn.close()


def delete_procedure(id):
    """Deleta um procedimento pelo ID."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM procedures WHERE id = ?', (id,))
    conn.commit()
    conn.close()


def add_procedures_if_not_exists():
    """Adiciona procedimentos padrão caso não existam."""
    existing_procedures = get_procedures()
    existing_names = {procedure[1] for procedure in existing_procedures}

    new_procedures = [
        "DECORES (POR DECLARAÇÃO)",
            "NBCTG 1002 (POR CONJUNTO DE DEMONSTRAÇÕES): PROJETO 2001",
            "NBCTG 1001 (POR CONJUNTO DE DEMONSTRAÇÕES): PROJETO 2001",
            "NBCTG 1000 E NBCTG 26 (POR CONJUNTO DE DEMONSTRAÇÕES): PROJETO 2001",
            "RELATÓRIO (E PROCEDIMENTOS) DE AUDITORIA DE ACORDO COM AS NBCS (POR RELATÓRIO)",
            "LAUDO PERICIAL DE ACORDO COM AS NBCS (POR LAUDO)",
            "REGISTRO (1 PROFISSIONAL RAIS/CAGED PF) (POR AGENDAMENTO)",
            "REGISTRO (CNAE PJ) (POR AGENDAMENTO)",
            "REGISTRO (BAIXADO)",
            "REGISTRO (ORGANIZAÇÃO CONTÁBIL/SÓCIOS E FUNCIONÁRIOS) (POR AGENDAMENTO)",
            "FALTA DE ESCRITURAÇÃO (LIVROS OBRIGATÓRIOS) (POR CLIENTE)",
            "COMUNICAÇÃO",
            "REPRESENTAÇÃO",
            "DENÚNCIA",
            "NBCTG 1002 (POR CONJUNTO DE DEMONSTRAÇÕES): PROJETO 2002",
            "NBCTG 1001 (POR CONJUNTO DE DEMONSTRAÇÕES): PROJETO 2002",
            "NBCTG 1000 E NBCTG 26 (POR CONJUNTO DE DEMONSTRAÇÕES): PROJETO 2002",
            "ENTIDADES DESPORTIVAS PROFISSIONAIS (ANÁLISE DEMONSTRAÇÕES CONTÁBEIS DE ACORDO COM AS NBCS - ITG 2003)",
            "ÓRGÃOS PÚBLICOS (ANÁLISE DEMONSTRAÇÕES CONTÁBEIS DE ACORDO COM AS NBCS - NBCTSP)",
            "ENTIDADE FECHADA DE PREVIDÊNCIA COMPLEMENTAR (ANÁLISE DEMONSTRAÇÕES CONTÁBEIS DE ACORDO COM AS NBCS - ITG 2001)",
            "COOPERATIVAS (ANÁLISE DEMONSTRAÇÕES CONTÁBEIS DE ACORDO COM AS NBCS - ITG 2004)",
            "ENTIDADES SEM FINS LUCRATIVOS (ANÁLISE DEMONSTRAÇÕES CONTÁBEIS DE ACORDO COM AS NBCS - ITG 2002)",
            "REGISTRO DE RT DE ORGANIZAÇÃO NÃO CONTÁBIL (PROFISSIONAL/ORGANIZAÇÃO CONTÁBIL) (POR AGENDAMENTO)",
            "CANCELADO"
    ]

    for procedure_name in new_procedures:
        if procedure_name not in existing_names:
            add_procedure(procedure_name, '')


# --------------------------------
# Funções para Agendamentos
# --------------------------------

def insert_agendamento(data_conclusao, numero_agendamento, fiscal, tipo_registro, numero_registro, nome):
    """Insere um novo agendamento no banco de dados."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO agendamentos (data_conclusao, numero_agendamento, fiscal, tipo_registro, numero_registro, nome) 
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (data_conclusao, numero_agendamento, fiscal, tipo_registro, numero_registro, nome))
    conn.commit()
    conn.close()


def assign_procedure(username, agendamento_data, procedures_quantities):
    """
    Atribui os procedimentos selecionados a um agendamento específico
    e os salva na tabela correspondente ao usuário.
    """
    try:
        if not username:
            raise ValueError("O nome do usuário não foi fornecido.")

        if not agendamento_data:
            raise ValueError("Os dados do agendamento não foram fornecidos.")

        if not procedures_quantities:
            raise ValueError("Nenhum procedimento foi selecionado para atribuição.")

        sanitized_username = username.replace(" ", "_").lower()  # Normaliza nome do usuário para nome da tabela
        table_name = f"procedimentos_{sanitized_username}"

        print(f"[DEBUG] Salvando procedimentos para {username} na tabela: {table_name}")

        conn = sqlite3.connect(r'\\192.168.0.120\public\Bancodeteste\application.db')
        cursor = conn.cursor()

        # Criar a tabela do usuário caso não exista
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS {table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data_conclusao TEXT,
                numero_agendamento TEXT,
                fiscal TEXT,
                tipo_registro TEXT,
                numero_registro TEXT,
                nome TEXT,
                procedimento TEXT,
                quantidade INTEGER
            )
        ''')

        for procedure_name, quantity in procedures_quantities:
            # 🔹 Verifica se já existe esse procedimento cadastrado no mesmo agendamento
            cursor.execute(f'''
                SELECT COUNT(*) FROM {table_name} 
                WHERE numero_agendamento = ? AND procedimento = ?
            ''', (agendamento_data["Número Agendamento"], procedure_name))

            existing_count = cursor.fetchone()[0]

            if existing_count == 0:
                print(f"[DEBUG] Inserindo: {procedure_name} - Quantidade: {quantity} para {username}")
                cursor.execute(f'''
                    INSERT INTO {table_name} (
                        data_conclusao, numero_agendamento, fiscal, tipo_registro,
                        numero_registro, nome, procedimento, quantidade
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    agendamento_data["Data Conclusão"],
                    agendamento_data["Número Agendamento"],
                    agendamento_data["Fiscal"],
                    agendamento_data["Tipo Registro"],
                    agendamento_data["Número Registro"],
                    agendamento_data["Nome"],
                    procedure_name,
                    quantity
                ))
            else:
                print(
                    f"[INFO] O procedimento '{procedure_name}' já está atribuído ao agendamento {agendamento_data['Número Agendamento']}. Ignorando duplicação.")

        conn.commit()
        conn.close()
        print(f"[SUCESSO] Procedimentos atribuídos ao usuário {username} com sucesso.")

    except sqlite3.IntegrityError as e:
        print(f"[ERRO] Violação de restrição UNIQUE: {e}")
    except Exception as e:
        print(f"[ERRO] Falha ao atribuir procedimentos: {e}")
        raise e


def get_assigned_procedures(username, is_admin):
    """Retorna todos os procedimentos atribuídos.
       Se for admin, retorna todos das tabelas individuais dos usuários.
       Se for usuário comum, retorna apenas os seus.
    """
    conn = connect_db()
    cursor = conn.cursor()

    if is_admin:
        # 🔹 Buscar todas as tabelas com nome "procedimento_{username}"
        cursor.execute("SELECT username FROM users")
        users = cursor.fetchall()

        all_data = []
        for user in users:
            sanitized_username = user[0].replace(" ", "_").lower()
            table_name = f"procedimento_{sanitized_username}"

            # Verificar se a tabela do usuário existe
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
            if cursor.fetchone():
                # Pega os dados dessa tabela
                cursor.execute(f"""
                    SELECT data_conclusao, numero_agendamento, fiscal, tipo_registro, 
                           numero_registro, nome, procedimento, quantidade     
                    FROM {table_name}
                    ORDER BY data_conclusao DESC
                """)
                all_data.extend(cursor.fetchall())

        conn.close()
        print(f"[DEBUG] Total de registros carregados para admin: {len(all_data)}")  # 🔹 Log
        return all_data

    else:
        # 🔹 Se for usuário comum, filtra apenas pela tabela dele
        sanitized_username = username.replace(" ", "_").lower()
        table_name = f"procedimento_{sanitized_username}"

        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
        if cursor.fetchone():
            cursor.execute(f"""
                SELECT data_conclusao, numero_agendamento, fiscal, tipo_registro, 
                       numero_registro, nome, procedimento, quantidade     
                FROM {table_name}
                ORDER BY data_conclusao DESC
            """)
            data = cursor.fetchall()
        else:
            data = []  # Nenhum procedimento atribuído ainda

        conn.close()
        print(f"[DEBUG] Total de registros carregados para {username}: {len(data)}")  # 🔹 Log
        return data


# --------------------------------
# Inicialização do Banco de Dados
# --------------------------------

def grant_admin_permissions():
    """ Garante que o usuário 'admin' tenha acesso a todas as abas. """
    conn = connect_db()
    cursor = conn.cursor()

    # Verificar se o admin já existe
    cursor.execute("SELECT id FROM users WHERE username = 'admin'")
    admin = cursor.fetchone()

    if admin:
        admin_id = admin[0]

        # Definir permissões para todas as abas
        abas = [
            "Atribuir",
            "Relatório de Atribuições",
            "Resultados do Fiscal",
            "Resultado Mensal",
            "Administração",
            "Log de Ações"
        ]

        # Apagar permissões antigas para evitar duplicações
        cursor.execute("DELETE FROM user_permissions WHERE user_id = ?", (admin_id,))

        # Inserir novas permissões
        for aba in abas:
            cursor.execute("INSERT INTO user_permissions (user_id, tab_name, allowed) VALUES (?, ?, ?)",
                           (admin_id, aba, 1))

        conn.commit()
        print("[DEBUG] Permissões do admin foram corrigidas!")

    conn.close()


def reset_user_data():
    conn = sqlite3.connect(r'\\192.168.0.120\public\Bancodeteste\application.db')
    cursor = conn.cursor()

    # Pega os nomes das tabelas que começam com 'procedimentos'
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'procedimentos%'")
    tables = [row[0] for row in cursor.fetchall()]

    for table in tables:
        cursor.execute(f"DELETE FROM {table}")

    cursor.execute("DELETE FROM weights")

    conn.commit()
    conn.close()
# Criar banco de dados e garantir permissões do admin
if __name__ == "__main__":
    create_tables()
    ensure_meta_columns()  # ← aqui
    add_procedures_if_not_exists()
    add_user("admin", "123456", 1)  # ✅ Corrigido: Passando '1' como inteiro
    grant_admin_permissions()  # Garantir que ele tenha todas as permissões




