from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable

# Pasta onde os sequenciamentos são salvos quando o usuário aperta ENTER
# na pergunta do caminho base.
CAMINHO_PADRAO = Path(r"D:\UFRJ - BioDossel\Demultiplexing\Baixando")

# Imagem do Primer R usada quando o usuário aperta ENTER na pergunta do
# Primer R.
PRIMER_R_PADRAO = Path(r"D:\UFRJ - BioDossel\Demultiplexing\BIM-PrimerR-658_Blue-PCR.jpg")

# Locality sugerida quando ainda não há nenhuma salva de uma execução
# anterior.
LOCALIDADE_PADRAO = "BR-AM-Careiro-Rod254-km17MonteHorebe-cascade"

# O que o usuário digita, em qualquer pergunta, para voltar à anterior.
COMANDO_VOLTAR = "<"


# -------------------------------------------------------------------- #
# UTILITÁRIOS DE CAMINHO                                               #
# -------------------------------------------------------------------- #


def pasta_do_programa() -> Path:
    """Pasta onde os caches locais são gravados: ao lado do .exe quando
    empacotado (o __file__ aponta para a pasta temporária do PyInstaller,
    apagada ao fechar o programa) ou ao lado dos .py no código-fonte."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def limpar_caminho(texto: str) -> str:
    """Remove espaços e as aspas que o Windows inclui ao usar "Copiar como
    caminho" (Ctrl+Shift+C) ou ao arrastar um arquivo para o terminal."""
    return texto.strip().strip("\"'").strip()


# -------------------------------------------------------------------- #
# PERGUNTAS COM OPÇÃO DE VOLTAR                                        #
# -------------------------------------------------------------------- #


class Voltar(Exception):
    """Lançada quando o usuário digita COMANDO_VOLTAR numa pergunta."""


def perguntar(mensagem: str, atual: object = None) -> str:
    """Faz uma pergunta ao usuário. Se houver um valor atual (resposta
    anterior ou padrão), ele aparece entre colchetes e ENTER o mantém.
    Lança Voltar se o usuário digitar COMANDO_VOLTAR."""
    if atual not in (None, ""):
        mensagem = f"{mensagem}[{atual}] "

    resposta = input(mensagem).strip()

    if resposta == COMANDO_VOLTAR:
        raise Voltar
    if not resposta and atual is not None:
        return str(atual)
    return resposta


def pedir_texto(mensagem: str, atual: object = None) -> str:
    """Como perguntar(), mas repete a pergunta até receber algo não vazio."""
    while True:
        resposta = perguntar(mensagem, atual)
        if resposta:
            return resposta
        print("❌ Este campo não pode ficar vazio.")


def executar_etapas(etapas: list[Callable[[], None]], pode_voltar_antes: bool = False) -> None:
    """Executa as etapas em ordem. Quando uma etapa lança Voltar, a
    anterior é repetida. Na primeira etapa, Voltar é repassado para quem
    chamou se pode_voltar_antes for True; senão, a etapa é repetida."""
    i = 0
    while i < len(etapas):
        try:
            etapas[i]()
            i += 1
        except Voltar:
            if i > 0:
                i -= 1
            elif pode_voltar_antes:
                raise
            else:
                print("↩ Esta já é a primeira pergunta.")


# -------------------------------------------------------------------- #
# UTILITÁRIOS DE INTERVALO DE PLACAS                                   #
# -------------------------------------------------------------------- #


def parse_intervalo(texto: str) -> set[int] | None:
    """Converte um texto como "1-3,5,7-9" num conjunto de números de placa.
    Retorna None se o texto estiver vazio (= "sem filtro, pega todas")."""
    if not texto.strip():
        return None

    resultado = set()

    for parte in texto.split(","):
        parte = parte.strip()

        if "-" in parte:
            ini, fim = map(int, parte.split("-"))
            resultado.update(range(ini, fim + 1))
        else:
            resultado.add(int(parte))

    return resultado


def pedir_intervalo(mensagem: str, atual: str | None = None, obrigatorio: bool = True) -> tuple[str, set[int] | None]:
    """Pede um intervalo de placas e repete a pergunta se o texto for
    inválido. Retorna o texto digitado (para reaparecer como valor atual
    se o usuário voltar) e o conjunto de placas."""
    while True:
        texto = perguntar(mensagem, atual)
        if not texto and obrigatorio:
            print("❌ Informe um intervalo (ex: 1-40,50,60-70).")
            continue
        try:
            return texto, parse_intervalo(texto)
        except ValueError:
            print("❌ Intervalo inválido. Use o formato do exemplo: 1-40,50,60-70")


def extrair_numero(nome: str) -> int | None:
    """Extrai os dígitos de uma string (ex: nome de pasta ou de placa) e
    os converte para int. Retorna None se não houver nenhum dígito."""
    numeros = ''.join(filter(str.isdigit, nome))
    return int(numeros) if numeros else None
