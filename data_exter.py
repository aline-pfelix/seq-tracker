from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Callable

import pandas as pd

from utils import (
    CAMINHO_PADRAO,
    LOCALIDADE_PADRAO,
    PRIMER_R_PADRAO,
    Voltar,
    executar_etapas,
    extrair_numero,
    limpar_caminho,
    pasta_do_programa,
    pedir_intervalo,
    pedir_texto,
    perguntar,
)

LOCALIDADE_CACHE_PATH = pasta_do_programa() / "localidade_cache.json"


# -------------------------------------------------------------------- #
# FUNÇÕES AUXILIARES                                                   #
# -------------------------------------------------------------------- #


def pedir_inteiro(mensagem: str, atual: int | None = None) -> int:
    """Pede um número inteiro positivo ao usuário, repetindo a pergunta
    até receber uma entrada válida (evita crash com ValueError cru)."""
    while True:
        entrada = perguntar(mensagem, atual)
        if entrada.isdigit() and int(entrada) > 0:
            return int(entrada)
        print("❌ Digite um número inteiro maior que zero.")


def pedir_arquivo(mensagem: str, atual: Path | None = None) -> Path:
    """Pede o caminho de um arquivo (aceitando aspas, como no "Copiar como
    caminho" do Windows) e repete a pergunta até o arquivo existir."""
    while True:
        caminho = Path(limpar_caminho(perguntar(mensagem, atual)))
        if caminho != Path("") and caminho.is_file():
            return caminho
        print(f"❌ Arquivo não encontrado: {caminho}")


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


# -------------------------------------------------------------------- #
# PERGUNTAS DA ORGANIZAÇÃO                                             #
# -------------------------------------------------------------------- #


def _pedir_lista(
    titulo_qtd: str,
    anteriores: list[dict[str, Any]],
    etapas_item: Callable[[int, dict[str, Any]], list[Callable[[], None]]],
) -> list[dict[str, Any]]:
    """Pergunta quantos itens (blocos ou siglas) existem e, em seguida, os
    campos de cada um. Voltar a partir do primeiro campo leva de volta à
    pergunta da quantidade; respostas anteriores reaparecem como padrão."""
    while True:
        qtd = pedir_inteiro(titulo_qtd, len(anteriores) or None)
        itens = [dict(item) for item in anteriores[:qtd]]
        itens += [{} for _ in range(qtd - len(itens))]

        etapas = [etapa for i, item in enumerate(itens) for etapa in etapas_item(i, item)]
        try:
            executar_etapas(etapas, pode_voltar_antes=True)
            return itens
        except Voltar:
            anteriores = itens


def _etapas_bloco(i: int, bloco: dict[str, Any]) -> list[Callable[[], None]]:
    def intervalo() -> None:
        print(f"\n--- BLOCO {i+1} ---")
        bloco["intervalo_texto"], bloco["intervalo"] = pedir_intervalo("Intervalo de placas: ", bloco.get("intervalo_texto"))

    def estrato() -> None:
        bloco["estrato"] = pedir_texto("Estrato (2 dígitos): ", bloco.get("estrato"))

    def coleta() -> None:
        bloco["coleta"] = pedir_texto("Coleta (2 dígitos): ", bloco.get("coleta"))

    def data() -> None:
        bloco["data"] = pedir_texto(
            "Collection Date (siga estritamente o formato do exemplo: 06jan2025): ", bloco.get("data")
        )

    def arquivo() -> None:
        bloco["arquivo"] = pedir_arquivo("Etiqueta de coleta: ", bloco.get("arquivo"))

    return [intervalo, estrato, coleta, data, arquivo]


def _etapas_prefixo(i: int, prefixo: dict[str, Any]) -> list[Callable[[], None]]:
    def codigo() -> None:
        print(f"\n--- SIGLA {i+1} ---")
        prefixo["codigo"] = pedir_texto("Sigla da pessoa que realizou a PCR (ex: MA, RR): ", prefixo.get("codigo"))

    def intervalo() -> None:
        prefixo["intervalo_texto"], prefixo["intervalo"] = pedir_intervalo(
            "Intervalo de placas: ", prefixo.get("intervalo_texto")
        )

    return [codigo, intervalo]


def etapas_organizacao(cfg: dict[str, Any]) -> list[Callable[[], None]]:
    """Perguntas da organização dos dados externos (Locality, Primer R,
    blocos e siglas), feitas no início junto com o resto da configuração.
    As respostas ficam em cfg, para uso posterior em organizar_dados."""

    def localidade() -> None:
        atual = cfg.get("localidade") or _carregar_ultima_localidade() or LOCALIDADE_PADRAO
        cfg["localidade"] = pedir_texto("\nLocality (ENTER mantém o valor entre colchetes): ", atual)

    def primer_r() -> None:
        print(f"\nPrimer R padrão: {PRIMER_R_PADRAO}")
        cfg["primer_r"] = pedir_arquivo("Caminho do Primer R (ENTER usa o padrão): ", cfg.get("primer_r", PRIMER_R_PADRAO))

    def blocos() -> None:
        cfg["blocos"] = _pedir_lista(
            "\nQuantos blocos de dados (Um bloco deve ter um único estrato e de um única coleta)? ",
            cfg.get("blocos", []),
            _etapas_bloco,
        )

    def prefixos() -> None:
        cfg["prefixos"] = _pedir_lista(
            "\nQuantas pessoas fizeram PCRs? ",
            cfg.get("prefixos", []),
            _etapas_prefixo,
        )

    return [localidade, primer_r, blocos, prefixos]


def resumo_organizacao(cfg: dict[str, Any]) -> list[str]:
    """Linhas do resumo da configuração da organização, para conferência
    antes de iniciar a corrida."""
    linhas = [
        f"Locality:   {cfg['localidade']}",
        f"Primer R:   {cfg['primer_r']}",
    ]
    for i, b in enumerate(cfg["blocos"], start=1):
        linhas.append(
            f"Bloco {i}:    placas {b['intervalo_texto']} | estrato {b['estrato']} | coleta {b['coleta']}"
            f" | {b['data']} | {b['arquivo'].name}"
        )
    for p in cfg["prefixos"]:
        linhas.append(f"Sigla {p['codigo']}:   placas {p['intervalo_texto']}")
    return linhas


# -------------------------------------------------------------------- #
# ORGANIZAÇÃO DE DADOS EXTERNOS                                        #
# -------------------------------------------------------------------- #


def organizar_dados(seq: str, base: Path | None, cfg: dict[str, Any]) -> None:
    """Distribui o primer R e as etiquetas de coleta pelas pastas de
    placa em base/seq/Dados_imagens, e gera a planilha de metadados
    (SampleID, Locality, Collection Date) de cada uma, usando as
    respostas coletadas por etapas_organizacao."""
    if base is None:
        base = CAMINHO_PADRAO

    BASE = base / seq / "Dados_imagens"

    if not BASE.exists():
        print(f"❌ Pasta não encontrada: {BASE}")
        return

    print(f"\n📂 Pasta encontrada: {BASE}")

    localidade = cfg["localidade"]
    primer_r = cfg["primer_r"]
    blocos = cfg["blocos"]
    prefixos = cfg["prefixos"]

    _salvar_ultima_localidade(localidade)

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
