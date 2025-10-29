import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import secrets
from datetime import datetime

# Configuração da página
st.set_page_config(
    page_title="Sistema de Gerenciamento de POPs e Rotas",
    page_icon="📊",
    layout="wide"
)

# Funções de segurança
def hash_password(password):
    """Gera hash da senha"""
    return hashlib.sha256(password.encode()).hexdigest()

def generate_session_token():
    """Gera token de sessão seguro"""
    return secrets.token_hex(32)

# Inicialização do banco de dados
def init_db():
    conn = sqlite3.connect('pops_rotas.db', check_same_thread=False)
    c = conn.cursor()
    
    # Tabela de Usuários
    c.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            nome_completo TEXT NOT NULL,
            matricula TEXT UNIQUE NOT NULL,
            permissao TEXT DEFAULT 'USER',
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ativo INTEGER DEFAULT 1
        )
    ''')
    
    # Tabela de POPs
    c.execute('''
        CREATE TABLE IF NOT EXISTS pops (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_pop TEXT NOT NULL,
            localizacao TEXT,
            capacidade INTEGER,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabela de Cidades
    c.execute('''
        CREATE TABLE IF NOT EXISTS cidades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_cidade TEXT NOT NULL,
            pop_id INTEGER,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (pop_id) REFERENCES pops (id)
        )
    ''')
    
    # Tabela de Rotas
    c.execute('''
        CREATE TABLE IF NOT EXISTS rotas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pop_id INTEGER,
            cidade_id INTEGER,
            nome_rota TEXT NOT NULL,
            status_lancamento TEXT DEFAULT 'PENDENTE',
            status_fusao TEXT DEFAULT 'PENDENTE',
            observacoes_lancamento TEXT,
            observacoes_fusao TEXT,
            status_alimentacao TEXT,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            usuario_atualizacao TEXT,
            FOREIGN KEY (pop_id) REFERENCES pops (id),
            FOREIGN KEY (cidade_id) REFERENCES cidades (id)
        )
    ''')
    
    # Criar usuário admin padrão se não existir
    c.execute('''
        INSERT OR IGNORE INTO usuarios (username, password_hash, nome_completo, matricula, permissao)
        VALUES (?, ?, ?, ?, ?)
    ''', ('admin', hash_password('admin123'), 'Administrador do Sistema', '000000', 'ADMIN'))
    
    conn.commit()
    conn.close()

# Funções para gerenciamento de usuários
def criar_usuario(username, password, nome_completo, matricula, permissao='USER'):
    conn = sqlite3.connect('pops_rotas.db', check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO usuarios (username, password_hash, nome_completo, matricula, permissao)
            VALUES (?, ?, ?, ?, ?)
        ''', (username, hash_password(password), nome_completo, matricula, permissao))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def verificar_login(username, password):
    conn = sqlite3.connect('pops_rotas.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''
        SELECT id, username, nome_completo, permissao, matricula 
        FROM usuarios 
        WHERE username = ? AND password_hash = ? AND ativo = 1
    ''', (username, hash_password(password)))
    usuario = c.fetchone()
    conn.close()
    
    if usuario:
        return {
            'id': usuario[0],
            'username': usuario[1],
            'nome_completo': usuario[2],
            'permissao': usuario[3],
            'matricula': usuario[4]
        }
    return None

def get_all_usuarios():
    conn = sqlite3.connect('pops_rotas.db', check_same_thread=False)
    df = pd.read_sql('''
        SELECT id, username, nome_completo, matricula, permissao, data_criacao 
        FROM usuarios 
        WHERE ativo = 1
    ''', conn)
    conn.close()
    return df

def excluir_usuario(usuario_id):
    conn = sqlite3.connect('pops_rotas.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('UPDATE usuarios SET ativo = 0 WHERE id = ?', (usuario_id,))
    conn.commit()
    conn.close()

# Funções para operações no banco de dados - POPs
def add_pop(nome_pop, localizacao, capacidade):
    conn = sqlite3.connect('pops_rotas.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('INSERT INTO pops (nome_pop, localizacao, capacidade) VALUES (?, ?, ?)',
              (nome_pop, localizacao, capacidade))
    conn.commit()
    conn.close()

def get_all_pops():
    conn = sqlite3.connect('pops_rotas.db', check_same_thread=False)
    df = pd.read_sql('''
        SELECT p.*, COUNT(r.id) as quantidade_rotas 
        FROM pops p 
        LEFT JOIN rotas r ON p.id = r.pop_id 
        GROUP BY p.id
    ''', conn)
    conn.close()
    return df

def delete_pop(pop_id):
    conn = sqlite3.connect('pops_rotas.db', check_same_thread=False)
    c = conn.cursor()
    # Primeiro deleta as rotas associadas
    c.execute('DELETE FROM rotas WHERE pop_id = ?', (pop_id,))
    # Depois deleta as cidades associadas
    c.execute('DELETE FROM cidades WHERE pop_id = ?', (pop_id,))
    # Depois deleta o POP
    c.execute('DELETE FROM pops WHERE id = ?', (pop_id,))
    conn.commit()
    conn.close()

# Funções para operações no banco de dados - Cidades
def add_cidade(nome_cidade, pop_id):
    conn = sqlite3.connect('pops_rotas.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('INSERT INTO cidades (nome_cidade, pop_id) VALUES (?, ?)',
              (nome_cidade, pop_id))
    conn.commit()
    conn.close()

def get_cidades_by_pop(pop_id):
    conn = sqlite3.connect('pops_rotas.db', check_same_thread=False)
    df = pd.read_sql('SELECT * FROM cidades WHERE pop_id = ? ORDER BY nome_cidade', conn, params=(pop_id,))
    conn.close()
    return df

def get_all_cidades():
    conn = sqlite3.connect('pops_rotas.db', check_same_thread=False)
    df = pd.read_sql('''
        SELECT c.*, p.nome_pop 
        FROM cidades c 
        LEFT JOIN pops p ON c.pop_id = p.id 
        ORDER BY p.nome_pop, c.nome_cidade
    ''', conn)
    conn.close()
    return df

def delete_cidade(cidade_id):
    conn = sqlite3.connect('pops_rotas.db', check_same_thread=False)
    c = conn.cursor()
    # Primeiro verifica se existem rotas vinculadas a esta cidade
    c.execute('SELECT COUNT(*) FROM rotas WHERE cidade_id = ?', (cidade_id,))
    count_rotas = c.fetchone()[0]
    
    if count_rotas > 0:
        conn.close()
        return False, f"Não é possível excluir a cidade pois existem {count_rotas} rota(s) vinculada(s) a ela."
    
    # Se não houver rotas vinculadas, exclui a cidade
    c.execute('DELETE FROM cidades WHERE id = ?', (cidade_id,))
    conn.commit()
    conn.close()
    return True, "Cidade excluída com sucesso!"

# Funções para operações no banco de dados - Rotas
def add_rota(pop_id, cidade_id, nome_rota):
    conn = sqlite3.connect('pops_rotas.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('INSERT INTO rotas (pop_id, cidade_id, nome_rota) VALUES (?, ?, ?)',
              (pop_id, cidade_id, nome_rota))
    conn.commit()
    conn.close()

def get_rotas_by_pop(pop_id):
    conn = sqlite3.connect('pops_rotas.db', check_same_thread=False)
    df = pd.read_sql('''
        SELECT r.*, c.nome_cidade, p.nome_pop 
        FROM rotas r 
        LEFT JOIN cidades c ON r.cidade_id = c.id 
        LEFT JOIN pops p ON r.pop_id = p.id 
        WHERE r.pop_id = ? 
        ORDER BY r.data_criacao ASC, r.id ASC
    ''', conn, params=(pop_id,))
    conn.close()
    return df

def get_rotas_by_cidade(cidade_id):
    conn = sqlite3.connect('pops_rotas.db', check_same_thread=False)
    df = pd.read_sql('''
        SELECT r.*, c.nome_cidade, p.nome_pop 
        FROM rotas r 
        LEFT JOIN cidades c ON r.cidade_id = c.id 
        LEFT JOIN pops p ON r.pop_id = p.id 
        WHERE r.cidade_id = ? 
        ORDER BY r.data_criacao ASC, r.id ASC
    ''', conn, params=(cidade_id,))
    conn.close()
    return df

def update_status_rota(rota_id, status_lancamento, status_fusao, observacoes_lancamento=None, observacoes_fusao=None, status_alimentacao=None, usuario=None):
    conn = sqlite3.connect('pops_rotas.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''
        UPDATE rotas 
        SET status_lancamento = ?, status_fusao = ?, observacoes_lancamento = ?, 
            observacoes_fusao = ?, status_alimentacao = ?, 
            data_atualizacao = CURRENT_TIMESTAMP, usuario_atualizacao = ?
        WHERE id = ?
    ''', (status_lancamento, status_fusao, observacoes_lancamento, observacoes_fusao, status_alimentacao, usuario, rota_id))
    conn.commit()
    conn.close()

def delete_rota(rota_id):
    conn = sqlite3.connect('pops_rotas.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('DELETE FROM rotas WHERE id = ?', (rota_id,))
    conn.commit()
    conn.close()

def get_estatisticas_status():
    conn = sqlite3.connect('pops_rotas.db', check_same_thread=False)
    df_lancamento = pd.read_sql('SELECT status_lancamento as status, COUNT(*) as count FROM rotas GROUP BY status_lancamento', conn)
    df_fusao = pd.read_sql('SELECT status_fusao as status, COUNT(*) as count FROM rotas GROUP BY status_fusao', conn)
    conn.close()
    return df_lancamento, df_fusao

# Sistema de autenticação
def login():
    st.sidebar.title("🔐 Login")
    
    with st.sidebar.form("login_form"):
        username = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")
        submitted = st.form_submit_button("Entrar")
        
        if submitted:
            usuario = verificar_login(username, password)
            if usuario:
                st.session_state['usuario'] = usuario
                st.session_state['logado'] = True
                st.session_state['token'] = generate_session_token()
                st.sidebar.success(f"Bem-vindo, {usuario['nome_completo']}!")
                st.rerun()
            else:
                st.sidebar.error("Usuário ou senha inválidos!")

def logout():
    st.session_state.clear()
    st.rerun()

def usuario_eh_admin():
    return st.session_state.get('usuario', {}).get('permissao') == 'ADMIN'

# Inicializar banco de dados
init_db()

# Interface principal
def main():
    # Verificar se usuário está logado
    if 'logado' not in st.session_state or not st.session_state['logado']:
        login()
        return
    
    # Header com informações do usuário
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.title("📊 Sistema de Gerenciamento de POPs e Rotas")
    with col2:
        usuario = st.session_state['usuario']
        st.write(f"**Usuário:** {usuario['nome_completo']}")
    with col3:
        if st.button("🚪 Sair"):
            logout()
    
    st.write(f"**Permissão:** {'Administrador' if usuario_eh_admin() else 'Usuário'} | **Matrícula:** {usuario['matricula']}")
    st.markdown("---")
    
    # Menu baseado na permissão
    if usuario_eh_admin():
        menu_options = ["Cadastrar POP", "Cadastrar Cidade", "Listar POPs", "Listar Cidades", "Gerenciar Rotas", "Visualizar Rotas", "Estatísticas", "Gerenciar Usuários"]
    else:
        menu_options = ["Visualizar Rotas", "Estatísticas"]
    
    menu = st.sidebar.selectbox("Menu", menu_options)
    
    if menu == "Cadastrar POP" and usuario_eh_admin():
        st.header("📝 Cadastrar Novo POP")
        
        with st.form("cadastro_pop"):
            col1, col2 = st.columns(2)
            
            with col1:
                nome_pop = st.text_input("Nome do POP*")
                localizacao = st.text_input("Localização")
            
            with col2:
                capacidade = st.number_input("Capacidade", min_value=1, value=100)
            
            submitted = st.form_submit_button("Cadastrar POP")
            
            if submitted:
                if nome_pop:
                    add_pop(nome_pop, localizacao, capacidade)
                    st.success(f"POP '{nome_pop}' cadastrado com sucesso!")
                    st.rerun()
                else:
                    st.error("Nome do POP é obrigatório!")
    
    elif menu == "Cadastrar Cidade" and usuario_eh_admin():
        st.header("🏙️ Cadastrar Nova Cidade")
        
        pops_df = get_all_pops()
        
        if not pops_df.empty:
            with st.form("cadastro_cidade"):
                col1, col2 = st.columns(2)
                
                with col1:
                    nome_cidade = st.text_input("Nome da Cidade*")
                
                with col2:
                    pop_options = {f"{row['nome_pop']} (ID: {row['id']})": row['id'] for _, row in pops_df.iterrows()}
                    selected_pop = st.selectbox("Selecione o POP*:", list(pop_options.keys()))
                    pop_id = pop_options[selected_pop]
                
                submitted = st.form_submit_button("Cadastrar Cidade")
                
                if submitted:
                    if nome_cidade:
                        add_cidade(nome_cidade, pop_id)
                        st.success(f"Cidade '{nome_cidade}' cadastrada com sucesso no POP '{selected_pop}'!")
                        st.rerun()
                    else:
                        st.error("Nome da cidade é obrigatório!")
        else:
            st.info("Cadastre um POP primeiro para vincular cidades.")
    
    elif menu == "Listar POPs" and usuario_eh_admin():
        st.header("📋 Lista de POPs")
        
        pops_df = get_all_pops()
        
        if not pops_df.empty:
            pops_df_display = pops_df.copy()
            pops_df_display['data_criacao'] = pd.to_datetime(pops_df_display['data_criacao']).dt.strftime('%d/%m/%Y %H:%M')
            
            st.dataframe(pops_df_display, use_container_width=True)
            
            st.subheader("Ações")
            pop_options = {f"{row['nome_pop']} (ID: {row['id']})": row['id'] for _, row in pops_df.iterrows()}
            selected_pop = st.selectbox("Selecione um POP para ações:", list(pop_options.keys()))
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🗑️ Excluir POP Selecionado"):
                    pop_id = pop_options[selected_pop]
                    delete_pop(pop_id)
                    st.success("POP excluído com sucesso!")
                    st.rerun()
            
            with col2:
                if st.button("🔄 Atualizar Lista"):
                    st.rerun()
                    
        else:
            st.info("Nenhum POP cadastrado ainda.")
    
    elif menu == "Listar Cidades" and usuario_eh_admin():
        st.header("🏙️ Lista de Cidades")
        
        cidades_df = get_all_cidades()
        
        if not cidades_df.empty:
            cidades_df_display = cidades_df.copy()
            cidades_df_display['data_criacao'] = pd.to_datetime(cidades_df_display['data_criacao']).dt.strftime('%d/%m/%Y %H:%M')
            
            st.dataframe(cidades_df_display, use_container_width=True)
            
            st.subheader("Ações")
            cidade_options = {f"{row['nome_cidade']} (POP: {row['nome_pop']})": row['id'] for _, row in cidades_df.iterrows()}
            selected_cidade = st.selectbox("Selecione uma cidade para excluir:", list(cidade_options.keys()))
            
            if st.button("🗑️ Excluir Cidade Selecionada"):
                cidade_id = cidade_options[selected_cidade]
                sucesso, mensagem = delete_cidade(cidade_id)
                if sucesso:
                    st.success(mensagem)
                else:
                    st.error(mensagem)
                st.rerun()
                    
        else:
            st.info("Nenhuma cidade cadastrada ainda.")
    
    elif menu == "Gerenciar Rotas" and usuario_eh_admin():
        st.header("🛣️ Gerenciar Rotas")
        
        pops_df = get_all_pops()
        
        if not pops_df.empty:
            # Selecionar POP
            pop_options = {f"{row['nome_pop']} (ID: {row['id']})": row['id'] for _, row in pops_df.iterrows()}
            selected_pop = st.selectbox("Selecione um POP:", list(pop_options.keys()))
            pop_id = pop_options[selected_pop]
            
            # Buscar cidades do POP selecionado
            cidades_df = get_cidades_by_pop(pop_id)
            
            if not cidades_df.empty:
                # Adicionar nova rota
                st.subheader("Adicionar Nova Rota")
                col1, col2, col3 = st.columns([2, 2, 1])
                
                with col1:
                    nome_rota = st.text_input("Nome da Rota*")
                
                with col2:
                    cidade_options = {row['nome_cidade']: row['id'] for _, row in cidades_df.iterrows()}
                    selected_cidade = st.selectbox("Selecione a Cidade*:", list(cidade_options.keys()))
                    cidade_id = cidade_options[selected_cidade]
                
                with col3:
                    if st.button("➕ Adicionar Rota"):
                        if nome_rota:
                            add_rota(pop_id, cidade_id, nome_rota)
                            st.success(f"Rota '{nome_rota}' adicionada para a cidade '{selected_cidade}'!")
                            st.rerun()
                        else:
                            st.error("Digite um nome para a rota!")
                
                # Listar e gerenciar rotas do POP selecionado
                st.subheader(f"Rotas do POP: {selected_pop}")
                rotas_df = get_rotas_by_pop(pop_id)
                
                if not rotas_df.empty:
                    for _, rota in rotas_df.iterrows():
                        with st.expander(f"🛣️ {rota['nome_rota']} - Cidade: {rota['nome_cidade']}"):
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.subheader("📡 Status Lançamento")
                                status_lancamento = st.selectbox(
                                    "Status Lançamento:",
                                    ["PENDENTE", "EM ANDAMENTO", "FINALIZADA"],
                                    key=f"lanc_{rota['id']}",
                                    index=["PENDENTE", "EM ANDAMENTO", "FINALIZADA"].index(rota['status_lancamento'])
                                )
                                
                                if status_lancamento == "EM ANDAMENTO":
                                    observacoes_lancamento = st.text_area(
                                        "Observações Lançamento:",
                                        value=rota['observacoes_lancamento'] if rota['observacoes_lancamento'] else "",
                                        key=f"obs_lanc_{rota['id']}",
                                        height=100,
                                        placeholder="Digite observações sobre o andamento do lançamento..."
                                    )
                                else:
                                    observacoes_lancamento = rota['observacoes_lancamento']
                            
                            with col2:
                                st.subheader("🔗 Status Fusão")
                                status_fusao = st.selectbox(
                                    "Status Fusão:",
                                    ["PENDENTE", "EM ANDAMENTO", "FINALIZADA"],
                                    key=f"fusao_{rota['id']}",
                                    index=["PENDENTE", "EM ANDAMENTO", "FINALIZADA"].index(rota['status_fusao'])
                                )
                                
                                if status_fusao == "EM ANDAMENTO":
                                    st.write("**Status Alimentação:**")
                                    col_btn1, col_btn2 = st.columns(2)
                                    with col_btn1:
                                        if st.button("🟢 ALIMENTADA", key=f"alim_{rota['id']}"):
                                            status_alimentacao = "ALIMENTADA"
                                            update_status_rota(rota['id'], rota['status_lancamento'], status_fusao, 
                                                              rota['observacoes_lancamento'], rota['observacoes_fusao'], 
                                                              status_alimentacao, usuario['username'])
                                            st.success("Status de alimentação atualizado!")
                                            st.rerun()
                                    with col_btn2:
                                        if st.button("🔴 SEM SINAL", key=f"sem_sinal_{rota['id']}"):
                                            status_alimentacao = "SEM SINAL"
                                            update_status_rota(rota['id'], rota['status_lancamento'], status_fusao, 
                                                              rota['observacoes_lancamento'], rota['observacoes_fusao'], 
                                                              status_alimentacao, usuario['username'])
                                            st.success("Status de alimentação atualizado!")
                                            st.rerun()
                                    
                                    # Mostrar status atual da alimentação
                                    if rota['status_alimentacao']:
                                        st.info(f"Status atual: {rota['status_alimentacao']}")
                                    
                                    observacoes_fusao = st.text_area(
                                        "Observações Fusão:",
                                        value=rota['observacoes_fusao'] if rota['observacoes_fusao'] else "",
                                        key=f"obs_fusao_{rota['id']}",
                                        height=100,
                                        placeholder="Digite observações sobre o andamento da fusão..."
                                    )
                                else:
                                    observacoes_fusao = rota['observacoes_fusao']
                                    status_alimentacao = rota['status_alimentacao']
                            
                            # Botões de ação
                            col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])
                            with col_btn1:
                                if st.button("💾 Salvar Alterações", key=f"save_{rota['id']}"):
                                    update_status_rota(rota['id'], status_lancamento, status_fusao, 
                                                      observacoes_lancamento, observacoes_fusao, 
                                                      status_alimentacao, usuario['username'])
                                    st.success("Status atualizado!")
                                    st.rerun()
                            
                            with col_btn2:
                                if st.button("🗑️ Excluir Rota", key=f"del_{rota['id']}"):
                                    delete_rota(rota['id'])
                                    st.success("Rota excluída!")
                                    st.rerun()
                            
                            # Informações da rota
                            if rota['data_criacao']:
                                data_criacao_formatada = pd.to_datetime(rota['data_criacao']).strftime('%d/%m/%Y %H:%M')
                                st.caption(f"Data de criação: {data_criacao_formatada}")
                            
                            if rota['data_atualizacao']:
                                data_atualizacao_formatada = pd.to_datetime(rota['data_atualizacao']).strftime('%d/%m/%Y %H:%M')
                                usuario_atualizacao = rota['usuario_atualizacao'] or 'N/A'
                                st.caption(f"Última atualização: {data_atualizacao_formatada} por {usuario_atualizacao}")
                else:
                    st.info("Este POP não possui rotas cadastradas.")
            else:
                st.info("Este POP não possui cidades cadastradas. Cadastre cidades primeiro.")
                
        else:
            st.info("Cadastre um POP primeiro para gerenciar rotas.")
    
    elif menu == "Visualizar Rotas":
        st.header("👀 Visualizar e Atualizar Rotas")
        
        pops_df = get_all_pops()
        
        if not pops_df.empty:
            pop_options = {f"{row['nome_pop']} (ID: {row['id']})": row['id'] for _, row in pops_df.iterrows()}
            selected_pop = st.selectbox("Selecione um POP para visualizar rotas:", list(pop_options.keys()))
            pop_id = pop_options[selected_pop]
            
            st.subheader(f"Rotas do POP: {selected_pop}")
            rotas_df = get_rotas_by_pop(pop_id)
            
            if not rotas_df.empty:
                st.info(f"Total de rotas encontradas: {len(rotas_df)}")
                
                # Exibir as rotas em expanders
                for _, rota in rotas_df.iterrows():
                    # Criar um badge de status resumido
                    status_lancamento = rota['status_lancamento']
                    status_fusao = rota['status_fusao']
                    
                    # Definir cores para os status
                    cores_lancamento = {
                        "PENDENTE": "🔴",
                        "EM ANDAMENTO": "🟡", 
                        "FINALIZADA": "🟢"
                    }
                    
                    cores_fusao = {
                        "PENDENTE": "🔴",
                        "EM ANDAMENTO": "🟡",
                        "FINALIZADA": "🟢"
                    }
                    
                    with st.expander(f"🛣️ {rota['nome_rota']} - Cidade: {rota['nome_cidade']} - Lançamento: {cores_lancamento[status_lancamento]} {status_lancamento} - Fusão: {cores_fusao[status_fusao]} {status_fusao}", expanded=False):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.subheader("📡 Status Lançamento")
                            status_lancamento = st.selectbox(
                                "Status Lançamento:",
                                ["PENDENTE", "EM ANDAMENTO", "FINALIZADA"],
                                key=f"lanc_view_{rota['id']}",
                                index=["PENDENTE", "EM ANDAMENTO", "FINALIZADA"].index(rota['status_lancamento'])
                            )
                            
                            if status_lancamento == "EM ANDAMENTO":
                                observacoes_lancamento = st.text_area(
                                    "Observações Lançamento:",
                                    value=rota['observacoes_lancamento'] if rota['observacoes_lancamento'] else "",
                                    key=f"obs_lanc_view_{rota['id']}",
                                    height=100,
                                    placeholder="Digite observações sobre o andamento do lançamento..."
                                )
                            else:
                                observacoes_lancamento = rota['observacoes_lancamento']
                        
                        with col2:
                            st.subheader("🔗 Status Fusão")
                            status_fusao = st.selectbox(
                                "Status Fusão:",
                                ["PENDENTE", "EM ANDAMENTO", "FINALIZADA"],
                                key=f"fusao_view_{rota['id']}",
                                index=["PENDENTE", "EM ANDAMENTO", "FINALIZADA"].index(rota['status_fusao'])
                            )
                            
                            if status_fusao == "EM ANDAMENTO":
                                st.write("**Status Alimentação:**")
                                col_btn1, col_btn2 = st.columns(2)
                                with col_btn1:
                                    if st.button("🟢 ALIMENTADA", key=f"alim_view_{rota['id']}"):
                                        status_alimentacao = "ALIMENTADA"
                                        update_status_rota(rota['id'], rota['status_lancamento'], status_fusao, 
                                                          rota['observacoes_lancamento'], rota['observacoes_fusao'], 
                                                          status_alimentacao, usuario['username'])
                                        st.success("Status de alimentação atualizado!")
                                        st.rerun()
                                with col_btn2:
                                    if st.button("🔴 SEM SINAL", key=f"sem_sinal_view_{rota['id']}"):
                                        status_alimentacao = "SEM SINAL"
                                        update_status_rota(rota['id'], rota['status_lancamento'], status_fusao, 
                                                          rota['observacoes_lancamento'], rota['observacoes_fusao'], 
                                                          status_alimentacao, usuario['username'])
                                        st.success("Status de alimentação atualizado!")
                                        st.rerun()
                                
                                # Mostrar status atual da alimentação
                                if rota['status_alimentacao']:
                                    st.info(f"Status atual: {rota['status_alimentacao']}")
                                
                                observacoes_fusao = st.text_area(
                                    "Observações Fusão:",
                                    value=rota['observacoes_fusao'] if rota['observacoes_fusao'] else "",
                                    key=f"obs_fusao_view_{rota['id']}",
                                    height=100,
                                    placeholder="Digite observações sobre o andamento da fusão..."
                                )
                            else:
                                observacoes_fusao = rota['observacoes_fusao']
                                status_alimentacao = rota['status_alimentacao']
                        
                        # Botões de ação
                        col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])
                        with col_btn1:
                            if st.button("💾 Salvar Alterações", key=f"save_view_{rota['id']}"):
                                update_status_rota(rota['id'], status_lancamento, status_fusao, 
                                                  observacoes_lancamento, observacoes_fusao, 
                                                  status_alimentacao, usuario['username'])
                                st.success("Status atualizado!")
                                st.rerun()
                        
                        with col_btn2:
                            if usuario_eh_admin():
                                if st.button("🗑️ Excluir Rota", key=f"del_view_{rota['id']}"):
                                    delete_rota(rota['id'])
                                    st.success("Rota excluída!")
                                    st.rerun()
                        
                        # Informações da rota
                        if rota['data_criacao']:
                            data_criacao_formatada = pd.to_datetime(rota['data_criacao']).strftime('%d/%m/%Y %H:%M')
                            st.caption(f"Data de criação: {data_criacao_formatada}")
                        
                        if rota['data_atualizacao']:
                            data_atualizacao_formatada = pd.to_datetime(rota['data_atualizacao']).strftime('%d/%m/%Y %H:%M')
                            usuario_atualizacao = rota['usuario_atualizacao'] or 'N/A'
                            st.caption(f"Última atualização: {data_atualizacao_formatada} por {usuario_atualizacao}")
                
                # Botão para atualizar a lista
                if st.button("🔄 Atualizar Lista de Rotas"):
                    st.rerun()
                    
            else:
                st.info("Este POP não possui rotas cadastradas.")
        else:
            st.info("Nenhum POP cadastrado no sistema.")
    
    elif menu == "Estatísticas":
        st.header("📈 Estatísticas do Sistema")
        
        pops_df = get_all_pops()
        cidades_df = get_all_cidades()
        df_lancamento, df_fusao = get_estatisticas_status()
        
        if not pops_df.empty:
            col1, col2, col3, col4 = st.columns(4)
            
            total_pops = len(pops_df)
            total_cidades = len(cidades_df) if not cidades_df.empty else 0
            total_rotas = pops_df['quantidade_rotas'].sum()
            
            with col1:
                st.metric("Total de POPs", total_pops)
            
            with col2:
                st.metric("Total de Cidades", total_cidades)
            
            with col3:
                st.metric("Total de Rotas", total_rotas)
            
            with col4:
                if total_pops > 0:
                    media_rotas = total_rotas / total_pops
                    st.metric("Média de rotas por POP", f"{media_rotas:.1f}")
                else:
                    st.metric("Média de rotas por POP", "0")
            
            # Gráfico de rotas por POP
            st.subheader("Rotas por POP")
            if total_rotas > 0:
                chart_data = pops_df[['nome_pop', 'quantidade_rotas']].set_index('nome_pop')
                st.bar_chart(chart_data)
            else:
                st.info("Nenhuma rota cadastrada para exibir gráfico.")
            
            # Status das rotas - Lançamento
            st.subheader("Status de Lançamento das Rotas")
            if not df_lancamento.empty:
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    st.dataframe(df_lancamento, use_container_width=True)
                
                with col2:
                    st.bar_chart(df_lancamento.set_index('status'))
            else:
                st.info("Nenhuma rota cadastrada para análise de status de lançamento.")
            
            # Status das rotas - Fusão
            st.subheader("Status de Fusão das Rotas")
            if not df_fusao.empty:
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    st.dataframe(df_fusao, use_container_width=True)
                
                with col2:
                    st.bar_chart(df_fusao.set_index('status'))
            else:
                st.info("Nenhuma rota cadastrada para análise de status de fusão.")
            
        else:
            st.info("Nenhum dado disponível para estatísticas.")
    
    elif menu == "Gerenciar Usuários" and usuario_eh_admin():
        st.header("👥 Gerenciar Usuários")
        
        tab1, tab2 = st.tabs(["Cadastrar Novo Usuário", "Lista de Usuários"])
        
        with tab1:
            st.subheader("Cadastrar Novo Usuário")
            
            with st.form("cadastro_usuario"):
                col1, col2 = st.columns(2)
                
                with col1:
                    username = st.text_input("Nome de usuário*")
                    nome_completo = st.text_input("Nome completo*")
                    matricula = st.text_input("Matrícula*")
                
                with col2:
                    password = st.text_input("Senha*", type="password")
                    confirm_password = st.text_input("Confirmar senha*", type="password")
                    permissao = st.selectbox("Permissão", ["USER", "ADMIN"])
                
                submitted = st.form_submit_button("Cadastrar Usuário")
                
                if submitted:
                    if not all([username, nome_completo, matricula, password, confirm_password]):
                        st.error("Todos os campos são obrigatórios!")
                    elif password != confirm_password:
                        st.error("As senhas não coincidem!")
                    elif len(password) < 4:
                        st.error("A senha deve ter pelo menos 4 caracteres!")
                    else:
                        if criar_usuario(username, password, nome_completo, matricula, permissao):
                            st.success(f"Usuário '{username}' cadastrado com sucesso!")
                            st.rerun()
                        else:
                            st.error("Erro ao cadastrar usuário. Nome de usuário ou matrícula já existem.")
        
        with tab2:
            st.subheader("Usuários Cadastrados")
            
            usuarios_df = get_all_usuarios()
            
            if not usuarios_df.empty:
                usuarios_df_display = usuarios_df.copy()
                usuarios_df_display['data_criacao'] = pd.to_datetime(usuarios_df_display['data_criacao']).dt.strftime('%d/%m/%Y %H:%M')
                
                st.dataframe(usuarios_df_display, use_container_width=True)
                
                st.subheader("Ações")
                usuario_options = {f"{row['nome_completo']} ({row['username']})": row['id'] for _, row in usuarios_df.iterrows() if row['username'] != 'admin'}
                
                if usuario_options:
                    selected_usuario = st.selectbox("Selecione um usuário para excluir:", list(usuario_options.keys()))
                    
                    if st.button("🗑️ Excluir Usuário Selecionado"):
                        usuario_id = usuario_options[selected_usuario]
                        excluir_usuario(usuario_id)
                        st.success("Usuário excluído com sucesso!")
                        st.rerun()
                else:
                    st.info("Nenhum usuário disponível para exclusão (exceto admin).")
            else:
                st.info("Nenhum usuário cadastrado além do admin.")

# Rodapé
if 'logado' in st.session_state and st.session_state['logado']:
    st.sidebar.markdown("---")
    st.sidebar.info(
        "**Sistema de Gerenciamento de POPs e Rotas**\n\n"
        "**Permissões:**\n"
        "• 👑 ADMIN: Acesso total ao sistema\n"
        "• 👤 USER: Visualizar e atualizar status de rotas\n\n"
        "**Status de Lançamento:**\n"
        "• 🔴 PENDENTE\n"
        "• 🟡 EM ANDAMENTO\n" 
        "• 🟢 FINALIZADA\n\n"
        "**Status de Fusão:**\n"
        "• 🔴 PENDENTE\n"
        "• 🟡 EM ANDAMENTO\n"
        "• 🟢 FINALIZADA\n\n"
        "**Status de Alimentação (quando Fusão em ANDAMENTO):**\n"
        "• 🟢 ALIMENTADA\n"
        "• 🔴 SEM SINAL"
    )

# Executar aplicação
if __name__ == "__main__":
    main()
