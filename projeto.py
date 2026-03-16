import requests
import pandas as pd
import numpy as np
import time

ufs = [
    11, 12, 13, 14, 15, 16, 17,
    21, 22, 23, 24, 25, 26, 27, 28, 29,
    31, 32, 33, 35,
    41, 42, 43,
    50, 51, 52, 53
]

anos = range(2010, 2026)

todos_dfs = []

for uf in ufs:
    for ano in anos:
        url = (
            f"https://servicodados.ibge.gov.br/api/v3/agregados/647/"
            f"periodos/{ano}01-{ano}12/variaveis/51"
            f"?localidades=N3[{uf}]&classificacao=41[all]|314[all]"
        )

        print(f"Baixando UF {uf} - {ano}...")

        try:
            r = requests.get(url, timeout=120)
            r.raise_for_status()
            dados = r.json()
        except requests.exceptions.RequestException as e:
            print(f"Erro na UF {uf}, ano {ano}: {e}")
            continue

        linhas = []

        for var in dados:
            id_variavel = var["id"]
            nome_variavel = var["variavel"]
            unidade = var.get("unidade")

            for resultado in var["resultados"]:
                classes = {}

                for c in resultado["classificacoes"]:
                    nome_classificacao = c["nome"]
                    valor_classificacao = list(c["categoria"].values())[0]
                    classes[nome_classificacao] = valor_classificacao

                for serie in resultado["series"]:
                    local = serie["localidade"]["nome"]
                    id_local = serie["localidade"]["id"]

                    for periodo, valor in serie["serie"].items():
                        linhas.append({
                            "id_variavel": id_variavel,
                            "variavel": nome_variavel,
                            "unidade": unidade,
                            "id_localidade": id_local,
                            "localidade": local,
                            "periodo": periodo,
                            "valor": valor,
                            **classes
                        })

        if linhas:
            df_parcial = pd.DataFrame(linhas)
            todos_dfs.append(df_parcial)

        time.sleep(0.5)

df = pd.concat(todos_dfs, ignore_index=True)

df["valor"] = df["valor"].replace("..", np.nan)
df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
df = df.dropna(subset=["valor"]).copy()

df["periodo"] = pd.to_datetime(df["periodo"], format="%Y%m")
df["ano"] = df["periodo"].dt.year
df["mes"] = df["periodo"].dt.month

df.to_csv("tabela_647_ufs_2010_2025.csv", index=False, encoding="utf-8-sig")

print(df.head())
print(df.shape)
print("Arquivo salvo com sucesso.")