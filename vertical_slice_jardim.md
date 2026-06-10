# Vertical Slice — Mundo Jardim
## Calango Filhote · Fases 1–5 · Documento de Design e Implementação

---

## 1. Análise do Núcleo de Movimentação

### O que o código tem (e está funcionando bem)

Depois de ler `player.py`, `main.py`, `config.py` e `tilemap_loader.py`, o núcleo está **sólido para um Vertical Slice**. Aqui está o que cada sistema oferece ao design de fases:

| Sistema | Constante/Arquivo | O que significa pro Level Design |
|---|---|---|
| Velocidade horizontal | `SPEED = 160 px/s` | O calango é **lento e deliberado** — bom para fases pequenas, combina com nenenzinho |
| Gravidade | `GRAVITY = 1200 px/s²` | Queda **rápida e pesada** — pulos são decisivos, não flutuados |
| Força de pulo | `JUMP_FORCE = -550 px/s` | Pulo de **~2.4 tiles de altura** (calculado: h = v²/2g ≈ 126px ≈ 3.15 tiles de 40px) |
| Coyote Time | `0.15s` | Generoso — jogador raramente perde pulos por bordas |
| Jump Buffer | `0.10s` | Permite antecipar pousos — reduz frustração em plataformas pequenas |
| Terminal Velocity | `900 px/s` | Quedas longas terminam em squash dramático, não em tunnel |
| Escalada | `VEL_ESCALA_SOBE = -100 px/s` | **Escalada lenta** — paredes altas custam tempo e atenção |
| Wall Jump | `FORCA_WALL_JUMP = 220 px/s (60% do pulo normal)` | Escape de emergência, não combo fácil |
| Squash & Stretch | Vários `SS_*` | Feedback visual rico — o calango comunica emoção sem texto |
| Partículas | `emitir_landing_dust`, `emitir_jump_dust` | Reforço visual de cada ação física |

### Diagnóstico de feel para o Vertical Slice

**Pontos fortes do núcleo atual:**
- A física de pulo com coyote + buffer já elimina a maior fonte de frustração em plataformers
- O Squash & Stretch com squash proporcional à velocidade de queda cria feedback tátil real
- A escalada com escorregamento passivo (40px/s) cria tensão natural — parede ≠ descanso

**Pontos para observar durante o playtest:**
- `SPEED = 160px/s` é bem conservador. Com tile de 40px, o calango percorre 4 tiles por segundo. Em fases de ~75 tiles de largura, isso é ~18 segundos só de travessia linear — considere gaps e obstáculos que quebrem o ritmo horizontal
- A escalada sobe a 100px/s = 2.5 tiles/s. Paredes com mais de 5 tiles de altura (~200px) já exigem comprometimento real

---

## 2. Arquitetura do Mapa (como o engine lê)

O `tilemap_loader.py` suporta **dois formatos**:

### Formato A: `.txt` (atual, em uso)
```
Legenda:
  #   = plataforma sólida (Plataforma sprite)
  P   = player_spawn
  M   = moeda/larva
  E   = inimigo patrulheiro
  .   = espaço vazio
```
Cada caractere = **1 tile de 40×40px**. Uma linha de 80 caracteres = mapa de 3200px de largura.

### Formato B: `.tmx` (Tiled, suportado pelo loader)
O loader já suporta camadas `colisao`, `decoracao` e `objetos` (com `player_spawn`, `moeda`, `inimigo`). A seção 6 deste documento detalha como usar o Tiled.

### Dimensões de referência
- Tela: **800×600px** = 20×15 tiles
- Tile: **40×40px**
- Pulo máximo: ~3 tiles de altura, ~4–5 tiles de alcance horizontal (com velocidade)
- Largura recomendada por fase: **80–120 tiles** (3200–4800px)

---

## 3. Progressão de Dificuldade — Visão Geral

```
FASE 1 ── FASE 2 ── FASE 3 ── FASE 4 ── FASE 5
 Tutorial   Ritmo   Escalada   Precisão   Síntese
   ★☆☆☆☆    ★★☆☆☆    ★★★☆☆     ★★★★☆     ★★★★★
```

Cada fase introduz **um conceito novo de espaço** usando apenas as mecânicas existentes:

| Fase | Conceito Central | Perigo Principal | Exige |
|---|---|---|---|
| 1 | Familiarização | Buracos rasos | Andar + pular |
| 2 | Ritmo de pulo | Buracos médios + plataformas suspensas | Timing de pulo |
| 3 | Escalada vertical | Paredes altas + queda longa | Escalar + pulo de parede |
| 4 | Precisão horizontal | Plataformas pequenas + gaps apertados | Coyote + buffer |
| 5 | Combinação | Tudo junto + percurso longo | Fluência completa |

---

## 4. Fase a Fase — Design Detalhado

---

### FASE 1 — "O Jardim de Entrada"
**Conceito:** Tutorial implícito. O calango acorda no jardim, tudo é baixo e seguro.

**Métricas:**
- Largura: **80 tiles** (3200px)
- Altura: **15 tiles** (600px)
- Colecionáveis (larvas/moedas): **5**
- Checkpoints: **0** (fase curta, não precisa)
- Tempo estimado de conclusão: 45–90 segundos

**Progressão interna:**
1. **Zona A (tiles 0–20):** Chão plano com 1 buraco de 2 tiles. Moeda no ar, acessível com pulo simples. Ensina que buracos existem.
2. **Zona B (tiles 20–45):** Duas plataformas elevadas (+3 tiles de altura) com moedas em cima. Ensinam o pulo como ferramenta, não obstáculo.
3. **Zona C (tiles 45–65):** Sequência de 3 plataformas crescentes (escada de degrau único). Moedas em cada degrau.
4. **Zona D (tiles 65–80):** Descida suave até a saída (tile de saída = área sem chão à direita que avança a fase).

**Perigos:**
- Buracos de **2 tiles** (80px) — impossível cair sem perceber
- **Sem inimigos** nesta fase

**Layout conceitual (txt, 80 cols × 15 rows):**
```
................................................................................
................................................................................
....P...........................................................................
..###...........................................................................
.................M......M.......................................................
..............###.....###......#####............................................
...............................................................................
.......................................M........M.......M........................
....................................####.....####.....#####......................
................................................................................
.......#.......................................................................
......###......................................................................
.....#####.....................................................................
################################################################################
################################################################################
```

**Intenção de aprendizado:** O jogador descobre que pode subir em plataformas, que moedas estão no ar e que buracos terminam em morte. Tudo com zero pressão.

---

### FASE 2 — "Entre as Folhas"
**Conceito:** Ritmo de pulo. Plataformas suspensas exigem sequências de 2–3 pulos encadeados.

**Métricas:**
- Largura: **90 tiles** (3600px)
- Altura: **15 tiles** (600px)
- Colecionáveis: **7**
- Checkpoints: **1** (no meio da fase, tile 45)
- Tempo estimado: 60–120 segundos

**Progressão interna:**
1. **Zona A (0–25):** Introdução a plataformas suspensas (+4 tiles). Gap de 3 tiles entre plataformas. Duas moedas acessíveis com 2 pulos diretos.
2. **Zona B (25–45):** Plataformas em zigue-zague horizontal — alternam altura +3 e +5 tiles. Exige coyote time para os mais impacientes que pisam na borda.
3. **CHECKPOINT (tile 45):** Chão sólido com moeda de bônus acima.
4. **Zona C (45–70):** Buraco de **5 tiles** (o maior até agora). Há uma "ilha" no meio com moeda — o jogador escolhe pousar nela ou pular direto.
5. **Zona D (70–90):** Sequência de descida em plataformas decrescentes. Moedas nas mais baixas.

**Perigos:**
- Buracos de **3–5 tiles**
- 1 inimigo patrulheiro simples na Zona C (no chão, antes do buraco grande) — serve de aviso visual para abrir espaço

**Perigo ambiental:** Plataformas com **borda visual marcada** (tile diferente) indicando que há queda. Implementar como tile decorativo diferente no Tiled.

**Layout conceitual:**
```
................................................................................
.......M......................M..........M.......................................
......####...............#####...........####...................................
...............................M...............M.................................
...........................####...............####..............................
..P..............................................M.......M.......................
.####..................................................................#########
........###.............C.............###.......####............................
.............####.....####.....####.....................................M.......
..............................................####....####....###....##..........
#########.......................................................................
.................................................................###############
################################################################################
```
*(C = objeto checkpoint; tiles de chão omitidos por legibilidade)*

---

### FASE 3 — "A Trepadeira"
**Conceito:** Escalada vertical. O jardim tem **muros altos** que só podem ser atravessados escalando.

**Métricas:**
- Largura: **100 tiles** (4000px)
- Altura: **20 tiles** (800px — fase mais **alta** que larga em certas seções)
- Colecionáveis: **8**
- Checkpoints: **1**
- Tempo estimado: 90–150 segundos

**Progressão interna:**
1. **Zona A (0–20):** Chão plano com apresentação do muro. Uma parede de **6 tiles de altura** bloqueia o caminho. Única solução: escalar. Moeda no topo do muro.
2. **Zona B (20–50):** Corredor em "S" formado por paredes. Escalar a primeira parede, pular para a segunda, escalar de novo (mas do outro lado). Moedas em cada transição.
3. **CHECKPOINT (tile 50)**
4. **Zona C (50–75):** Área aberta com **2 paredes gêmeas** (espaçadas 3 tiles). O calango deve usar wall jump para sair do "corredor de paredes" — não há outra saída vertical. Moeda no topo.
5. **Zona D (75–100):** Descida com plataformas. A última plataforma está a **5 tiles abaixo** — queda de impacto com squash dramático recompensa o jogador visualmente.

**Perigos:**
- **Espinhos** (tiles visuais sem colisão diferente, ou tiles com tag `dano`): no fundo de certos poços entre paredes. Cair no poço = morte sem inimigo.
  > *Implementação no motor atual: adicionar tipo `"espinho"` no `tilemap_loader.py` e checar colisão em `main.py` da mesma forma que inimigos — `tomar_dano()`. Nenhuma nova mecânica, só novo tipo de objeto.*
- 2 inimigos patrulheiros no chão (Zonas B e D)

**Introdução ao Wall Jump:** A Zona C **força** o wall jump naturalmente, sem tutorial explícito. O espaço entre as paredes não permite pulo normal de saída — o jogador descobre pela experimentação.

**Layout conceitual (seção da Zona C):**
```
.......................................................
.......................................................
..........................M............................
.................####...####...........................
.................#..#...#..#...........................
.................#..#...#..#...........................
.................#..#...#..#...........................
.................####...####...........................
.......................................................
```

---

### FASE 4 — "Caminho das Pedras"
**Conceito:** Precisão e timing. Plataformas pequenas (1–2 tiles), gaps que exigem pulo no limite do alcance.

**Métricas:**
- Largura: **95 tiles** (3800px)
- Altura: **15 tiles** (600px)
- Colecionáveis: **9**
- Checkpoints: **2** (a cada ~30 tiles)
- Tempo estimado: 2–4 minutos

**Progressão interna:**
1. **Zona A (0–30):** Plataformas de **2 tiles** separadas por gaps de 3 tiles. Altura variada (+2, +4, +2). Moedas na maioria das plataformas — recompensa cada acerto.
2. **CHECKPOINT 1 (tile 30)**
3. **Zona B (30–60):** Combinação de plataformas pequenas **e** parede escalável. O jogador deve escalar para chegar a uma plataforma que só é acessível pelo topo da parede. Moedas no caminho "difícil".
4. **CHECKPOINT 2 (tile 60)**
5. **Zona C (60–95):** Sequência final de 5 plataformas de **1 tile** — o teste máximo de precisão da fase. Moedas apenas em plataformas alternadas (não premia só a chegada, premia a leitura do percurso).

**Perigos:**
- Buracos de até **6 tiles** — quase no limite do pulo horizontal
- 3 inimigos patrulheiros, posicionados **em plataformas** (não no chão) — forçam o jogador a planejar a rota com o inimigo na trajetória
- Espinhos no fundo de buracos selecionados

**Mecânica de pressão:** O coyote time e o jump buffer são *essenciais* nesta fase — quem não os descobriu organicamente até aqui, descobre aqui. Não há texto: o design força o aprendizado.

---

### FASE 5 — "O Jardim Secreto"
**Conceito:** Síntese de tudo. Fase mais longa e variada, mistura todos os elementos anteriores num fluxo contínuo sem repetição mecânica.

**Métricas:**
- Largura: **120 tiles** (4800px)
- Altura: **20 tiles** (800px)
- Colecionáveis: **12**
- Checkpoints: **3** (tiles 30, 60, 90)
- Tempo estimado: 3–6 minutos

**Progressão interna:**
1. **Abertura (0–30):** Recapitulação rápida — chão com buraco, plataforma elevada, moeda. O jogador aquecido passa voando. 3 moedas.
2. **CHECKPOINT 1**
3. **Seção Escalada (30–60):** Área vertical com 3 paredes de altura crescente (4, 5, 6 tiles). Wall jump obrigatório na última. 4 moedas escondidas em nichos laterais acessíveis pela escalada.
4. **CHECKPOINT 2**
5. **Seção Precisão (60–90):** O corredor de plataformas pequenas mais desafiador do jogo. Gap de 5 tiles com plataforma de 1 tile no meio. Após este gap, uma área de descanso recompensa o jogador antes do final. 3 moedas.
6. **CHECKPOINT 3**
7. **Clímax (90–120):** Sequência mista — plataformas suspensas + paredes + espinhos no fundo. A última seção tem uma "vista panorâmica" (chão desce, o calango fica alto no cenário) antes da chegada. 2 moedas de bônus no caminho alternativo mais difícil.

**Perigos:**
- Todos os tipos anteriores
- Espinhos em posições que criam "escolhas de rota" — caminho seguro (mais longo) vs. caminho com espinhos (mais curto, recompensa quem acerta)
- 4 inimigos patrulheiros, incluindo 1 em plataforma estreita

---

## 5. Lista Completa de Obstáculos e Colecionáveis

### Obstáculos por tipo

| Tipo | Fases | Implementação | Descrição |
|---|---|---|---|
| **Buraco raso** (1–2 tiles) | 1 | `.` no txt | Queda fatal, recuperável com coyote |
| **Buraco médio** (3–4 tiles) | 2, 3 | `.` no txt | Exige pulo intencional |
| **Buraco largo** (5–6 tiles) | 4, 5 | `.` no txt | No limite do alcance horizontal |
| **Parede escalável** (4–6 tiles) | 3, 4, 5 | `#` vertical | Bloco sólido vertical — já funciona com escalada atual |
| **Corredor de paredes** | 3, 5 | `#..#` no txt | Força wall jump — paredes gêmeas espaçadas 3 tiles |
| **Espinhos** | 3, 4, 5 | Novo objeto TMX | `tomar_dano()` ao colidir — sem nova mecânica, novo tipo de tile |
| **Inimigo patrulheiro** | 2–5 | `E` no txt ou objeto TMX | Já implementado em `sprites.py` |
| **Inimigo em plataforma** | 4, 5 | Posicionamento TMX | Mesmo inimigo, posição diferente muda o desafio |

### Colecionáveis

| Fase | Quantidade | Distribuição | Dificuldade de acesso |
|---|---|---|---|
| 1 | 5 | Todos em rotas principais | Nenhuma — existem para ensinar o verbo "coletar" |
| 2 | 7 | 5 na rota principal, 2 em desvio | 2 exigem pequeno desvio de rota |
| 3 | 8 | 4 na rota principal, 4 em nichos de escalada | 4 exigem perceber nichos laterais |
| 4 | 9 | 4 obrigatórios, 5 em plataformas opcionais difíceis | 5 são o "desafio do speedrunner" |
| 5 | 12 | 8 na rota principal, 4 em caminho alternativo | 4 exigem rota de espinhos ou escalada extra |
| **Total** | **41** | | |

---

## 6. Como Construir as Fases no Tiled

### Setup inicial do Tiled

1. **Crie um novo mapa:** `Arquivo → Novo → Novo Mapa`
   - Orientação: Ortogonal
   - Formato de layer: CSV
   - Tamanho do tile: **16×16px** (o loader converte para 40px automaticamente)
   - Tamanho do mapa: ex. 80×15 tiles para a Fase 1

2. **Importe o tileset:** `Tileset → Novo Tileset → tileset.png` (do projeto)

### Camadas obrigatórias

Crie exatamente com estes nomes (o loader usa `layer.name`):

```
colisao     ← Layer de Tiles: tiles sólidos. GID ≠ 0 = bloco físico.
decoracao   ← Layer de Tiles: visuais sem colisão (flores, galhos). Ignorado pelo loader.
objetos     ← Object Layer: spawn, moedas, inimigos, checkpoints.
```

### Object Layer — tipos reconhecidos

No Tiled, crie objetos do tipo **Point** ou **Rectangle** com o campo **Nome** configurado:

| Nome do objeto | Efeito no jogo | Propriedades extras |
|---|---|---|
| `player_spawn` | Posição inicial do calango | — |
| `moeda` | Larva/moeda coletável | — |
| `inimigo` | Inimigo patrulheiro | `x_min`, `x_max` (px), `velocidade` (px/s) |
| `checkpoint` | (futura implementação — já no loader) | — |
| `espinho` | (adicionar ao loader — ver seção abaixo) | — |

### Configurando inimigos no Tiled

1. Crie um objeto Point na posição desejada
2. Nome: `inimigo`
3. Adicione propriedades customizadas:
   - `x_min` (int) = limite esquerdo da patrulha em pixels (ex: `400`)
   - `x_max` (int) = limite direito em pixels (ex: `800`)
   - `velocidade` (float) = velocidade em px/s (ex: `80.0`)

### Exportando para o jogo

1. `Arquivo → Salvar Como` → salve como `fase1.tmx` (ou `fase2.tmx`, etc.)
2. Coloque o `.tmx` na raiz do projeto (junto com `fase1.txt`)
3. No `config.py`, adicione o caminho:
   ```python
   FASE_1_TMX: str = str(BASE_DIR / "fase1.tmx")
   ```
4. Em `main.py`, atualize `_arquivo_fase_atual()` para apontar para o `.tmx`

### Para os espinhos (pequena adição ao loader)

No `tilemap_loader.py`, no bloco de leitura de objetos, adicione:
```python
elif obj.name == "espinho":
    dados["espinhos"].append((int(obj.x * escala), int(obj.y * escala)))
```
Em `main.py`, cheque colisão com espinhos exatamente como checa com inimigos — chamando `player.tomar_dano()`. Nenhuma nova mecânica.

### Fluxo de iteração recomendado

```
1. Esboce o layout no papel (ou use o txt)
2. Construa no Tiled com a camada de colisão
3. Adicione objetos (spawn, moedas, inimigos)
4. Exporte e teste no jogo
5. Ajuste gaps e alturas com base no feel real
6. Adicione decoração (camada ignorada pelo loader, mas visível se implementar blit futuro)
```

---

## 7. Como Testar e Validar a Diversão do Movimento

### O teste dos 10 minutos

Coloque alguém que **nunca viu o projeto** para jogar as 5 fases sem explicação. Observe:

- [ ] Consegue completar a Fase 1 sem ajuda?
- [ ] Descobre a escalada sozinho na Fase 3 (sem ler manual)?
- [ ] Usa coyote time por instinto até a Fase 4?
- [ ] Tenta coletar moedas difíceis ou ignora?
- [ ] Morre frustrado ou morre e tenta de novo?

### Métricas quantitativas para o playtest

Para cada fase, registre:

| Métrica | Como medir | Meta |
|---|---|---|
| Mortes por fase | Contador simples no console | F1: <3, F2-3: <5, F4-5: <8 |
| Tempo de conclusão | `time.time()` no `_avancar_fase()` | Dentro das estimativas ±50% |
| Moedas coletadas | `score` final | >60% das moedas = design funcionando |
| Uso de escalada | Flag `player.escalando` por frame | Deve aparecer na F3 sem instrução |
| Onde morre mais | Posição `player.rect.x` na morte | Mostra onde o design está duro |

### Perguntas qualitativas após o playtest

1. **"Teve algum momento que você sentiu que morreu injustamente?"** → Se sim, ajuste coyote time ou reposicione o obstáculo
2. **"Teve algum momento que você se sentiu especialmente esperto?"** → Esse momento é o coração do design. Preserve-o e crie mais
3. **"O que a escalada parecia?"** → Se responder "incômoda", aumentar `VEL_ESCALA_SOBE` (ex: -130). Se "fácil demais", reduzir
4. **"Você queria coletar tudo ou só terminar?"** → Informa se o sistema de moedas está motivando

### Ajustes finos de física para validar

Se o movimento parecer "escorregadio" ou "pesado", os parâmetros a testar primeiro:

```python
# Em config.py — ordem de impacto no feel:
PLAYER_SPEED        = 160.0  # ↑ mais ágil, ↓ mais deliberado
PLAYER_GRAVITY      = 1200.0 # ↑ pulos mais secos, ↓ mais flutuados
PLAYER_JUMP_FORCE   = -550.0 # ↑ pulo mais alto (atenção: rebalancear gaps!)

# Em player.py — escalada:
VEL_ESCALA_SOBE  = -100.0  # ↑ (em abs) sobe mais rápido
VEL_ESCORREGA    = 40.0    # ↑ escorrega mais rápido = mais tensão
```

> **Regra de ouro:** Mude **uma constante por vez** e jogue a Fase 3 completa antes de mudar outra. A escalada é o sistema mais sensível a ajustes combinados.

### Checklist do Vertical Slice antes de considerar concluído

- [ ] 5 arquivos de fase criados e carregando sem erro
- [ ] Progressão de fase 1→2→3→4→5 funcionando via `_avancar_fase()`
- [ ] `TOTAL_FASES = 5` atualizado em `main.py`
- [ ] Cada fase testada em isolamento (pode iniciar direto pela fase, editando `fase_atual` no construtor)
- [ ] Pelo menos 1 playtest com pessoa externa
- [ ] Sem morte por bug (cair através de plataforma, inimigo fora dos limites, etc.)
- [ ] Moedas coletáveis em todas as fases
- [ ] Squash & stretch visível em quedas das Fases 3 e 5 (as mais altas)

---

## 8. Próximos Passos (pós-Vertical Slice)

Após validar que o movimento é divertido com estas 5 fases, os próximos blocos naturais são:

1. **Checkpoints salvando posição** — o sistema de objeto `checkpoint` já está no `tilemap_loader.py`, só precisa de lógica em `main.py` para salvar `_spawn_x/_spawn_y`
2. **Plataformas móveis** — a classe `Plataforma` em `sprites.py` já tem comentário `"Subclasses (PlataformaMovel, Armadilha) podem sobrescrever update(dt)"` — a arquitetura suporta
3. **Espinhos** — adição mínima ao loader (descrita acima), sem nova mecânica
4. **Arte no Tiled** — a camada `decoracao` já é lida e ignorada; implementar o blit dessa camada permite adicionar vegetação, fundos e variação visual sem tocar na física

---

*Documento gerado com base na análise de `player.py`, `main.py`, `config.py`, `sprites.py`, `tilemap_loader.py` e `fase1.txt` do projeto "Meu primeiro jogo" (commit de 04/06/2026).*
