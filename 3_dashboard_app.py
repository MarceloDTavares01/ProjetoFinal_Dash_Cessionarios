# Dashboard Streamlit - Parquet

import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime
from io import BytesIO

# Configurações gerais
st.set_page_config(page_title="Dashboard Cessionários", layout="wide")
st.title("Dash DinDin JA - Cessão de Crédito INSS - 1º Trimestre 2025")
st.caption(f"Data de Referência: {datetime.today().strftime('%d/%m/%Y')}")

# Caminho da pasta com arquivos Parquet
diretorio = os.path.join(os.path.dirname(__file__), "parquet")

@st.cache_data
def listar_cessionarios(caminho_pasta):
    arquivos = [f for f in os.listdir(caminho_pasta) if f.endswith(".parquet") and f != "RESUMO.parquet"]
    nomes = [os.path.splitext(f)[0] for f in arquivos]
    # Coloca "FORA_DAS_REGRAS" no final, se existir
    nomes_ordenados = sorted([n for n in nomes if n != "FORA_DAS_REGRAS"])  # ordena os outros
    if "FORA_DAS_REGRAS" in nomes:
        nomes_ordenados.append("FORA_DAS_REGRAS")
    return nomes_ordenados

@st.cache_data
def carregar_dados_parquet(caminho_pasta, nome_cessionario):
    caminho_arquivo = os.path.join(caminho_pasta, f"{nome_cessionario}.parquet")
    return pd.read_parquet(caminho_arquivo)

if not os.path.exists(diretorio):
    st.error("Pasta 'parquet' não encontrada. Certifique-se de que os arquivos estejam disponíveis.")
else:
    cessionarios = listar_cessionarios(diretorio)
    aba = st.selectbox("Selecione o Cessionário", cessionarios)

    df = carregar_dados_parquet(diretorio, aba)

    if df.empty:
        st.warning("Nenhum dado disponível para esta carteira.")
    else:
        df["DATA DESEMBOLSO"] = pd.to_datetime(df["DATA DESEMBOLSO"], dayfirst=True, errors='coerce')
        
        # Converter para inteiros (sem ponto decimal)
        if "CD BENEFICIO" in df.columns:
            df["CD BENEFICIO"] = df["CD BENEFICIO"].apply(lambda x: int(x) if pd.notnull(x) else pd.NA).astype("Int64")
        if "TABELA" in df.columns:
            df["TABELA"] = df["TABELA"].apply(lambda x: int(x) if pd.notnull(x) else pd.NA).astype("Int64")
        
        st.divider()
        st.subheader("📍 Filtros Interativos")

        colf1 = st.container()
        with colf1:
            data_min = df["DATA DESEMBOLSO"].min()
            data_max = df["DATA DESEMBOLSO"].max()
            data_range = st.date_input("Data de Desembolso", [data_min, data_max])

        estados = st.multiselect("Estados", sorted(df["ESTADO"].dropna().unique()))
        beneficios = st.multiselect("Códigos de Benefício", sorted(df["CD BENEFICIO"].dropna().unique()))
        tipos_operacao = st.multiselect(
            "Tipo de Operação", 
            options=["NOVO", "REFIN"], 
            default=["NOVO", "REFIN"]
        )
        
        tabelas = sorted(df["TABELA"].dropna().unique())
        modo_tabela = st.radio("Filtro de Tabela", ["Todas", "Incluir algumas", "Excluir algumas"], horizontal=True)

        if modo_tabela == "Incluir algumas":
            filtro_tabelas = st.multiselect("Selecionar Tabelas", tabelas)
        elif modo_tabela == "Excluir algumas":
            filtro_tabelas = st.multiselect("Tabelas a Excluir", tabelas)
        else:
            filtro_tabelas = []

        # Aplicar filtros
        df_filtrado = df.copy()
        if len(data_range) ==2:
            df_filtrado = df_filtrado[(df_filtrado["DATA DESEMBOLSO"] >= pd.to_datetime(data_range[0])) &
                                       (df_filtrado["DATA DESEMBOLSO"] <= pd.to_datetime(data_range[1]))]
        else:
            st.warning("⏳ Aguarde: selecione as duas datas para aplicar o filtro de desembolso.")
        if estados:
            df_filtrado = df_filtrado[df_filtrado["ESTADO"].isin(estados)]
        if beneficios:
            df_filtrado = df_filtrado[df_filtrado["CD BENEFICIO"].isin(beneficios)]
        if tipos_operacao:
            df_filtrado = df_filtrado[df_filtrado["tipo_operacao"].isin(tipos_operacao)]
        if modo_tabela == "Incluir algumas" and filtro_tabelas:
            df_filtrado = df_filtrado[df_filtrado["TABELA"].isin(filtro_tabelas)]
        elif modo_tabela == "Excluir algumas" and filtro_tabelas:
            df_filtrado = df_filtrado[~df_filtrado["TABELA"].isin(filtro_tabelas)]

        st.divider()
        st.subheader("📌 Indicadores da Carteira")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Contratos", len(df_filtrado))
        col2.metric("VP Total", f'R$ {df_filtrado["VP"].sum():,.2f}')
        col3.metric("Idade Média", f'{df_filtrado["IDADE"].mean():.1f} anos')
        col4.metric("% Masculino", f'{(df_filtrado["SEXO"].value_counts(normalize=True).get("M", 0)*100):.1f}%')

        st.divider()
        abas = ["📈 Gráficos", "📂 Exportar Dados"]
        aba1, aba2 = st.tabs(abas)
        cor_azul = ["#1f77b4"]

        with aba1:
            st.subheader("VP por Estado")
            df_estado = df_filtrado.groupby("ESTADO")["VP"].sum().reset_index()
            fig_estado = px.bar(df_estado, x="ESTADO", y="VP", text_auto='.2s', color_discrete_sequence=cor_azul)
            st.plotly_chart(fig_estado, use_container_width=True)

            st.subheader("VP por Código de Benefício")
            df_benef = df_filtrado.groupby("CD BENEFICIO")["VP"].sum().reset_index()
            df_benef["CD BENEFICIO"] = df_benef["CD BENEFICIO"].astype(int)
            fig_benef = px.bar(df_benef, x="CD BENEFICIO", y="VP", text_auto='.2s', color_discrete_sequence=cor_azul)
            st.plotly_chart(fig_benef, use_container_width=True)

        with aba2:
            st.subheader("📂 Exportar Dados Filtrados")
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                df_filtrado.to_excel(writer, index=False, sheet_name="Filtrado")
            buffer.seek(0)
            st.download_button(
                label="📥 Baixar Excel",
                data=buffer,
                file_name=f"dados_filtrados_{aba}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )


















