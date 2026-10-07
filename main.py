from __future__ import annotations

import sys
import traceback
import getpass
from pathlib import Path

from export_forms_media import form_pcr, form_eletroforese, form_rack, resolver_asset_uids
from utils import CAMINHO_PADRAO, limpar_caminho, parse_intervalo
from data_exter import organizar_dados
from report import create_report

# O console padrão do Windows costuma usar um codepage legado (ex: cp1252),
# que não sabe codificar os emojis usados nas mensagens abaixo — sem isso,
# qualquer print com emoji derruba o programa com UnicodeEncodeError.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")


# -------------------------------------------------------------------- #
# FUNÇÕES AUXILIARES                                                   #
# -------------------------------------------------------------------- #


def pausar(mensagem: str = "\nPressione ENTER para fechar...") -> None:
    """Bloqueia a execução até o usuário apertar ENTER (evita que a
    janela do .exe feche sozinha antes de dar tempo de ler o resultado)."""
    input(mensagem)


def pedir_caminho_base() -> Path | None:
    """Pede o caminho base ao usuário e valida se existe, oferecendo
    criá-lo caso não exista. Retorna None se o usuário cancelar."""
    padrao = CAMINHO_PADRAO

    print(f"\nCaminho padrão: {padrao}")
    entrada = input("Informe o caminho base para salvar os arquivos (ou ENTER para usar o padrão): ")
    entrada = limpar_caminho(entrada)

    if not entrada:
        caminho = padrao
    else:
        caminho = Path(entrada)

    if not caminho.exists():
        print(f"⚠️  Caminho não encontrado: {caminho}")
        criar = input("Deseja criar a pasta? (s/n): ").strip().lower()
        if criar == "s":
            caminho.mkdir(parents=True, exist_ok=True)
            print(f"✔ Pasta criada: {caminho}")
        else:
            print("❌ Operação cancelada.")
            return None

    return caminho


# -------------------------------------------------------------------- #
# EXECUÇÃO DO PIPELINE                                                 #
# -------------------------------------------------------------------- #


def main() -> None:
    """Executa o pipeline completo: download dos formulários do
    KoboToolbox, organização dos arquivos externos e relatório final."""
    try:
        print("--- DATA BIODOSSEL ---\n")

        # ---- ETAPA 1: CAMINHO BASE ---- #
        base = pedir_caminho_base()
        if base is None:
            return

        # ---- ETAPA 2: DADOS DE ENTRADA ---- #
        seq = input("\nInforme o código do sequenciamento (ex: Seq001): ").strip()

        if not seq:
            print("❌ Código do sequenciamento não pode ser vazio.")
            return

        destino = base / seq
        print(f"\n📁 Os arquivos serão salvos em:\n   {destino}\n")

        username = input("Usuário do KoboToolbox: ").strip()
        password = getpass.getpass("Senha do KoboToolbox: ")

        # ---- ETAPA 3: INTERVALO DE PLACAS ---- #
        intervalo_input = input("Informe o intervalo de placas (ex: 1-40,50,60-70) ou ENTER para todas: ").strip()
        intervalo = parse_intervalo(intervalo_input)

        # ---- ETAPA 4: RESOLUÇÃO DOS FORMULÁRIOS ---- #
        # Resolve os formulários do KoboToolbox agora (pode pedir para você
        # escolher qual é qual, na primeira vez), para que o download em
        # seguida rode sem precisar de mais nenhuma interação.
        try:
            uids = resolver_asset_uids(username, password)
        except Exception as e:
            print(f"\n❌ Erro ao identificar os formulários no KoboToolbox: {e}")
            traceback.print_exc()
            return

        # ---- ETAPA 5: DOWNLOAD DOS FORMULÁRIOS ---- #
        print("\n[1/3] Baixando formulários...")

        # Cada formulário roda isolado: se um falhar persistentemente (ex:
        # queda de rede longa demais para as retentativas internas), os
        # outros dois ainda são tentados, em vez de abortar tudo junto.
        formularios_com_erro = []
        for nome_formulario, funcao_formulario in (
            ("PCR", form_pcr),
            ("Eletroforese", form_eletroforese),
            ("Rack", form_rack),
        ):
            try:
                funcao_formulario(username, password, seq, intervalo, base, asset_uid=uids[nome_formulario.lower()])
            except Exception as e:
                print(f"\n❌ Erro na etapa de exportação ({nome_formulario}): {e}")
                traceback.print_exc()
                formularios_com_erro.append(nome_formulario)

        if formularios_com_erro:
            print(f"\n⚠️  Os seguintes formulários falharam e foram pulados: {', '.join(formularios_com_erro)}")
            print("   Rode o programa novamente para tentar baixá-los.")

        # ---- ETAPA 6: ORGANIZAÇÃO DOS ARQUIVOS ---- #
        print("\n[2/3] Distribuindo arquivos externos...")

        try:
            organizar_dados(seq, base)
        except Exception as e:
            print(f"\n❌ Erro na organização: {e}")
            traceback.print_exc()
            return

        # ---- ETAPA 7: RELATÓRIO FINAL ---- #
        print("\n[3/3] Gerando relatório final...")

        try:
            create_report(seq, intervalo, base)
        except Exception as e:
            print(f"\n❌ Erro no relatório final: {e}")
            traceback.print_exc()

        print("\n✅ Pipeline finalizado com sucesso!")
        print(f"📂 Arquivos salvos em: {destino}")

    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        traceback.print_exc()

    finally:
        pausar("\nPressione ENTER para fechar...")


if __name__ == "__main__":
    main()
