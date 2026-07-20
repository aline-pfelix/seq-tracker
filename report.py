from __future__ import annotations

from pathlib import Path

import pandas as pd


# -------------------------------------------------------------------- #
# GERAÇÃO DO RELATÓRIO FINAL                                           #
# -------------------------------------------------------------------- #


def create_report(seq: str, intervalo: set[int] | None = None, base: Path | None = None) -> None:
    """Consolida os formulários exportados de PCR, eletroforese e rack
    (o mais recente de cada) numa única planilha por placa, com
    rendimento médio de amplificação, e salva em base/seq."""
    if base is None:
        base = Path.home() / "Documents" / "Demultiplixing_Todos_arquivos"

    BASE = base / seq
    EXPORT_BASE = BASE / "Formularios_Exportados"

    if not EXPORT_BASE.exists():
        print("❌ Pasta de formulários não encontrada.")
        return

    print(f"\n📂 Lendo formulários em: {EXPORT_BASE}")

    # ---- ETAPA 1: LOCALIZAR ARQUIVOS MAIS RECENTES ---- #
    def get_latest(pattern: str) -> Path | None:
        files = sorted(EXPORT_BASE.glob(pattern))
        return files[-1] if files else None

    pcr_file = get_latest("*PCR*.xlsx")
    eletro_file = get_latest("*eletroforese*.xlsx")
    rack_file = get_latest("*Racks*.xlsx")

    if not all([pcr_file, eletro_file, rack_file]):
        print("❌ Arquivos de formulário não encontrados.")
        return

    # ---- ETAPA 2: LER DADOS ---- #
    df_pcr = pd.read_excel(pcr_file)
    df_eletro = pd.read_excel(eletro_file)
    df_rack = pd.read_excel(rack_file)

    print("✔ Arquivos carregados")

    # ---- ETAPA 3: FUNÇÕES AUXILIARES ---- #
    def tratar_placa(valor: object) -> str | None:
        if pd.isna(valor):
            return None
        return str(valor).replace(" ", "").upper()[:6]

    def tratar_controle(valor: object) -> str:
        if pd.isna(valor):
            return "N/A"
        v = str(valor).lower()
        if v in ["n_o", "nao", "não"]:
            return "NÃO"
        elif v == "sim":
            return "SIM"
        return "N/A"

    def extrair_numero(placa: str | None) -> int | None:
        if placa is None:
            return None
        numeros = ''.join(filter(str.isdigit, placa))
        return int(numeros) if numeros else None

    def dentro_intervalo(placa: str | None) -> bool:
        if not intervalo:
            return True
        num = extrair_numero(placa)
        return num in intervalo if num else False

    # ---- ETAPA 4: PCR (última submissão) ---- #
    df_pcr["placa"] = df_pcr["Informe_placa_e_primer"].apply(tratar_placa)
    df_pcr = df_pcr[df_pcr["placa"].apply(dentro_intervalo)]
    df_pcr = df_pcr.sort_values("_submission_time").drop_duplicates("placa", keep="last")

    dados_pcr = {
        row["placa"]: {
            "Tag": row.get("Tag"),
            "Usuario_PCR": row.get("username"),
            "Data_PCR": row.get("_submission_time")
        }
        for _, row in df_pcr.iterrows()
    }

    # ---- ETAPA 5: ELETROFORESE (última) ---- #
    df_eletro["placa"] = df_eletro["Informe_a_placa_do_gel"].apply(tratar_placa)
    df_eletro = df_eletro[df_eletro["placa"].apply(dentro_intervalo)]
    df_eletro = df_eletro.sort_values("_submission_time").drop_duplicates("placa", keep="last")

    dados_eletro = {}

    for _, row in df_eletro.iterrows():
        total = row.get("N_mero_total_de_amostras_no_gel")
        ampl = row.get("N_mero_de_amostras_amplificadas")

        try:
            rendimento = (float(ampl) * 100) / float(total)
        except (TypeError, ValueError, ZeroDivisionError):
            rendimento = None

        dados_eletro[row["placa"]] = {
            "Total_amostras": total,
            "Amplificadas": ampl,
            "Controle_negativo": tratar_controle(row.get("o_controle_negativo_amplificou")),
            "Rendimento (%)": rendimento,
            "Usuario_Eletro": row.get("username"),
            "Data_Eletro": row.get("_submission_time")
        }

    # ---- ETAPA 6: RACK (última) ---- #
    df_rack["placa"] = df_rack["Informe_o_rack_dos_especimes"].apply(tratar_placa)
    df_rack = df_rack[df_rack["placa"].apply(dentro_intervalo)]
    df_rack = df_rack.sort_values("_submission_time").drop_duplicates("placa", keep="last")

    dados_rack = {
        row["placa"]: {
            "Usuario_Rack": row.get("username"),
            "Data_Rack": row.get("_submission_time")
        }
        for _, row in df_rack.iterrows()
    }

    # ---- ETAPA 7: UNIR TODAS AS PLACAS ---- #
    todas_placas = set(dados_pcr) | set(dados_eletro) | set(dados_rack)

    linhas = []

    for placa in todas_placas:
        linha = {"Placa": placa}

        if placa in dados_pcr:
            linha.update(dados_pcr[placa])

        if placa in dados_eletro:
            linha.update(dados_eletro[placa])

        if placa in dados_rack:
            linha.update(dados_rack[placa])

        linhas.append(linha)

    df_final = pd.DataFrame(linhas)

    # ---- ETAPA 8: TRATAMENTOS FINAIS ---- #
    df_final["Rendimento (%)"] = pd.to_numeric(df_final["Rendimento (%)"], errors="coerce")
    rendimento_medio = df_final["Rendimento (%)"].mean()

    df_final = df_final.sort_values("Placa")
    df_final = df_final.round(2)
    df_final = df_final.fillna("N/A")

    # ---- ETAPA 9: EXPORTAR ---- #
    saida = BASE / f"{seq}_RELATORIO_FINAL.xlsx"

    total_placas = len(df_final)

    with pd.ExcelWriter(saida, engine="openpyxl") as writer:
        df_final.to_excel(writer, index=False, startrow=3)

        ws = writer.book.active
        ws["A1"] = f"Sequenciamento: {seq}"
        ws["A2"] = f"Total de placas do Biodossel: {total_placas}"
        ws["A3"] = f"Rendimento médio (eletroforese): {round(rendimento_medio, 2)}%"

    print(f"\n✅ Relatório final salvo em:\n{saida}")
