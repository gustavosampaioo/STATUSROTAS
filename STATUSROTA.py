import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import json

# Configuração da página
st.set_page_config(
    page_title="Sistema de Gerenciamento de POPs e Rotas",
    page_icon="📊",
    layout="wide"
)

# Inicialização do banco de dados
def init_db():
    conn = sqlite3.connect('pops_rotas.db')
    c = conn.cursor()
    
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
            FOREIGN KEY (pop_id) REFERENCES pops (id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Funções para operações no banco de dados
def add_pop(nome_pop, localizacao, capacidade):
    conn = sqlite3.connect('pops_rotas.db')
    c = conn.cursor()
    c.execute('INSERT INTO pops (nome_pop, localizacao, capacidade) VALUES (?, ?, ?)',
              (nome_pop, localizacao, capacidade))
    conn.commit()
    conn.close()

def get_all_pops():
    conn = sqlite3.connect('pops_rotas.db')
    df = pd.read_sql('''
        SELECT p.*, COUNT(r.id) as quantidade_rotas 
        FROM pops p 
        LEFT JOIN rotas r ON p.id = r.pop_id 
        GROUP BY p.id
    ''', conn)
    conn.close()
    return df

def add_rota(pop_id, nome_rota):
    conn = sqlite3.connect('pops_rotas.db')
    c = conn.cursor()
    c.execute('INSERT INTO rotas (pop_id, nome_rota) VALUES (?, ?)',
              (pop_id, nome_rota))
    conn.commit()
    conn.close()

def get_rotas_by_pop(pop_id):
    conn = sqlite3.connect('pops_rotas.db')
    df = pd.read_sql('SELECT * FROM rotas WHERE pop_id = ?', conn, params=(pop_id,))
    conn.close()
    return df

def update_status_rota(rota_id, novo_status, observacoes=None):
    conn = sqlite3.connect('pops_rotas.db')
    c = conn.cursor()
    c.execute('''
        UPDATE rotas 
        SET status = ?, observacoes = ?, data_atualizacao = CURRENT_TIMESTAMP 
        WHERE id = ?
    ''', (novo_status, observacoes, rota_id))
    conn.commit()
    conn.close()

def delete_pop(pop_id):
    conn = sqlite3.connect('pops_rotas.db')
    c = conn.cursor()
    # Primeiro deleta as rotas associadas
    c.execute('DELETE FROM rotas WHERE pop_id = ?', (pop_id,))
    # Depois deleta o POP
    c.execute('DELETE FROM pops WHERE id = ?', (pop_id,))
    conn.commit()
    conn.close()

def delete_rota(rota_id):
    conn = sqlite3.connect('pops_rotas.db')
    c = conn.cursor()
    c.execute('DELETE FROM rotas WHERE id = ?', (rota_id,))
    conn.commit()
    conn.close()

# Inicializar banco de dados
init_db()

# Interface Streamlit
st.title("📊 Sistema de Gerenciamento de POPs e Rotas")

# Menu lateral
menu = st.sidebar.selectbox(
    "Menu",
    ["Cadastrar POP", "Listar POPs", "Gerenciar Rotas", "Estatísticas"]
)

if menu == "Cadastrar POP":
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
            else:
                st.error("Nome do POP é obrigatório!")

elif menu == "Listar POPs":
    st.header("📋 Lista de POPs")
    
    pops_df = get_all_pops()
    
    if not pops_df.empty:
        # Exibir tabela de POPs
        st.dataframe(pops_df, use_container_width=True)
        
        # Selecionar POP para gerenciar ou excluir
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

elif menu == "Gerenciar Rotas":
    st.header("🛣️ Gerenciar Rotas")
    
    pops_df = get_all_pops()
    
    if not pops_df.empty:
        # Selecionar POP
        pop_options = {f"{row['nome_pop']} (ID: {row['id']})": row['id'] for _, row in pops_df.iterrows()}
        selected_pop = st.selectbox("Selecione um POP:", list(pop_options.keys()))
        pop_id = pop_options[selected_pop]
        
        # Adicionar nova rota
        st.subheader("Adicionar Nova Rota")
        col1, col2 = st.columns([3, 1])
        
        with col1:
            nova_rota = st.text_input("Nome da Nova Rota")
        
        with col2:
            if st.button("➕ Adicionar Rota") and nova_rota:
                add_rota(pop_id, nova_rota)
                st.success(f"Rota '{nova_rota}' adicionada!")
                st.rerun()
        
        # Listar e gerenciar rotas do POP selecionado
        st.subheader(f"Rotas do POP Selecionado")
        rotas_df = get_rotas_by_pop(pop_id)
        
        if not rotas_df.empty:
            for _, rota in rotas_df.iterrows():
                with st.expander(f"🛣️ {rota['nome_rota']} - Status: {rota['status']}"):
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
                            height=100
                        )
                    
                    with col3:
                        if st.button("💾 Salvar", key=f"save_{rota['id']}"):
                            update_status_rota(rota['id'], novo_status, observacoes)
                            st.success("Status atualizado!")
                            st.rerun()
                        
                        if st.button("🗑️ Excluir", key=f"del_{rota['id']}"):
                            delete_rota(rota['id'])
                            st.success("Rota excluída!")
                            st.rerun()
                    
                    st.caption(f"Última atualização: {rota['data_atualizacao']}")
        else:
            st.info("Este POP não possui rotas cadastradas.")
            
    else:
        st.info("Cadastre um POP primeiro para gerenciar rotas.")

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
            st.metric("POP com mais rotas", pops_df.loc[pops_df['quantidade_rotas'].idxmax(), 'nome_pop'])
        
        with col4:
            st.metric("Média de rotas por POP", f"{total_rotas/total_pops:.1f}")
        
        # Gráfico de rotas por POP
        st.subheader("Rotas por POP")
        chart_data = pops_df[['nome_pop', 'quantidade_rotas']].set_index('nome_pop')
        st.bar_chart(chart_data)
        
        # Status das rotas (precisaríamos de uma consulta mais complexa)
        st.subheader("Status das Rotas")
        conn = sqlite3.connect('pops_rotas.db')
        status_df = pd.read_sql('SELECT status, COUNT(*) as count FROM rotas GROUP BY status', conn)
        conn.close()
        
        if not status_df.empty:
            st.dataframe(status_df, use_container_width=True)
        else:
            st.info("Nenhuma rota cadastrada para análise de status.")
        
    else:
        st.info("Nenhum dado disponível para estatísticas.")

# Rodapé
st.sidebar.markdown("---")
st.sidebar.info(
    "Sistema de Gerenciamento de POPs e Rotas\n\n"
    "Status disponíveis:\n"
    "• LANÇAMENTO PENDENTE\n"
    "• LANÇAMENTO FINALIZADO\n" 
    "• FUSÃO PENDENTE\n"
    "• FUSÃO FINALIZADA"
)
