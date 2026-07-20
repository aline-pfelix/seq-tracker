from __future__ import annotations

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


def extrair_numero(nome: str) -> int | None:
    """Extrai os dígitos de uma string (ex: nome de pasta ou de placa) e
    os converte para int. Retorna None se não houver nenhum dígito."""
    numeros = ''.join(filter(str.isdigit, nome))
    return int(numeros) if numeros else None
