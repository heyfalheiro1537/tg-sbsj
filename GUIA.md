# Guia do repositório — TG SBSJ

Ponto de partida para quem abre o repositório: o que é o trabalho, como o código está organizado, como rodar e onde cada resultado está. Atualizado em 21/10/2026.

---

## 1. O trabalho, em uma página

**Pergunta.** É possível tornar dados aeroportuários geolocalizados auditáveis — cada valor atribuível, retido, re-derivável e com adulteração evidente —, e quais são os limites dessa garantia?

**Contribuição.** Uma arquitetura baseada em *event sourcing* para dados de infraestrutura aeroportuária, com três ideias:

- **um ledger em que só se escreve**, encadeado por hash: nada se apaga, tudo tem autor, motivo e causa, e a adulteração fica evidente (PANS-AIM 2.2);
- **posições apoiadas em poucos referentes medidos** (referenciamento linear, ISO 19148): a pista vai "da THR16 até a THR34", e o comprimento nunca é escrito;
- **derivados calculados na leitura**: comprimento, rumo e distâncias declaradas saem das premissas, e todos os produtos (tabela do AIP, carta) saem da mesma fonte, consistentes por construção (PANS-AIM 2.1.3.2).

O estudo de caso é a pista do SBSJ (São José dos Campos), com dados reais do AIP e do ADC. Nenhuma das técnicas é nova isoladamente; a contribuição é combiná-las para um problema que continua aberto na informação aeronáutica (o AIXM corrige, mas não garante retenção nem evidência de adulteração, e não guarda as premissas que geraram um número).

**Método.** Design Science Research com avaliação por falseamento: cada experimento tem a previsão escrita e registrada antes de rodar, um gabarito independente do modelo e um veredito (passou ou falhou).

---

## 2. Estrutura

```
tg-sbsj/
├── GUIA.md                     este arquivo
├── README.md
├── requirements.txt            biblioteca + notebook + scripts do protocolo
├── docker-compose.yml          PostGIS + Jupyter
├── Dockerfile.jupyter
├── scripts/
│   ├── pg_local.sh             PostgreSQL local, sem Docker
│   └── rodar_experimentos.sh   roda o notebook do começo ao fim (oficial ou ensaio)
│
├── artefato/                   A BIBLIOTECA (o artefato do TG)
│   ├── README.md               documentação: conceitos, API, exemplos
│   ├── pyproject.toml          pacote "aeroledger"
│   ├── src/aeroledger/         código e esquema SQL
│   └── tests/                  39 testes, aeródromo fictício
│
├── experimento/                OS EXPERIMENTOS (usam a biblioteca)
│   ├── experimentos.ipynb      notebook E1–E5 (gerado)
│   ├── montar_notebook.py      fonte do notebook (texto e código, revisável no git)
│   ├── passos.py               registro dos vereditos e apoio
│   ├── fontes.py               dados do SBSJ, com fonte de cada um
│   ├── fontes_ensaio.py        aeródromo fictício para ensaiar o notebook
│   ├── ataques.py              ataques do E4
│   ├── verificador_independente.py   E5: verifica a cadeia sem importar a biblioteca
│   └── arquivo_v0.4/           o notebook de sete atos da v0.4 (histórico)
│
├── protocolo/                  O QUE SE PREVIU ANTES DE RODAR
│   ├── protocolo.yaml          v0.4, congelada (commit fcfb6a5)
│   ├── PROTOCOLO.sha256
│   ├── v0.5/protocolo.yaml     v0.5, os cinco experimentos (rascunho até congelar)
│   ├── derivar_tolerancias.py  margens de H2 pela precisão de publicação
│   ├── gabarito/               gabarito geodésico independente (Vincenty)
│   └── adc/                    calibração e extração de contornos do ADC (usados na v0.4)
│
└── resultados/
    ├── execucoes.jsonl         registro de todas as execuções (só se acrescenta)
    └── <exec_id>/              vereditos, figuras e exportação de cada execução
```

A separação é intencional: **a biblioteca é o objeto avaliado; o notebook é a avaliação.** O notebook importa `aeroledger` como qualquer usuário faria, e cada passo é uma chamada a ela. A biblioteca não sabe nada do SBSJ.

---

## 3. A biblioteca `aeroledger`

Documentação completa em [`artefato/README.md`](artefato/README.md). Resumo:

```python
import aeroledger as al

conn = al.conectar(); al.criar_esquema(conn)
run = al.novo_run(conn, origem)
ref = al.publicar_referencial(conn, corpo)                       # cabeceiras medidas
al.escrever(conn, run, "SBSJ", "airport", "BASELINE", asserted_by="DECEA",
            corpo={"referencial": {"ref_id": ref}})
al.estado(conn, run, "SBSJ-RWY", t)                              # como estava em t
al.distancias_declaradas(conn, run, t)                           # calculado, nunca guardado
al.verificar_cadeia(conn, run)                                   # [] = íntegra
```

Decisões de arquitetura registradas no código e na documentação:

- **seed na forma B:** `{elemento, referente, s, o}`; diz de onde mede, não quanto mede;
- **referentes múltiplos** com três regras: georreferenciado ou relativo, sem ciclos, ponto sozinho não define direção;
- **`caused_by` no envelope**, dentro do hash;
- **tempo de transação** como única linha do tempo; relógio que só avança; `t` por instante ou por evento;
- **forma canônica JCS (RFC 8785)** para o hash, publicada como especificação para que terceiros verifiquem.

---

## 4. Os experimentos (protocolo v0.5)

| | Pergunta | O que se faz | Gabarito |
|---|---|---|---|
| E1 | Qual é o problema? | as duas edições oficiais em "modo forma", como o AIXM faria | as próprias publicações |
| E2 | O número se refaz a partir das premissas? | comprimento, rumo e distâncias calculados das cabeceiras; a THR34 é remedida e a pista acompanha com um evento | AD 2.12 e AD 2.13; Vincenty em outro código |
| E3 | Como estava em *t*, quem afirmou e por quê? | estado antes e depois da remedição; interdição temporária; envelope; trilha de auditoria | o roteiro, conhecido de antemão |
| E4 | Alguém consegue adulterar sem ser visto? | quatro ataques diretos ao banco, com e sem âncora | a previsão de cada ataque |
| E5 | Dois produtos podem divergir? A prova é verificável por terceiros? | tabela do AIP e ADC do mesmo ledger; verificador independente sobre o JSON exportado | PANS-AIM 2.1.3.2; especificação JCS |

As predições de derivação (H2.01–H2.19) são as da v0.4, reusadas sem alteração. O que saiu do escopo testado, e por quê, está em `protocolo/v0.5/protocolo.yaml` (`motivo_da_mudanca`): o motor de geometria e o ajuste de formas à carta (H1) passaram a demonstração; a barreira (ato 2) e o custo de leitura (H4) ficaram fora desta versão.

**Limites declarados, sem teste:** `asserted_by` registra mas não prova autoria (sem assinatura digital); nenhum sistema torna uma medição verdadeira, só a atribui; interoperabilidade entre organizações diferentes não é testável num TG.

---

## 5. Como rodar

### 5.1 Instalar

Precisa de Python 3.12+ e PostgreSQL 14+ (PostGIS opcional).

```sh
git clone https://github.com/heyfalheiro1537/tg-sbsj && cd tg-sbsj    # clone, não "Download ZIP":
pip install -r requirements.txt                                         # o notebook confere o protocolo pelo git
scripts/pg_local.sh                                                     # Postgres em localhost:54329
```

Ou com Docker: `docker compose up -d` (PostGIS em `localhost:54329`, Jupyter em `localhost:8888`). **O caminho Docker ainda não foi testado com um daemon real.**

### 5.2 Testar a biblioteca

```sh
cd artefato && python3 -m pytest -q          # 39 testes
```

### 5.3 Rodar os experimentos

```sh
scripts/rodar_experimentos.sh --ensaio       # aeródromo fictício: confere que tudo roda; nada é gravado
scripts/rodar_experimentos.sh                # oficial, sobre o SBSJ: exige o protocolo v0.5 congelado
```

Ou abra `experimento/experimentos.ipynb` no Jupyter e rode todas as células (`AEROLEDGER_ENSAIO=1` para ensaio).

No modo ensaio, as verificações de H2 falham de propósito: os números fictícios não são os do SBSJ. O ensaio só confere que o código roda.

Cada execução oficial: confere o hash do protocolo; roda os testes da biblioteca; cria um banco só dela (que não é apagado); acrescenta cada verificação em `resultados/execucoes.jsonl`; grava `resultados/<exec_id>/vereditos.json`, a figura e o JSON exportado.

### 5.4 Conferir sem rodar

```sh
cd protocolo && sha256sum -c PROTOCOLO.sha256    # protocolo v0.4 íntegro
```

`resultados/execucoes.jsonl` traz, para cada verificação de cada execução, o previsto, o observado, a margem e o veredito, além do commit do código que rodou.

### 5.5 Mudar o notebook

O notebook é gerado: edite `experimento/montar_notebook.py` e rode `python3 montar_notebook.py`. Assim o texto e o código ficam revisáveis no git.

---

## 6. Histórico do protocolo e das execuções

| Versão | Estado | O que tem |
|---|---|---|
| v0.4 | congelada em 20/10/2026, commit `fcfb6a5` | H1–H4, 39 verificações, roteiro de sete atos |
| v0.5 | rascunho | E1–E5; reusa H2 da v0.4; motivo da mudança registrado |

**Execução 20261020T234807Z-ebc7ee7 (v0.4, primeira válida).** 40 de 44 verificações passaram: H2 19/19, H3 10/10. H1.02 e H1.05 falharam (a extração da pista pegou só uma das duas peças desenhadas; a carta desenha a SWY ~5 m fora do lugar; o ajuste só usou retângulos). H1.04, R12 e H4 não foram executadas (sem arcos; regra da barreira ausente; o script de escala caiu). Esses resultados continuam no registro e no texto. A execução anterior (`…-b1eccba`) não conta: rodou com código não commitado.

**Achado do verificador independente (21/10/2026).** Ao comparar a forma canônica da biblioteca com a reimplementada a partir do RFC 8785, apareceu um erro na biblioteca: números inteiros acima de 2⁵³ guardados como `float` saíam com os dígitos binários exatos, não com os dígitos mais curtos que o RFC exige. Nenhum valor do TG chega perto disso, então nenhum resultado foi afetado. A biblioteca foi corrigida e ganhou um teste.

---

## 7. Achados nas publicações oficiais (material para o capítulo 3)

1. **As duas edições oficiais divergem sem causa registrada.** Da AOC 2213 para o ADC 2604: pista 2676 → 2675 m, SWY 325 → 283 m, faixa 3121 × 300 → 3118 × 280 m, ASDA 3001 → 2958 m. É o E1.
2. **A observação da RWY 34 no AD 2.12 fala em "THR 34 deslocada"**, mas LDA 34 = TORA 34 = 2675 m: não há deslocamento em vigor.
3. **A posição longitudinal da faixa não é publicada:** 160 m além de pista + SWY, sem divisão entre as pontas (na AOC eram 60 + 60 m).
4. **O AD 2.12 não traz as coordenadas do fim de pista**, que o PANS-AIM exige.
5. **Um tique da gratícula do ADC está desenhado 7,4 m fora do lugar** (45°51'06", borda de baixo).
6. **O ADC usa o norte da quadrícula UTM**, girado 0,33° em relação ao norte verdadeiro.
7. **A SWY está desenhada no ADC ~5 m fora** da posição que o AD 2.12 implica.
8. **As casas decimais do AD 2.12 seguem o PANS-AIM:** cabeceira de precisão (RWY 16) com elevação ao decímetro; não precisão (RWY 34) ao metro.
9. **O PANS-AIM deixa a distribuição em aberto:** a seção 2.1.4 (*Distribution*) diz "*To be developed*". É onde a integridade costuma se perder, e é o que o E5 ataca.

---

## 8. O que falta

1. **Revisar e congelar o protocolo v0.5** (`protocolo/v0.5/protocolo.yaml`): estado `congelado`, hash em `protocolo/v0.5/PROTOCOLO.sha256`, commit enviado ao GitHub antes de rodar.
2. **Rodar a execução oficial** (`scripts/rodar_experimentos.sh`) e enviar o registro.
3. **Criar as tags** `protocolo-v0.4` (commit `fcfb6a5`) e, depois, `protocolo-v0.5`, pelo GitHub (Releases).
4. **Decidir onde ficam as fontes oficiais** (PDFs do ADC e da AOC, print do AD 2.12): no repositório, num depósito com DOI (Zenodo) ou só com hashes e a indicação de onde obter.
5. **Testar o Docker** numa máquina com daemon.

**Em aberto, sem bloquear:** âncora externa (na arquitetura ou como limite); assinatura digital por evento; custo de leitura (H4) numa v0.6; comparação com BIM na introdução ou em trabalhos relacionados.

---

## 9. Ressalva

Dados do AIP Brasil (DECEA) usados para pesquisa. Nada aqui substitui a publicação oficial.
