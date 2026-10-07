# SeqTracker

Ferramenta de linha de comando para automatizar o fluxo de dados do projeto Biodossel: baixa os formulários do KoboToolbox (PCR, eletroforese e rack de espécimes), organiza as imagens e arquivos externos por placa, e gera um relatório final consolidado em Excel.

## Funcionalidades

- **Download dos formulários** (`export_forms_media.py`, módulo confidencial — ver [Módulo confidencial](#módulo-confidencial)): baixa os formulários de PCR, eletroforese e rack diretamente da API do KoboToolbox, incluindo as imagens anexadas, e organiza tudo em pastas por placa.
- **Organização de dados externos** (`data_exter.py`): distribui arquivos de primer e etiquetas de coleta nas pastas de cada placa, gerando uma planilha de metadados (SampleID, localidade, data de coleta) por placa.
- **Relatório final** (`report.py`): consolida os dados de PCR, eletroforese e rack em uma única planilha Excel, com rendimento médio de amplificação e status de controle negativo.

## Requisitos

- Python 3.8+
- Acesso (usuário/senha) ao KoboToolbox do projeto

## Instalação

```bash
python -m venv venv
venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

## Módulo confidencial

`export_forms_media.py` contém o mecanismo de integração com a API do KoboToolbox (resolução de asset UID, download de submissões e de anexos) e **não é versionado** — não faz parte do repositório.

`export_forms_media.example.py` documenta a interface que `main.py` espera (`resolver_asset_uids`, `form_pcr`, `form_eletroforese`, `form_rack`). Para rodar o projeto a partir do código-fonte, copie esse arquivo para `export_forms_media.py` e implemente cada função com a integração real do seu projeto no KoboToolbox.

## Uso

```bash
python main.py
```

O script solicita interativamente:

1. Caminho base onde os arquivos serão salvos (padrão: `D:\BioDossel\Demultiplixing_Todos_arquivos\Baixando`; o caminho pode ser colado com ou sem aspas)
2. Código do sequenciamento (ex: `Seq001`)
3. Usuário e senha do KoboToolbox
4. Intervalo de placas a processar (ex: `1-40,50,60-70`, ou vazio para todas)
5. Na primeira execução (sem `kobo_uid_cache.json` ainda), qual formulário da conta corresponde a PCR/Eletroforese/Rack
6. Na etapa de organização dos dados (`data_exter.py`), a Locality do sítio de coleta — veja [Caches locais](#caches-locais)

Depois disso, o download dos formulários acontece automaticamente. A etapa de organização dos dados (`data_exter.py`) ainda pede o caminho do Primer R e, para cada bloco de placas, o intervalo, estrato, coleta, data de coleta e etiqueta — além da sigla de quem fez a PCR em cada intervalo de placas. Só depois disso o relatório final é gerado automaticamente.

## Caches locais

Para não pedir os mesmos dados repetidamente, o script salva localmente:

- `kobo_uid_cache.json` — o UID de cada formulário do KoboToolbox, descoberto na primeira execução.
- `localidade_cache.json` — a última Locality informada na organização dos dados; nas execuções seguintes, só pede confirmação (ENTER mantém o valor salvo) em vez de redigitar a string inteira.

## Como citar

Félix, A. P. (2026). *SeqTracker* (Versão 1.3.4) [Software]. https://github.com/aline-pfelix/seq-tracker

## Autora

Aline Félix — felix.aline.p@gmail.com
