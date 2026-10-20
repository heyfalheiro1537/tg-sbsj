# Guia do repositório — TG SBSJ

Este guia registra o que foi construído até 20/10/2026, as decisões tomadas no caminho, como rodar cada parte e o que vem a seguir. É o ponto de partida para quem abre o repositório, inclusive você daqui a três meses.

---

## 1. O que é o trabalho, em uma página

O TG é um trabalho de Design Science Research. Constrói uma arquitetura para dados do lado ar de aeroportos e a avalia por falseamento, com o SBSJ (São José dos Campos) como cenário.

A tese central é esta: **um resultado é auditável quando é derivável de premissas declaradas e retidas.** Uma forma geométrica materializada, como a que o AIXM armazena, é resultado sem premissa: só se compara, não se audita.

A arquitetura tem duas metades:

- **escrita:** um ledger em que só se escreve, encadeado por hash, com transaction-time como única linha do tempo;
- **leitura:** um modelo flexível, do qual cada consumidor extrai só o que precisa (o contrato como lente). O consumidor principal é um ADC gerado do ledger.

Quatro hipóteses sustentam que o modelo é possível:

| | Hipótese | Refutada se |
|---|---|---|
| H1 | Representação: para o uso ADC, primitivos simples geram envoltórias conservadoras dentro da tolerância | algum elemento exigir forma fora dos primitivos |
| H2 | Derivação: todo dado não-premissa é calculado, não armazenado | trocar uma premissa exigir reescrever *seeds* |
| H3 | Auditabilidade: o ledger retém tudo e evidencia adulteração | uma adulteração dentro do modelo de ameaça passar sem detecção |
| H4 | Extração: cada consumidor obtém só o que precisa, a custo viável | o custo crescer com o histórico total |

Uma falha só refuta a tese se a correção exigir violar um princípio da arquitetura. Caso contrário, é falha de implementação: registrada, corrigida e reexecutada.

O plano completo está no documento "Plano do TG — texto e experimento" (Claude Docs).

---

## 2. Estrutura do repositório

```
tg-sbsj/
├── GUIA.md                  este arquivo
├── README.md
├── requirements.txt         dependências Python, versões fixadas
├── ambiente.lock            ambiente em que tudo foi testado
├── docker-compose.yml       PostGIS + Jupyter
├── Dockerfile.jupyter
├── scripts/pg_local.sh      PostgreSQL local, sem Docker
├── protocolo/               protocolo de falseamento CONGELADO (não editar)
│   ├── protocolo.yaml       predições, oráculos e tolerâncias (39 verificações)
│   ├── PROTOCOLO.sha256     hashes do protocolo e dos artefatos que ele cita
│   ├── registrar_hashes.sh
│   ├── derivar_tolerancias.py
│   ├── gabarito/            gabarito geodésico independente (Vincenty)
│   └── adc/                 calibração do ADC e extração de contornos (oráculo de H1)
├── artefato/                o artefato do TG
│   ├── db/                  esquema e consultas SQL
│   ├── tg/                  pacote Python
│   └── tests/               testes do mecanismo (aeródromo fictício)
├── experimento/             a avaliação: o notebook e o que ele usa
│   ├── a_vida_do_sbsj.ipynb notebook narrativo, com as verificações (gerado)
│   ├── montar_notebook.py   fonte do notebook (texto e células)
│   ├── registro.py          protocolo, vereditos e registro de execuções
│   ├── fontes.py            dados do SBSJ, com fonte e papel
│   ├── digitalizacao.py     do desenho do ADC às seeds (ajuste de primitivos)
│   ├── metricas.py          métricas de H1
│   ├── ataques.py           bateria de adulteração de H3
│   ├── escala.py            epílogo de H4 (script separado)
│   ├── figuras.py, apoio.py
└── resultados/
    ├── execucoes.jsonl      registro de todas as execuções (só se acrescenta)
    └── <exec_id>/           vereditos e figuras de cada execução
```

---

## 3. O protocolo de falseamento

### 3.1 O que é e por que está congelado

O protocolo diz, **antes** de executar qualquer coisa, o que se espera observar em cada verificação, contra qual oráculo e com qual tolerância. Se predição e tolerância pudessem mudar depois de ver o resultado, o experimento confirmaria qualquer coisa.

- Estado: **congelado** em 20/10/2026, versão 0.4.
- Âncora: commit `fcfb6a5` na `main`. O hash do `protocolo.yaml` é `dd453c3404ccda5836f8dd81744a613f9dd4f4cb525d7b4f82310440ea38ad9f`.
- **Pendente:** a tag `protocolo-v0.4` no commit `fcfb6a5`. Ela não subiu pela sessão em que o protocolo foi feito; crie pelo GitHub (Releases → Draft a new release → tag `protocolo-v0.4`, alvo `fcfb6a5`).

Depois do congelamento, o protocolo não muda. Uma correção vira nova versão, com motivo, registrada antes de executar a parte que ela afeta. O ato 2 (barreira), por exemplo, vai exigir a v0.5.

### 3.2 Fontes (oráculos)

| | Documento | Edição |
|---|---|---|
| F1 | ADC SBSJ (carta de aeródromo) | AIRAC AMDT 2604A1, 16 APR 26 |
| F2 | AOC SBSJ (carta de obstáculos tipo A) | AIRAC AMDT 2213A1, 29 DEC 22 (só no prólogo) |
| F3 | AIP Brasil, AD 2.12 | eAIP edição 20-2026, 01 OCT 2026 |
| F4 | AIP Brasil, AD 2.13 (distâncias declaradas) | mesma de F3 |

Os arquivos têm o SHA-256 registrado no protocolo.

### 3.3 Como as tolerâncias foram obtidas

Regra do trabalho: **tolerância nunca é escolhida.** Cada uma sai de uma fonte declarada.

- **H2 (precisão de publicação).** Soma, em pior caso, de meia unidade da última casa publicada de cada grandeza de entrada, propagada até a grandeza comparada, mais meia unidade da última casa do valor publicado. As resoluções são as que o PANS-AIM (Doc 10066, App. 2, AD 2.12 e AD 2.13) exige. Resultado: comprimento ±0,919 m, azimute ±0,014°, rumo magnético ±1,009°, ASDA 16 ±1,419 m. O cálculo está em `protocolo/derivar_tolerancias.py`.
- **H1 (contrato e oráculo).** tolerância = max(exatidão do contrato, precisão do oráculo). O ADC está em ~1:21 000, com traço de ~3,5 m no terreno; abaixo de meio traço (1,77 m) a carta não distingue uma forma da outra. Como as exatidões do contrato (0,5 a 1,25 m) ficam abaixo disso, a tolerância de H1a é 1,77 m. Em H1b entra também o erro de georreferenciamento: 0,18 + 1,77 = 1,95 m. As exatidões do PANS-AIM valem a 95% de confiança (Doc 10066, App. 1, nota 7), por isso o desvio de H1 é julgado pelo percentil 95. A contenção continua em 100%, porque ser conservador é propriedade do modelo, não do contrato.
- **H3 (resultado exato).** Detectado ou não, e qual `event_id`.
- **H4 (modelo de custo).** Com custo dominado pela descida no índice, t ∝ ln N, e a inclinação média de ln t contra ln N entre 10³ e 10⁶ é ln 2 / ln 10³ = 0,10. Varredura sequencial daria 1,0.

### 3.4 Como conferir o protocolo

```sh
cd protocolo
sha256sum -c PROTOCOLO.sha256          # os nove arquivos devem dar OK
python3 gabarito/test_geodesia.py      # gabarito contra o caso publicado de Vincenty
python3 derivar_tolerancias.py         # reimprime as tolerâncias de H2
```

O gabarito é validado só no caso publicado Flinders Peak → Buninyong (54 972,271 m). **Ele não deve ser rodado sobre o SBSJ antes da execução do ato 1**, para não antecipar o resultado.

---

## 4. O oráculo de H1: calibração e extração do ADC

O ADC em PDF é vetorial. Dois scripts transformam o desenho em contornos no terreno sem comparar nada com o AIP (portanto, sem antecipar H1).

**`protocolo/adc/calibrar_adc.py`** encontra os tiques da gratícula na moldura (a cada 6"), ajusta a transformação página → lat/lon por mínimos quadrados e mede o resíduo.

- 40 tiques de latitude (resíduo máximo 0,01 m) e 31 de longitude (0,17 m); `r_cal` = 0,18 m.
- Um tique foi excluído pela regra fixada antes (resíduo maior que 5× a mediana): 45°51'06" na borda de baixo, desenhado 7,4 m fora do lugar.
- A gratícula está girada 0,33° em relação à moldura: a carta usa o norte da quadrícula UTM.
- `r_cal` mede a consistência da gratícula, não a fidelidade das feições ao terreno. Esta é o que H1b mede.

**`protocolo/adc/extrair_contornos.py`** extrai pista, faixa, SWY e 33 peças de pavimento, pelo estilo do desenho. Cada contorno guarda o número de trechos (para o limite de primitivos de H1.03).

**Unidade de teste de H1:** cada contorno como a carta o desenha, sem segmentação manual. Um anel dentro de outro do mesmo objeto é furo; as designações (TWY A–E, APN 1–8) só rotulam. Assim nenhum recorte pode ser ajustado ao resultado.

> **Atenção ao usar os contornos.** O campo `enu_m` de `contornos_brutos.geojson` está num plano tangente na altura elipsoidal de THR16 (616,7 m). O motor do artefato usa o plano sobre o elipsoide (h = 0), coerente com as derivações. A diferença de escala é ~1e-4 (até ~0,25 m na ponta da pista). **Compare sempre pela geometria em lat/lon do GeoJSON**, convertida pelo plano do motor, e não pelo `enu_m`. Os arquivos do oráculo estão congelados e não foram alterados.

Para reproduzir (exige `pymupdf`):

```sh
cd protocolo/adc
python3 calibrar_adc.py <caminho>/sbsj_sbsj-adc_adc_20260416_2.pdf
python3 extrair_contornos.py <caminho>/sbsj_sbsj-adc_adc_20260416_2.pdf
```

---

## 5. O artefato

### 5.1 Princípios que o código materializa

- **Só se escreve.** `append_event` é o único ponto de escrita. Nada edita nem apaga eventos.
- **Transaction-time é a única linha do tempo.** O `event_id` (snowflake) carrega o instante do relógio de simulação. O relógio de cada *run* só avança.
- **Nada derivado é armazenado.** O instante sai do `event_id`; o estado sai da dobra dos eventos; comprimento, azimute e distâncias declaradas saem do referencial e das *seeds*. Até o campo `previous` do esquema de agosto saiu, porque o diff se calcula a partir dos estados.
- **Nenhum estado em variável Python.** Toda leitura vem de `reconstruct_state` sobre o banco.

### 5.2 Esquema (`artefato/db/`)

| Tabela | Papel |
|---|---|
| `run` | execução: shard, instante de origem e relógio de simulação |
| `event` | envelope: tipo, `asserted_by`, `owner_ref`, `reason`, `caused_by`, `prev_hash`, `hash` |
| `event_field` | corpo, uma linha por campo: `(path, op, next)`; `op` é `set` ou `removed` |
| `referencial` | corpos de referencial, endereçados pelo conteúdo (`ref_id` = SHA-256 do JCS) |
| `snapshot`, `projecao_cache` | caches; nunca fonte de verdade |

`event_field` repete `run_id` e `feature_id` só para indexar a leitura por (feature, camada), que a série S2 de H4 exige. A FK composta garante que não divergem do envelope.

`02_leitura.sql` traz as consultas da arquitetura como funções: `estado_em` (Q1, com filtro de camada), `ciclos` (Q2), `marca_dagua` (Q4), `ligacao_quebrada` (Q5, só a ligação), mais `viva_em`, `instante_de` e `limite_de`. `03_postgis.sql` é opcional (só no Docker).

### 5.3 Pacote `tg`

| Módulo | O que faz |
|---|---|
| `canonico.py` | JCS (RFC 8785) e SHA-256 |
| `relogio.py` | runs, relógio monotônico, `event_id` snowflake, `instante` e `limite` |
| `ledger.py` | `append_event`, `reconstruct_state`, `ciclos`, `diff`, `marca_dagua`, `verify_chain`, `gravar_snapshot`, `features`, `cabeca` |
| `referencial.py` | validação das três regras, publicação, `Resolvedor` (referentes e *seeds*) |
| `motor.py` | primitivos (ponto, retângulo, coroa conservadora), plano local, `gerar`, `flecha_minima` |
| `derivacoes.py` | comprimento, azimutes, rumo magnético, distâncias declaradas |
| `projecao.py` | seleção × camadas × instante, com cache por marca d'água |

### 5.4 Decisões de arquitetura tomadas nesta etapa

**Seed na forma B (relativa a um referente, ISO 19148).** A *seed* diz de onde mede, não quanto mede: `{elemento, referente, s, o}`. A pista é "de THR16 (s = 0) até THR34 (s = 0)"; o comprimento nunca é escrito. Na forma A (estaca absoluta a partir de uma origem única), `estaca_fim = 2675` seria o comprimento gravado com outro nome, e remedir a THR34 exigiria reescrever a *seed* — exatamente a refutação de H2. Distinção usada no texto: um nó novo sobre o mesmo eixo acrescenta algo (cabeceira deslocada); corrigir um ponto que define o eixo exige referencial novo; uma obra que muda o pavimento justifica DELTA na *seed*.

**Referentes múltiplos.** Qualquer ponto pode ser referente, o que evita a origem única (ruim para aeródromos com várias pistas). Três regras, recusadas na publicação:

1. um referente é georreferenciado (lat, lon) ou relativo (elemento, de, s, o), nunca os dois;
2. os referentes formam um grafo sem ciclos;
3. um ponto sozinho não define direção: um referente relativo é medido ao longo de um elemento linear, a partir de uma das pontas.

O caso de várias pistas entra no texto como motivação de desenho, sem predição: o SBSJ tem uma pista só.

**`caused_by` no envelope.** Aponta para o evento que motivou a escrita (por exemplo, a troca de referencial) e entra no hash. Responde à segunda pergunta do auditor: por que isto mudou.

**t sem ambiguidade.** `reconstruct_state` aceita `event_id` (estado ao fim daquele evento) ou instante (estado ao fim daquele instante, convertido pelo maior `event_id` possível nele). Resolve a tensão "t ambíguo", que estava adiada.

**Plano do motor sobre o elipsoide.** O plano tangente fica em h = 0, coerente com as derivações (geodésica sobre o elipsoide, método fixado no protocolo). Um plano na altura do aeródromo esticaria as distâncias em 1 + h/R.

**Barreira: recusa em vez de adivinhar.** A regra de distâncias declaradas com barreira (ato 2) ainda não está no protocolo. Com uma barreira viva, `distancias_declaradas` levanta `RegraPendente`.

**Rejeições de `append_event`** (violação de forma; nada é escrito): tipo inválido; DELTA ou VOID sem BASELINE vigente; BASELINE sobre feature viva; envelope alterado (`feature_type`, `owner_ref`); VOID sem motivo ou com corpo; `asserted_by` vazio; path malformado; remoção de campo ausente; campo que é folha e prefixo ao mesmo tempo; `caused_by` inexistente; *seed* para referente ou elemento inexistente; troca de referencial que deixaria *seed* órfã; airport apontando para referencial não publicado.

### 5.5 Exemplo de uso

```python
from datetime import datetime, timezone
from tg import banco, ledger, referencial, relogio, motor, derivacoes

conn = banco.conectar()                       # TG_DSN ou postgresql://tg@localhost:54329/tg
run = relogio.novo_run(conn, datetime(2026, 4, 16, tzinfo=timezone.utc))

ref = referencial.publicar(conn, {
    "datum": "SIRGAS2000", "origem_local": "THR16",
    "referentes": {"THR16": {"lat": ..., "lon": ...}, "THR34": {"lat": ..., "lon": ...}},
    "elementos_lineares": {"RWY_16_34": ["THR16", "THR34"]},
})
ledger.append_event(conn, run, "SBSJ", "airport", "BASELINE", asserted_by="DECEA",
                    corpo={"referencial": {"ref_id": ref}})

s = lambda r, s=0, o=0: {"elemento": "RWY_16_34", "referente": r, "s": s, "o": o}
ledger.append_event(conn, run, "SBSJ-RWY", "runway", "BASELINE", asserted_by="DECEA",
                    corpo={"direcoes": {"inicio": "16", "fim": "34"},
                           "geometria": {"primitivos": {"pista": {
                               "tipo": "retangulo", "inicio": s("THR16"), "fim": s("THR34"), "largura": 45}}}})

estado = ledger.reconstruct_state(conn, run, "SBSJ-RWY")
forma, nos = motor.gerar(estado["geometria"], referencial.carregar(conn, ref))
tabela = derivacoes.distancias_declaradas(conn, run)
print(ledger.verify_chain(conn, run))        # [] = cadeia íntegra
```

As coordenadas do SBSJ ficam de fora de propósito: elas entram só no notebook do experimento, depois da tag.

---

## 6. Como rodar

### 6.1 Sem Docker (como foi desenvolvido)

Precisa de PostgreSQL 16 instalado (não precisa de PostGIS) e Python 3.12 ou mais novo.

```sh
pip install -r requirements.txt
scripts/pg_local.sh                     # sobe o Postgres em localhost:54329, usuário tg
cd artefato
python3 -m pytest -q tests              # 39 testes
```

Cada teste cria um banco novo a partir de um modelo com o esquema carregado e o apaga no fim. Para outro servidor, defina `TG_DSN_ADMIN` (conexão ao banco `postgres`) e `TG_DSN` (banco de trabalho).

Parar o Postgres local: `pg_ctl -D .pgdata stop`.

### 6.2 Com Docker

```sh
docker compose up -d                    # PostGIS em localhost:54329 e Jupyter em localhost:8888
docker compose exec jupyter python -m pytest -q artefato/tests
```

O serviço `db` carrega o esquema (incluindo o PostGIS opcional) na primeira subida. **Os arquivos de Docker não foram testados contra um daemon Docker real**: o ambiente de desenvolvimento não tinha um. Rode uma vez antes de depender deles.

### 6.3 Rodar o experimento

O experimento é o notebook `experimento/a_vida_do_sbsj.ipynb`. Ele é gerado por `montar_notebook.py` (para o texto e o código ficarem revisáveis no git) e já vem executado, com as saídas da execução oficial.

```sh
cd experimento
python3 montar_notebook.py               # só se mudar alguma célula
jupyter lab a_vida_do_sbsj.ipynb         # e "Run All"
# ou, sem interface:
python3 -c "import nbformat; from nbclient import NotebookClient as C; nb = nbformat.read('a_vida_do_sbsj.ipynb', 4); C(nb, timeout=3600).execute(); nbformat.write(nb, 'a_vida_do_sbsj.ipynb')"
```

O epílogo (escala) leva alguns minutos; `TG_PULAR_ESCALA=1` pula e marca H4 como não executada. Precisa de `nbformat`, `nbclient`, `ipykernel` e `matplotlib`, além do `requirements.txt`.

Cada execução:

- confere o hash do protocolo contra o commit de congelamento `fcfb6a5` e para se não bater;
- roda os testes do artefato;
- cria um banco só dela (`tg_exp_<exec_id>`), que não é apagado: dá para auditar qualquer execução depois;
- acrescenta em `resultados/execucoes.jsonl` cada verificação (observado, predito, tolerância, veredito) e cada escrita no ledger;
- grava `resultados/<exec_id>/vereditos.json` e as figuras.

O registro nunca é reescrito. Uma falha corrigida continua visível na execução em que aconteceu, como a regra do protocolo exige.

### 6.4 O que os testes cobrem

Todos usam um aeródromo fictício (perto de 10°S 50°W, `tests/cenario_sintetico.py`). Nenhum usa dado do SBSJ, nenhum executa uma verificação do protocolo.

- **Testes de apêndice** (`test_apendice.py`), previstos no plano: campo ausente ≠ null; ciclo de vida (BASELINE → VOID → BASELINE sob o mesmo `feature_id`, sem herança de campos); snapshot igual à reconstrução, em 60 eventos aleatórios com semente fixa.
- **Forma do ledger** (`test_ledger.py`): as 12 rejeições, relógio monotônico, t por instante ou por evento, diff e `caused_by`, JCS, e uma sanidade do hash. A bateria de ataques de H3 é do experimento, não destes testes.
- **Referencial** (`test_referencial.py`): as três regras, `ref_id` endereçado pelo conteúdo, referente relativo, *seed* órfã recusada na escrita e na troca de referencial.
- **Motor** (`test_motor.py`): retângulo, coroa conservadora em 8, 16 e 32 segmentos, LOD que reduz o excesso, `flecha_minima`, e a pista acompanhando a remedição sem escrita em *seed* (no fictício).
- **Derivações e projeção** (`test_derivacoes_projecao.py`): comprimento, azimute e rumo; distâncias declaradas sem nada escrito; recusa com barreira; cache que sobrevive a evento fora da seleção e cai com evento dentro; projeção por camada.

---

## 7. Achados até aqui (material para o capítulo 3)

1. **As duas edições oficiais divergem sem causa registrada.** Da AOC 2213 para o ADC 2604: pista 2676 → 2675 m, SWY 325 → 283 m, faixa 3121 × 300 → 3118 × 280 m, ASDA 3001 → 2958 m. A AOC se declara "dados não precisos". É o prólogo do experimento.
2. **A observação da RWY 34 no AD 2.12 fala em "THR 34 deslocada"**, mas LDA 34 = TORA 34 = 2675 m: não há deslocamento em vigor. A observação está desatualizada ou é inconsistente.
3. **A posição longitudinal da faixa não é publicada.** 3118 − 2675 − 283 = 160 m além de pista + SWY, sem divisão entre as pontas (na AOC eram 60 + 60 m). O próprio PANS-AIM só exige as dimensões da faixa.
4. **O AD 2.12 não traz as coordenadas do fim de pista**, que o PANS-AIM exige.
5. **Um tique da gratícula do ADC está desenhado 7,4 m fora do lugar** (45°51'06", borda de baixo).
6. **O ADC usa o norte da quadrícula UTM**, girado 0,33° em relação ao norte verdadeiro.
7. **A assimetria de casas decimais do AD 2.12 segue o PANS-AIM:** cabeceira de precisão (RWY 16) com elevação e ondulação ao decímetro; não precisão (RWY 34) ao metro.

---

## 8. O que vem a seguir

O experimento é um único notebook narrativo, "a vida do SBSJ contada pelo ledger". Cada ato termina numa célula que compara o observado com a predição do protocolo.

1. **Criar a tag `protocolo-v0.4`** no GitHub. Nada do notebook roda antes disso.
2. **Prólogo:** a pista em modo forma, como o AIXM faria (BASELINE com a AOC 2213, DELTA com o ADC 2604). R1.
3. **Ato 1, fundação AIRAC 2604:** referencial com as cabeceiras do AD 2.12; pista, SWY e faixa como *seeds*; pavimento digitalizado do ADC como entrada; lente ADC (geometria por elemento e tabela de distâncias). Verificações H2.01–H2.14 e H1.01–H1.05. Falta escrever a lente ADC e o ajuste de primitivos aos contornos.
4. **Ato 2, obra:** barreira simulada. Exige antes a regra de distâncias declaradas com barreira, registrada como protocolo v0.5.
5. **Ato 3, restrição temporária:** BASELINE + VOID. R10.
6. **Ato 4, nova medição:** THR34 remedida (cenário já fixado no protocolo). H2.15–H2.19.
7. **Ato 5, auditoria:** as três perguntas do auditor. R8.
8. **Ato 6, adulteração:** a bateria H3.01–H3.10 sobre cópias do banco.
9. **Epílogo, escala:** script separado com ledgers de 10³ a 10⁶ eventos, séries S1 e S2. H4.01–H4.05.

### Em aberto (não bloqueiam a execução)

- Citar no texto os valores de exatidão do Catálogo de Dados Aeronáuticos (PANS-AIM App. 1, arquivo eletrônico à parte do Doc 10066). Não muda veredito, salvo se algum valor passar de 1,77 m (condição registrada no protocolo).
- Âncora externa do hash da cabeça: entra na arquitetura ou fica como limite declarado. As predições de H3 cobrem os dois casos.
- Regra de distâncias declaradas com barreira (ato 2).
- Comparação com BIM: na introdução ou em trabalhos relacionados.

---

## 9. Ressalva

Dados do AIP Brasil (DECEA) usados para pesquisa. O ADC gerado reproduz o conteúdo da carta, não a cartografia do Anexo 4, e não substitui a publicação oficial.
