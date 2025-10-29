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
    
    # Tabela de Rotas
    c.execute('''
        CREATE TABLE IF NOT EXISTS rotas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pop_id INTEGER,
            nome_rota TEXT NOT NULL,
            status TEXT DEFAULT 'LANÇAMENTO PENDENTE',
            observacoes TEXT,
            data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            usuario_atualizacao TEXT,
            FOREIGN KEY (pop_id) REFERENCES pops (id)
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

# Funções para operações no banco de dados
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

def add_rota(pop_id, nome_rota):
    conn = sqlite3.connect('pops_rotas.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('INSERT INTO rotas (pop_id, nome_rota) VALUES (?, ?)',
              (pop_id, nome_rota))
    conn.commit()
    conn.close()

def get_rotas_by_pop(pop_id):
    conn = sqlite3.connect('pops_rotas.db', check_same_thread=False)
    df = pd.read_sql('SELECT * FROM rotas WHERE pop_id = ?', conn, params=(pop_id,))
    conn.close()
    return df

def update_status_rota(rota_id, novo_status, observacoes=None, usuario=None):
    conn = sqlite3.connect('pops_rotas.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''
        UPDATE rotas 
        SET status = ?, observacoes = ?, data_atualizacao = CURRENT_TIMESTAMP, usuario_atualizacao = ?
        WHERE id = ?
    ''', (novo_status, observacoes, usuario, rota_id))
    conn.commit()
    conn.close()

def delete_pop(pop_id):
    conn = sqlite3.connect('pops_rotas.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('DELETE FROM rotas WHERE pop_id = ?', (pop_id,))
    c.execute('DELETE FROM pops WHERE id = ?', (pop_id,))
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
    df = pd.read_sql('SELECT status, COUNT(*) as count FROM rotas GROUP BY status', conn)
    conn.close()
    return df

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

def verificar_autenticacao():
    if 'logado' not in st.session_state or not st.session_state['logado']:
        st.warning("⚠️ Você precisa fazer login para acessar o sistema.")
        login()
        st.stop()

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
        menu_options = ["Cadastrar POP", "Listar POPs", "Gerenciar Rotas", "Estatísticas", "Gerenciar Usuários"]
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
                if st.button("🗑️ Excluir POP Selecionado", type="secondary"):
                    pop_id = pop_options[selected_pop]
                    delete_pop(pop_id)
                    st.success("POP excluído com sucesso!")
                    st.rerun()
            
            with col2:
                if st.button("🔄 Atualizar Lista"):
                    st.rerun()
                    
        else:
            st.info("Nenhum POP cadastrado ainda.")
    
    elif menu == "Gerenciar Rotas" and usuario_eh_admin():
        st.header("🛣️ Gerenciar Rotas")
        
        pops_df = get_all_pops()
        
        if not pops_df.empty:
            pop_options = {f"{row['nome_pop']} (ID: {row['id']})": row['id'] for _, row in pops_df.iterrows()}
            selected_pop = st.selectbox("Selecione um POP:", list(pop_options.keys()))
            pop_id = pop_options[selected_pop]
            
            st.subheader("Adicionar Nova Rota")
            col1, col2 = st.columns([3, 1])
            
            with col1:
                nova_rota = st.text_input("Nome da Nova Rota", placeholder="Digite o nome da rota...")
            
            with col2:
                if st.button("➕ Adicionar Rota", use_container_width=True) and nova_rota:
                    add_rota(pop_id, nova_rota)
                    st.success(f"Rota '{nova_rota}' adicionada!")
                    st.rerun()
                elif st.button("➕ Adicionar Rota", use_container_width=True) and not nova_rota:
                    st.error("Digite um nome para a rota!")
            
            st.subheader(f"Rotas do POP Selecionado")
            rotas_df = get_rotas_by_pop(pop_id)
            
            if not rotas_df.empty:
                for _, rota in rotas_df.iterrows():
                    with st.expander(f"🛣️ {rota['nome_rota']} - Status: {rota['status']}", expanded=False):
                        col1, col2, col3 = st.columns([2, 2, 1])
                        
                        with col1:
                            novo_status = st.selectbox(
                                "Atualizar Status:",
                                [
                                    "LANÇAMENTO PENDENTE",
                                    "LANÇAMENTO FINALIZADO", 
                                    "FUSÃO PENDENTE",
                                    "FUSÃO FINALIZADA"
                                ],
                                key=f"status_{rota['id']}",
                                index=[
                                    "LANÇAMENTO PENDENTE",
                                    "LANÇAMENTO FINALIZADO", 
                                    "FUSÃO PENDENTE",
                                    "FUSÃO FINALIZADA"
                                ].index(rota['status'])
                            )
                        
                        with col2:
                            observacoes = st.text_area(
                                "Observações:",
                                value=rota['observacoes'] if rota['observacoes'] else "",
                                key=f"obs_{rota['id']}",
                                height=100,
                                placeholder="Digite observações sobre esta rota..."
                            )
                        
                        with col3:
                            if st.button("💾 Salvar", key=f"save_{rota['id']}", use_container_width=True):
                                update_status_rota(rota['id'], novo_status, observacoes, usuario['username'])
                                st.success("Status atualizado!")
                                st.rerun()
                            
                            if st.button("🗑️ Excluir", key=f"del_{rota['id']}", use_container_width=True):
                                delete_rota(rota['id'])
                                st.success("Rota excluída!")
                                st.rerun()
                        
                        if rota['data_atualizacao']:
                            data_formatada = pd.to_datetime(rota['data_atualizacao']).strftime('%d/%m/%Y %H:%M')
                            usuario_atualizacao = rota['usuario_atualizacao'] or 'N/A'
                            st.caption(f"Última atualização: {data_formatada} por {usuario_atualizacao}")
            else:
                st.info("Este POP não possui rotas cadastradas.")
                
        else:
            st.info("Cadastre um POP primeiro para gerenciar rotas.")
    
    elif menu == "Visualizar Rotas" and not usuario_eh_admin():
        st.header("👀 Visualizar e Atualizar Rotas")
        
        pops_df = get_all_pops()
        
        if not pops_df.empty:
            pop_options = {f"{row['nome_pop']}": row['id'] for _, row in pops_df.iterrows()}
            selected_pop = st.selectbox("Selecione um POP para visualizar rotas:", list(pop_options.keys()))
            pop_id = pop_options[selected_pop]
            
            st.subheader(f"Rotas do POP: {selected_pop}")
            rotas_df = get_rotas_by_pop(pop_id)
            
            if not rotas_df.empty:
                for _, rota in rotas_df.iterrows():
                    with st.expander(f"🛣️ {rota['nome_rota']} - Status: {rota['status']}", expanded=False):
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            novo_status = st.selectbox(
                                "Atualizar Status:",
                                [
                                    "LANÇAMENTO PENDENTE",
                                    "LANÇAMENTO FINALIZADO", 
                                    "FUSÃO PENDENTE",
                                    "FUSÃO FINALIZADA"
                                ],
                                key=f"user_status_{rota['id']}",
                                index=[
                                    "LANÇAMENTO PENDENTE",
                                    "LANÇAMENTO FINALIZADO", 
                                    "FUSÃO PENDENTE",
                                    "FUSÃO FINALIZADA"
                                ].index(rota['status'])
                            )
                            
                            observacoes = st.text_area(
                                "Observações:",
                                value=rota['observacoes'] if rota['observacoes'] else "",
                                key=f"user_obs_{rota['id']}",
                                height=100,
                                placeholder="Digite observações sobre esta rota..."
                            )
                        
                        with col2:
                            if st.button("💾 Salvar Alterações", key=f"user_save_{rota['id']}", use_container_width=True):
                                update_status_rota(rota['id'], novo_status, observacoes, usuario['username'])
                                st.success("Status atualizado com sucesso!")
                                st.rerun()
                        
                        if rota['data_atualizacao']:
                            data_formatada = pd.to_datetime(rota['data_atualizacao']).strftime('%d/%m/%Y %H:%M')
                            usuario_atualizacao = rota['usuario_atualizacao'] or 'N/A'
                            st.caption(f"Última atualização: {data_formatada} por {usuario_atualizacao}")
            else:
                st.info("Este POP não possui rotas cadastradas.")
        else:
            st.info("Nenhum POP cadastrado no sistema.")
    
    elif menu == "Estatísticas":
        st.header("📈 Estatísticas do Sistema")
        
        pops_df = get_all_pops()
        
        if not pops_df.empty:
            col1, col2, col3, col4 = st.columns(4)
            
            total_pops = len(pops_df)
            total_rotas = pops_df['quantidade_rotas'].sum()
            
            with col1:
                st.metric("Total de POPs", total_pops)
            
            with col2:
                st.metric("Total de Rotas", total_rotas)
            
            with col3:
                if total_rotas > 0:
                    pop_mais_rotas = pops_df.loc[pops_df['quantidade_rotas'].idxmax()]
                    st.metric("POP com mais rotas", f"{pop_mais_rotas['nome_pop']} ({pop_mais_rotas['quantidade_rotas']})")
                else:
                    st.metric("POP com mais rotas", "N/A")
            
            with col4:
                media_rotas = total_rotas / total_pops if total_pops > 0 else 0
                st.metric("Média de rotas por POP", f"{media_rotas:.1f}")
            
            st.subheader("Distribuição de Rotas por POP")
            if total_rotas > 0:
                chart_data = pops_df[['nome_pop', 'quantidade_rotas']].set_index('nome_pop')
                st.bar_chart(chart_data)
            else:
                st.info("Nenhuma rota cadastrada para exibir gráfico.")
            
            st.subheader("Status das Rotas")
            status_df = get_estatisticas_status()
            
            if not status_df.empty:
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    st.dataframe(status_df, use_container_width=True)
                
                with col2:
                    st.bar_chart(status_df.set_index('status'))
            else:
                st.info("Nenhuma rota cadastrada para análise de status.")
            
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
                    
                    if st.button("🗑️ Excluir Usuário Selecionado", type="secondary"):
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
        "**Status disponíveis:**\n"
        "• 🟡 LANÇAMENTO PENDENTE\n"
        "• 🟢 LANÇAMENTO FINALIZADO\n" 
        "• 🟠 FUSÃO PENDENTE\n"
        "• 🔵 FUSÃO FINALIZADA"
    )

# Executar aplicação
if __name__ == "__main__":
    main()
