from __future__ import annotations

from pathlib import Path

# export_forms_media.py é um módulo confidencial (o mecanismo de
# comunicação com a API do KoboToolbox: resolução de asset UID, download
# de submissões e de anexos) e não é versionado.
#
# Este arquivo só documenta a interface que main.py espera, para quem
# for rodar o projeto a partir do código-fonte (não do .exe já
# empacotado). Copie para export_forms_media.py e implemente cada
# função abaixo com a integração real do seu projeto no KoboToolbox.

# -------------------------------------------------------------------- #
# INTERFACE DO MÓDULO CONFIDENCIAL                                     #
# -------------------------------------------------------------------- #


def resolver_asset_uids(username: str, password: str) -> dict[str, str]:
    """Descobre (e idealmente cacheia localmente) o UID de cada
    formulário do KoboToolbox associado à conta informada. Deve
    retornar um dict com as chaves "pcr", "eletroforese" e "rack"."""
    raise NotImplementedError


def form_pcr(
    username: str,
    password: str,
    seq: str,
    intervalo: set[int] | None = None,
    base: Path | None = None,
    asset_uid: str | None = None,
) -> None:
    """Baixa as submissões e imagens do formulário de PCR para
    base/seq, respeitando o intervalo de placas informado."""
    raise NotImplementedError


def form_eletroforese(
    username: str,
    password: str,
    seq: str,
    intervalo: set[int] | None = None,
    base: Path | None = None,
    asset_uid: str | None = None,
) -> None:
    """Baixa as submissões e imagens do formulário de eletroforese para
    base/seq, respeitando o intervalo de placas informado."""
    raise NotImplementedError


def form_rack(
    username: str,
    password: str,
    seq: str,
    intervalo: set[int] | None = None,
    base: Path | None = None,
    asset_uid: str | None = None,
) -> None:
    """Baixa as submissões e imagens do formulário de rack de espécimes
    para base/seq, respeitando o intervalo de placas informado."""
    raise NotImplementedError
