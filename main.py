from __future__ import annotations

import sys
import traceback
import getpass
from pathlib import Path
from typing import Any

from export_forms_media import form_pcr, form_eletroforese, form_rack, resolver_asset_uids
from utils import (
    CAMINHO_PADRAO,
    COMANDO_VOLTAR,
    Voltar,
    executar_etapas,
    limpar_caminho,
    pedir_intervalo,
    pedir_texto,
    perguntar,
)
from data_exter import etapas_organizacao, organizar_dados, resumo_organizacao
from report import create_report

# O console padrão do Windows costuma usar um codepage legado (ex: cp1252),
# que não sabe codificar os emojis usados nas mensagens abaixo — sem isso,
# qualquer print com emoji derruba o programa com UnicodeEncodeError.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")


class Cancelado(Exception):
    """Lançada quando o usuário desiste da corrida na tela de confirmação."""


# -------------------------------------------------------------------- #
# FUNÇÕES AUXILIARES                                                   #
# -------------------------------------------------------------------- #


def pausar(mensagem: str = "\nPressione ENTER para fechar...") -> None:
    """Bloqueia a execução até o usuário apertar ENTER (evita que a
    janela do .exe feche sozinha antes de dar tempo de ler o resultado)."""
    input(mensagem)


def pedir_caminho_base(atual: Path | None = None) -> Path:
    """Pede o caminho base ao usuário. Se a pasta não existir, pergunta se
    ela deve ser criada (a criação só acontece ao iniciar a corrida)."""
    padrao = atual or CAMINHO_PADRAO

    while True:
        print(f"\nCaminho padrão: {padrao}")
        entrada = limpar_caminho(perguntar("Informe o caminho base para salvar os arquivos (ou ENTER para usar o padrão): "))
        caminho = Path(entrada) if entrada else padrao

        if caminho.exists():
            return caminho

        print(f"⚠️  Caminho não encontrado: {caminho}")
        if perguntar("Deseja criar a pasta? (s/n): ").lower() == "s":
            return caminho


# -------------------------------------------------------------------- #
# CONFIGURAÇÃO DA CORRIDA                                              #
# -------------------------------------------------------------------- #


def configurar_corrida() -> dict[str, Any]:
    """Faz todas as perguntas da corrida de uma vez, antes de qualquer
    download, para que o resto do processo rode sem precisar de ninguém
    no computador. Em qualquer pergunta, COMANDO_VOLTAR volta à anterior.
    Lança Cancelado se o usuário desistir na confirmação."""
    cfg: dict[str, Any] = {}

    def base() -> None:
        cfg["base"] = pedir_caminho_base(cfg.get("base"))

    def seq() -> None:
        cfg["seq"] = pedir_texto("\nInforme o código do sequenciamento (ex: Seq001): ", cfg.get("seq"))

    def usuario() -> None:
        cfg["username"] = pedir_texto("\nUsuário do KoboToolbox: ", cfg.get("username"))

    def senha() -> None:
        # A senha é digitada às cegas, então não há valor atual para manter.
        while True:
            password = getpass.getpass(f"Senha do KoboToolbox ({COMANDO_VOLTAR} para voltar): ")
            if password.strip() == COMANDO_VOLTAR:
                raise Voltar
            if not password:
                print("❌ A senha não pode ficar vazia.")
                continue
            try:
                # Pode pedir para escolher os formulários (só na primeira
                # vez); por isso roda aqui, ainda na fase de perguntas.
                cfg["uids"] = resolver_asset_uids(cfg["username"], password)
            except Exception as e:
                print(f"\n❌ Erro ao acessar o KoboToolbox: {e}")
                print(f"   Digite a senha de novo ou {COMANDO_VOLTAR} para corrigir o usuário.")
                continue
            cfg["password"] = password
            return

    def intervalo() -> None:
        # Sem valor atual: ENTER aqui significa "todas as placas".
        cfg["intervalo_texto"], cfg["intervalo"] = pedir_intervalo(
            "\nInforme o intervalo de placas (ex: 1-40,50,60-70) ou ENTER para todas: ", obrigatorio=False
        )

    def confirmar() -> None:
        print("\n" + "=" * 60)
        print("RESUMO DA CORRIDA")
        print("=" * 60)
        print(f"Salvar em:  {cfg['base'] / cfg['seq']}")
        print(f"Usuário:    {cfg['username']}")
        print(f"Placas:     {cfg['intervalo_texto'] or 'todas'}")
        for linha in resumo_organizacao(cfg):
            print(linha)
        print("=" * 60)

        while True:
            resposta = perguntar(f"\nIniciar a corrida? (s = iniciar / n = cancelar / {COMANDO_VOLTAR} = voltar): ").lower()
            if resposta == "s":
                return
            if resposta == "n":
                raise Cancelado
            print("Opção inválida.")

    print(f"Dica: digite {COMANDO_VOLTAR} em qualquer pergunta para voltar à anterior.")
    executar_etapas([base, seq, usuario, senha, intervalo, *etapas_organizacao(cfg), confirmar])
    return cfg


# -------------------------------------------------------------------- #
# EXECUÇÃO DO PIPELINE                                                 #
# -------------------------------------------------------------------- #


def main() -> None:
    """Executa o pipeline completo: primeiro todas as perguntas, depois,
    sem mais interação, o download dos formulários do KoboToolbox, a
    organização dos arquivos externos e o relatório final."""
    try:
        print("--- DATA BIODOSSEL ---\n")

        # ---- ETAPA 1: CONFIGURAÇÃO (ÚNICA PARTE INTERATIVA) ---- #
        try:
            cfg = configurar_corrida()
        except Cancelado:
            print("\n❌ Corrida cancelada.")
            return

        base, seq, intervalo = cfg["base"], cfg["seq"], cfg["intervalo"]
        username, password, uids = cfg["username"], cfg["password"], cfg["uids"]

        destino = base / seq
        base.mkdir(parents=True, exist_ok=True)
        print(f"\n📁 Os arquivos serão salvos em:\n   {destino}")
        print("\n⏳ A partir daqui não é preciso responder mais nada.")

        # ---- ETAPA 2: DOWNLOAD DOS FORMULÁRIOS ---- #
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

        # ---- ETAPA 3: ORGANIZAÇÃO DOS ARQUIVOS ---- #
        print("\n[2/3] Distribuindo arquivos externos...")

        try:
            organizar_dados(seq, base, cfg)
        except Exception as e:
            print(f"\n❌ Erro na organização: {e}")
            traceback.print_exc()
            return

        # ---- ETAPA 4: RELATÓRIO FINAL ---- #
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
