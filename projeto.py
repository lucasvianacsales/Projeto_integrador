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


def extrair_linhas(dados):
    linhas = []

    for var in dados:
        for resultado in var.get("resultados", []):
            classes = {}

            for c in resultado.get("classificacoes", []):
                nome = c.get("nome")
                categoria = c.get("categoria", {})
                if categoria:
                    # Evita depender de "pegar o primeiro valor" (ordem do dict pode variar)
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


@st.cache_data(show_spinner=False)
def buscar_tabela(ano_inicial, ano_final, estado):
    linhas_totais = []

    if estado == "Todos":
        localidades = "N3[all]"
    else:
        codigo = UFS[estado]
        localidades = f"N3[{codigo}]"

    for ano in range(ano_inicial, ano_final + 1):
        url = (
            f"https://servicodados.ibge.gov.br/api/v3/agregados/647/"
            f"periodos/{ano}01-{ano}12/variaveis/51"
            f"?localidades={localidades}&classificacao=314[all]|41[all]"
        )

        response = requests.get(url, timeout=60)
        response.raise_for_status()

        try:
            dados = response.json()
        except ValueError as e:
            # response.json() falha quando a resposta não é JSON válido
            raise requests.exceptions.RequestException(f"Resposta inválida (não JSON): {e}")
        linhas_totais.extend(extrair_linhas(dados))

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
    st.caption("Consulta por período e estado (ou todos).")

    with st.sidebar:
        st.header("Filtros")

        ano_inicial = st.selectbox(
            "Ano inicial",
            list(range(2010, 2027)),
            index=10
        )

        ano_final = st.selectbox(
            "Ano final",
            list(range(2010, 2027)),
            index=15
        )

        estado = st.selectbox(
            "Estado",
            ["Todos"] + list(UFS.keys()),
            index=1
        )

        buscar = st.button("Buscar tabela")

    if buscar:
        if ano_inicial > ano_final:
            st.error("Ano inicial não pode ser maior que o final.")
            return

        with st.spinner("Consultando API..."):
            try:
                df = buscar_tabela(ano_inicial, ano_final, estado)

                if df.empty:
                    st.warning("Nenhum dado encontrado.")
                else:
                    st.dataframe(df, use_container_width=True)

            except requests.exceptions.RequestException as e:
                st.error(f"Erro na API: {e}")


if __name__ == "__main__":
    main()