from __future__ import annotations

import json
import shutil
from pathlib import Path

import pandas as pd

from utils import CAMINHO_PADRAO, limpar_caminho, parse_intervalo, extrair_numero

LOCALIDADE_CACHE_PATH = Path(__file__).resolve().parent / "localidade_cache.json"


# -------------------------------------------------------------------- #
# FUNÇÕES AUXILIARES                                                   #
# -------------------------------------------------------------------- #


def pedir_inteiro(mensagem: str) -> int:
    """Pede um número inteiro ao usuário, repetindo a pergunta até
    receber uma entrada válida (evita crash com ValueError cru)."""
    while True:
        entrada = input(mensagem).strip()
        try:
            return int(entrada)
        except ValueError:
            print("❌ Digite um número inteiro válido.")


def pedir_caminho(mensagem: str) -> Path:
    """Pede um caminho de arquivo ao usuário, removendo as aspas que o
    Windows inclui ao usar "Copiar como caminho" (Ctrl+Shift+C)."""
    return Path(limpar_caminho(input(mensagem)))


# -------------------------------------------------------------------- #
# CACHE DE LOCALIDADE                                                  #
# -------------------------------------------------------------------- #


def _carregar_ultima_localidade() -> str | None:
    """Lê a última Locality usada, se houver cache de uma execução
    anterior. Retorna None se não houver cache ou se ele estiver
    corrompido/ilegível."""
    if LOCALIDADE_CACHE_PATH.exists():
        try:
            dados = json.loads(LOCALIDADE_CACHE_PATH.read_text(encoding="utf-8"))
            return dados.get("localidade")
        except (json.JSONDecodeError, OSError):
            return None
    return None


def _salvar_ultima_localidade(localidade: str) -> None:
    """Grava a Locality informada no cache local, para reuso na
    próxima execução."""
    LOCALIDADE_CACHE_PATH.write_text(
        json.dumps({"localidade": localidade}, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def pedir_localidade() -> str | None:
    """Pede a Locality ao usuário. Se já houver uma salva de uma execução
    anterior, oferece ela como padrão (ENTER confirma) em vez de obrigar a
    redigitar a string inteira toda vez. Retorna None se o usuário não
    informar nenhum valor."""
    ultima = _carregar_ultima_localidade()

    if ultima:
        entrada = input(f"\nLocality [{ultima}] (ENTER para manter ou digite uma nova): ").strip()
        localidade = entrada or ultima
    else:
        localidade = input("\nLocality (ex: BR-AM-iranduba-Rod352-km50-cascade): ").strip()

    if not localidade:
        print("❌ Locality não pode ser vazia.")
        return None

    _salvar_ultima_localidade(localidade)
    return localidade


# -------------------------------------------------------------------- #
# ORGANIZAÇÃO DE DADOS EXTERNOS                                        #
# -------------------------------------------------------------------- #


def organizar_dados(seq: str, base: Path | None = None) -> None:
    """Distribui o primer R e as etiquetas de coleta pelas pastas de
    placa em base/seq/Dados_imagens, e gera a planilha de metadados
    (SampleID, Locality, Collection Date) de cada uma."""
    if base is None:
        base = CAMINHO_PADRAO

    BASE = base / seq / "Dados_imagens"

    if not BASE.exists():
        print("❌ Pasta não encontrada.")
        return

    print(f"\n📂 Pasta encontrada: {BASE}")

    # ---- ETAPA 1: LOCALIDADE ---- #
    localidade = pedir_localidade()

    if localidade is None:
        return

    # ---- ETAPA 2: PRIMER R ---- #
    primer_r = pedir_caminho("\nCaminho do Primer R: ")

    if not primer_r.is_file():
        print(f"❌ Primer R não encontrado: {primer_r}")
        return

    # ---- ETAPA 3: BLOCOS ---- #
    blocos = []

    qtd_blocos = pedir_inteiro("\nQuantos blocos de dados (Um bloco deve ter um único estrato e de um única coleta)? ")

    for i in range(qtd_blocos):
        print(f"\n--- BLOCO {i+1} ---")

        intervalo = parse_intervalo(input("Intervalo de placas: ").strip())

        estrato = input("Estrato (2 dígitos): ").strip()
        coleta = input("Coleta (2 dígitos): ").strip()
        data = input("Collection Date (siga estritamente o formato do exemplo: 06jan2025): ").strip()

        arquivo_coleta = pedir_caminho("Etiqueta de coleta: ")

        if not arquivo_coleta.is_file():
            print(f"❌ Arquivo de coleta inválido: {arquivo_coleta}")
            return

        blocos.append({
            "intervalo": intervalo,
            "estrato": estrato,
            "coleta": coleta,
            "data": data,
            "arquivo": arquivo_coleta
        })

    # ---- ETAPA 4: PREFIXOS ---- #
    prefixos = []

    qtd_prefixos = pedir_inteiro("\nQuantas pessoas fizeram PCRs? ")

    for i in range(qtd_prefixos):
        print(f"\n--- SIGLA {i+1} ---")

        codigo = input("Sigla da pessoa que realizou a PCR (ex: MA, RR): ").strip()
        intervalo = parse_intervalo(input("Intervalo de placas: ").strip())

        prefixos.append({
            "codigo": codigo,
            "intervalo": intervalo
        })

    # ---- ETAPA 5: PROCESSAMENTO ---- #
    print("\n🚀 Processando...\n")

    for pasta in sorted(BASE.iterdir()):
        if not pasta.is_dir():
            continue

        num = extrair_numero(pasta.name)
        if num is None:
            continue

        # -------- BLOCO --------
        bloco = next((b for b in blocos if num in b["intervalo"]), None)

        if not bloco:
            print(f"{pasta.name} sem bloco.")
            continue

        # -------- PREFIXO --------
        matches = [p for p in prefixos if num in p["intervalo"]]

        if len(matches) == 0:
            print(f"{pasta.name} sem prefixo.")
            continue

        if len(matches) > 1:
            print(f"❌ {pasta.name} caiu em MAIS DE UM prefixo. Verifique.")
            continue

        pref = matches[0]

        # -------- SAMPLE ID --------
        sample_id = f"BIMCM{bloco['estrato']}{bloco['coleta']}"

        # -------- EXCEL --------
        df = pd.DataFrame([{
            "SampleID": sample_id,
            "Locality": localidade,
            "Collection Date": bloco["data"]
        }])

        nome_excel = f"{pref['codigo']}_{pasta.name}.xlsx"
        df.to_excel(pasta / nome_excel, index=False)

        # -------- ARQUIVOS --------
        shutil.copy2(primer_r, pasta / primer_r.name)
        shutil.copy2(bloco["arquivo"], pasta / bloco["arquivo"].name)

        print(f"✔ {pasta.name} → {nome_excel}")

    print("\n✅ Finalizado!")
