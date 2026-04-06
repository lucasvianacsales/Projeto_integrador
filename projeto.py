import requests
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Tabela 647 - IBGE", layout="wide")

UFS = {
    "RO": 11, "AC": 12, "AM": 13, "RR": 14, "PA": 15, "AP": 16, "TO": 17,
    "MA": 21, "PI": 22, "CE": 23, "RN": 24, "PB": 25, "PE": 26, "AL": 27,
    "SE": 28, "BA": 29, "MG": 31, "ES": 32, "RJ": 33, "SP": 35,
    "PR": 41, "SC": 42, "RS": 43, "MS": 50, "MT": 51, "GO": 52, "DF": 53
}

if "df_original" not in st.session_state:
    st.session_state.df_original = pd.DataFrame()


def extrair_linhas(dados):
    linhas = []

    for var in dados:
        for resultado in var.get("resultados", []):
            classes = {}

            for c in resultado.get("classificacoes", []):
                nome = c.get("nome")
                categoria = c.get("categoria", {})
                if categoria:
                    valores = list(categoria.values())
                    chave = f"class_{nome}"
                    if len(valores) == 1:
                        classes[chave] = valores[0]
                    else:
                        classes[chave] = "; ".join(map(str, valores))

            for serie in resultado.get("series", []):
                localidade = serie.get("localidade", {})
                local = localidade.get("nome")

                for periodo, valor in serie.get("serie", {}).items():
                    linhas.append({
                        "localidade": local,
                        "periodo": periodo,
                        "valor": valor,
                        **classes,
                    })

    return linhas


def consultar_api(localidades, ano):
    url = (
        f"https://servicodados.ibge.gov.br/api/v3/agregados/647/"
        f"periodos/{ano}01-{ano}12/variaveis/51"
        f"?localidades={localidades}&classificacao=314[all]|41[all]"
    )

    response = requests.get(url, timeout=60)
    response.raise_for_status()
    return response.json()


def buscar_tabela(ano_inicial, ano_final, estado):
    linhas_totais = []

    if estado == "Todos":
        lista_estados = list(UFS.items())
    else:
        lista_estados = [(estado, UFS[estado])]

    total_anos = ano_final - ano_inicial + 1
    total_etapas = len(lista_estados) * total_anos
    etapa_atual = 0

    progress_bar = st.progress(0)
    status_text = st.empty()

    for uf, codigo in lista_estados:
        localidades = f"N3[{codigo}]"

        for ano in range(ano_inicial, ano_final + 1):
            etapa_atual += 1
            progresso = etapa_atual / total_etapas

            status_text.text(f"Consultando {uf} - {ano} ({etapa_atual}/{total_etapas})")
            progress_bar.progress(progresso)

            dados = consultar_api(localidades, ano)
            linhas_totais.extend(extrair_linhas(dados))

    progress_bar.progress(1.0)
    status_text.text("Consulta concluída.")

    df = pd.DataFrame(linhas_totais)

    if not df.empty:
        df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
        df = df.dropna(subset=["valor"])

        df["periodo"] = pd.to_datetime(df["periodo"], format="%Y%m", errors="coerce")
        df = df.dropna(subset=["periodo"])

        df["ano"] = df["periodo"].dt.year.astype(str)
        df["mes"] = df["periodo"].dt.month

        df = df.drop(columns=["periodo"])

    return df


def main():
    st.title("Tabela 647 - IBGE")
    st.caption("Consulta + análise dinâmica dos dados.")

    with st.sidebar:
        st.header("Consulta")

        ano_inicial = st.selectbox("Ano inicial", list(range(2010, 2027)), index=10)
        ano_final = st.selectbox("Ano final", list(range(2010, 2027)), index=15)
        estado = st.selectbox("Estado", ["Todos"] + list(UFS.keys()), index=1)

        buscar = st.button("Buscar dados")

    if buscar:
        if ano_inicial > ano_final:
            st.error("Ano inicial não pode ser maior que o final.")
            return

        try:
            df = buscar_tabela(ano_inicial, ano_final, estado)
            st.session_state.df_original = df

        except requests.exceptions.RequestException as e:
            st.error(f"Erro na API: {e}")
            return
        except Exception as e:
            st.error(f"Erro inesperado: {e}")
            return

    df = st.session_state.df_original

    if df.empty:
        st.info("Faça uma consulta para carregar os dados.")
        return

    st.success(f"{len(df)} linhas carregadas.")
    st.subheader("Base carregada")
    st.dataframe(df, use_container_width=True)

    st.subheader("Filtros de análise")

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        estados_sel = st.multiselect(
            "Estado",
            sorted(df["localidade"].dropna().unique())
        )

    with col2:
        anos_sel = st.multiselect(
            "Ano",
            sorted(df["ano"].dropna().unique())
        )

    with col3:
        meses_sel = st.multiselect(
            "Mês",
            sorted(df["mes"].dropna().unique())
        )

    with col4:
        tipos_sel = st.multiselect(
            "Tipo de projeto",
            sorted(df["class_Tipo de projeto"].dropna().unique())
        )

    with col5:
        padroes_sel = st.multiselect(
            "Padrão de acabamento",
            sorted(df["class_Padrão de acabamento"].dropna().unique())
        )

    df_filtrado = df.copy()

    if estados_sel:
        df_filtrado = df_filtrado[df_filtrado["localidade"].isin(estados_sel)]

    if anos_sel:
        df_filtrado = df_filtrado[df_filtrado["ano"].isin(anos_sel)]

    if meses_sel:
        df_filtrado = df_filtrado[df_filtrado["mes"].isin(meses_sel)]

    if tipos_sel:
        df_filtrado = df_filtrado[df_filtrado["class_Tipo de projeto"].isin(tipos_sel)]

    if padroes_sel:
        df_filtrado = df_filtrado[df_filtrado["class_Padrão de acabamento"].isin(padroes_sel)]

    st.subheader("Indicadores")

    if df_filtrado.empty:
        st.warning("Nenhum dado encontrado com os filtros selecionados.")
        return

    media = df_filtrado["valor"].mean()
    minimo = df_filtrado["valor"].min()
    maximo = df_filtrado["valor"].max()

    c1, c2, c3 = st.columns(3)
    c1.metric("Média", f"{media:,.2f}")
    c2.metric("Mínimo", f"{minimo:,.2f}")
    c3.metric("Máximo", f"{maximo:,.2f}")

    st.subheader("Evolução")

    df_plot = df_filtrado.groupby(["ano", "mes"])["valor"].mean().reset_index()
    df_plot["data"] = pd.to_datetime(
        df_plot["ano"].astype(str) + "-" + df_plot["mes"].astype(str).str.zfill(2) + "-01"
    )
    df_plot = df_plot.sort_values("data")

    st.line_chart(df_plot.set_index("data")["valor"])

    st.subheader("Tabela filtrada")
    st.dataframe(df_filtrado, use_container_width=True)


if __name__ == "__main__":
    main()