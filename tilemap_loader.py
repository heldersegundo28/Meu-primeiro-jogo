"""
tilemap_loader.py
═════════════════
Loader híbrido e desacoplado de mapas para o Jogo do Calango.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RESPONSABILIDADE ÚNICA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Este módulo faz UMA coisa: ler um arquivo de mapa e retornar dados
estruturados puros (MapData). Ele NUNCA:
  • instancia sprites Pygame (Plataforma, Moeda, Inimigo...)
  • importa main.py, camera.py, player.py ou sprites.py
  • chama pygame.init() ou cria surfaces

Esse contrato garante zero dependência circular. O diagrama é:

    main.py
      │  importa
      ▼
    tilemap_loader.py
      │  importa apenas
      ├── pathlib   (stdlib)
      ├── config    (constantes — sem instâncias Pygame)
      └── pytmx     (opcional, importado localmente)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
O QUE É MapData
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MapData é um TypedDict — um dicionário com chaves fixas e tipos
conhecidos em tempo de análise estática. Representa o estado completo
de um mapa carregado, independente de qual formato originou os dados.

Esquema:

    MapData = {
        "largura_px":  int               dimensão real do mapa em pixels
        "altura_px":   int               dimensão real do mapa em pixels
        "tile_size":   int               tamanho lógico do tile de colisão
        "colisao":     list[TileRect]    retângulos de blocos sólidos
        "spawn":       tuple|None        posição inicial do calango
        "moedas":      list[tuple]       centros das moedas/larvas
        "inimigos":    list[InimigoDado]      dados para instanciar inimigos
        "checkpoints": list[CheckpointDado]  pontos de respawn da fase
        "saida":        SaidaDado | None       saída de fase (None = sem saída)
        "insetos":         list[InsetoDado]           insetos do cenário
        "plataformas_moveis": list[PlataformaMovelDado]  plataformas móveis
        "armadilhas":      list[ArmadilhaDado]        armadilhas ambientais
        "objetos":         list[ObjDado]              objetos genéricos (extensível)
    }

    TileRect   = (x, y, w, h)          ints, coordenadas de mundo
    InimigoDado = {
        "x", "y",                       topleft do sprite
        "x_min", "x_max",               limites de patrulha
        "velocidade",                   px/s
    }
    ObjDado = {
        "tipo",                         str: "player_spawn", "checkpoint"...
        "x", "y",                       coordenadas de mundo
        "props",                        dict extra (para futuras props Tiled)
    }

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONVERSÃO DE ESCALA VISUAL → LÓGICA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

O Tiled pode usar tiles de 16×16 ou 32×32 px para resolução visual.
O motor do jogo usa config.TILE_SIZE (40 px) como unidade lógica de
colisão e posicionamento.

Conversão:
    escala = config.TILE_SIZE / tmx_tile_size     (ex: 40/16 = 2.5)
    x_mundo = col * tmx_tile_size * escala = col * config.TILE_SIZE
    w_mundo = largura_tile_visual  * escala

Diagrama:

    Tiled (16px/tile)         Motor (40px/tile)
    ┌──┬──┬──┬──┐             ┌────┬────┬────┬────┐
    │  │  │  │  │  ──escala── │    │    │    │    │
    └──┴──┴──┴──┘  ×2.5       └────┴────┴────┴────┘
    64px total                160px total

A posição col×row é sempre convertida via:
    mundo_x = col * config.TILE_SIZE
    mundo_y = row * config.TILE_SIZE

independente do tilewidth do .tmx — o índice de grid é a unidade
invariante entre os dois sistemas.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CAMADAS ESPERADAS NO TILED (.tmx)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    Layer de Tiles — nome: "colisao"
      Tiles sólidos de colisão. GID qualquer ≠ 0 = bloco sólido.
      Um tile nesta camada vira um TileRect em MapData["colisao"].

    Layer de Tiles — nome: "decoracao" (opcional, ignorado)
      Tiles visuais sem colisão. Não lidos por este loader.
      No futuro: retornar lista separada para blit decorativo.

    Object Layer — nome: "objetos"
      Objetos com posição e tipo. Lidos e retornados em MapData["objetos"]
      e desempacotados em "spawn", "moedas" e "inimigos" por conveniência.

      Tipos de objetos reconhecidos (campo "name" no Tiled):
        "player_spawn"  → define MapData["spawn"]
        "moeda"         → adiciona a MapData["moedas"]
        "inimigo"       → adiciona a MapData["inimigos"]
        qualquer outro  → vai para MapData["objetos"] genérico

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COMPATIBILIDADE COM CHUNKS / STREAMING FUTURO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

As funções são projetadas para aceitar parâmetros de região:
    _tiles_colisao_txt(grid, T, regiao=None)
    _tiles_colisao_tmx(tmx_data, T, regiao=None)

O parâmetro "regiao" (None por ora) permitirá no futuro:
    regiao = (col_inicio, col_fim, lin_inicio, lin_fim)
Carregando apenas o retângulo visível + margem de segurança.
Implementação futura sem quebrar a API atual.
"""

from __future__ import annotations

import pathlib
from typing import TypedDict

import config


# ══════════════════════════════════════════════════════════════════════
# TIPOS ESTRUTURAIS
# ══════════════════════════════════════════════════════════════════════

# TileRect: retângulo de colisão no mundo (x, y, largura, altura) — ints
TileRect = tuple[int, int, int, int]

class InimigoDado(TypedDict, total=False):
    """
    Dados para instanciar um inimigo via EnemyFactory.

    total=False: campos "tipo" e "dano" são opcionais —
    ausentes em fases antigas; factory usa defaults.
    """
    x:          int
    y:          int
    x_min:      int
    x_max:      int
    velocidade: float
    tipo:       str   # opcional; default "patrulheiro" na factory
    dano:       int   # opcional; default 1 na factory

class CheckpointDado(TypedDict):
    """Dados necessários para instanciar um Checkpoint."""
    x: int
    y: int


class SaidaDado(TypedDict):
    """Dados necessários para instanciar a saída de fase."""
    x: int
    y: int


class InsetoDado(TypedDict, total=False):
    """
    Dados para instanciar um inseto via InsectFactory.

    Campos obrigatórios
    ───────────────────
    x, y : topleft em world-space

    Campos opcionais (total=False — ausentes = factory usa defaults)
    ─────────────────────────────────────────────────────────────────
    tipo       : chave no registry (default 'wandering')
    velocidade : px/s (default 28.0)
    area       : raio de confinamento em px (default 120)
    """
    x:          int
    y:          int
    tipo:       str
    velocidade: float
    area:       int


class PlataformaMovelDado(TypedDict, total=False):
    """
    Dados para instanciar uma PlataformaMovel.

    Campos obrigatórios
    ───────────────────
    x, y            : topleft inicial em pixels do motor
    largura, altura : dimensões da plataforma (pixels)
    tipo_movimento  : 'horizontal' ou 'vertical'
    velocidade      : px/s

    Campos opcionais (total=False; ausentes → defaults na classe)
    ──────────────────────────────────────────────────────────────
    x_min, x_max : limites horizontais em pixels do motor (default 0)
    y_min, y_max : limites verticais   em pixels do motor (default 0)
    """
    x:              int
    y:              int
    largura:        int
    altura:         int
    tipo_movimento: str
    velocidade:     float
    x_min:          int
    x_max:          int
    y_min:          int
    y_max:          int


class ArmadilhaDado(TypedDict):
    """
    Dados para instanciar uma armadilha via create_trap().

    tipo  : chave no registry de traps.py
    x, y  : posição topleft em pixels do motor
    props : dict de propriedades customizadas do Tiled
            (alcance, tempo_recarga, velocidade, direcao, etc.)
    """
    tipo:  str
    x:     int
    y:     int
    props: dict


class ObjDado(TypedDict):
    """Dado genérico de Object Layer — extensível para checkpoints, itens, etc."""
    tipo:  str
    x:     int
    y:     int
    props: dict   # propriedades customizadas do Tiled (livres)

class MapData(TypedDict):
    """
    Estrutura de dados retornada por carregar_mapa().
    Representa o estado completo de um nível, independente do formato.
    """
    largura_px:  int
    altura_px:   int
    tile_size:   int
    colisao:     list[TileRect]
    spawn:       tuple[float, float] | None
    moedas:      list[tuple[float, float]]
    inimigos:    list[InimigoDado]
    checkpoints: list[CheckpointDado]
    saida:       "SaidaDado | None"
    insetos:            list[InsetoDado]
    plataformas_moveis: list[PlataformaMovelDado]
    armadilhas:         list[ArmadilhaDado]
    objetos:            list[ObjDado]


# ══════════════════════════════════════════════════════════════════════
# API PÚBLICA
# ══════════════════════════════════════════════════════════════════════

def carregar_mapa(caminho: str) -> MapData | None:
    """
    Ponto de entrada único do loader — detecta formato e despacha.

    Formatos suportados
    ────────────────────
      .txt  →  _carregar_txt()   grid de caracteres (formato legado)
      .tmx  →  _carregar_tmx()   mapa Tiled via pytmx

    Retorno
    ────────
    MapData preenchido com dados do mapa, ou None se o arquivo não
    existe ou tem formato desconhecido. O caller (main.py) é responsável
    por usar o None como sinal de fallback.

    Por que retornar None em vez de levantar exceção?
    ──────────────────────────────────────────────────
    O jogo deve continuar rodando mesmo com arquivo ausente durante
    desenvolvimento — grupos vazios são preferíveis a um crash.
    Mensagens de aviso no terminal informam o desenvolvedor sem
    interromper o loop de jogo.

    Parâmetros
    ──────────
    caminho : str
        Caminho absoluto ou relativo para o arquivo de mapa.
        Aceita Path objects via str() implícito — pathlib.Path.suffix
        funciona tanto com str puro quanto com objetos Path.
    """
    sufixo = pathlib.Path(caminho).suffix.lower()

    if sufixo == ".txt":
        return _carregar_txt(caminho)
    elif sufixo == ".tmx":
        return _carregar_tmx(caminho)
    else:
        print(
            f"[LOADER] Formato não suportado: '{sufixo}' em '{caminho}'.\n"
            f"         Use .txt ou .tmx."
        )
        return None


def mapa_vazio() -> MapData:
    """
    Retorna um MapData mínimo e válido (sem tiles, sem objetos).

    Útil como fallback quando carregar_mapa() retorna None e o caller
    quer um dict válido em vez de checar None em todo lugar.

    Uso típico em main.py:
        dados = carregar_mapa(arquivo) or mapa_vazio()
    """
    return MapData(
        largura_px = config.WORLD_WIDTH,
        altura_px  = config.SCREEN_HEIGHT,
        tile_size  = config.TILE_SIZE,
        colisao      = [],
        spawn        = None,
        moedas       = [],
        inimigos     = [],
        checkpoints  = [],
        saida        = None,
        insetos             = [],
        plataformas_moveis  = [],
        armadilhas          = [],
        objetos             = [],
    )


# ══════════════════════════════════════════════════════════════════════
# LOADER TXT — grid de caracteres
# ══════════════════════════════════════════════════════════════════════

def _carregar_txt(caminho: str) -> MapData | None:
    """
    Carrega um mapa no formato de grid de caracteres (.txt).

    Formato
    ────────
    Arquivo de texto onde cada linha é uma linha do grid e cada
    caractere é um tile de config.TILE_SIZE × config.TILE_SIZE px.

    Legenda
    ────────
      '.'  espaço vazio (céu)
      '#'  tile de colisão sólido
      'M'  moeda / larva (centralizada no tile)
      'E'  inimigo patrulheiro
      'P'  spawn do calango filhote

    Retorno
    ────────
    MapData preenchido, ou None se FileNotFoundError.

    Parâmetros
    ──────────
    caminho : str   caminho para o arquivo .txt
    """
    try:
        with open(caminho, encoding="utf-8") as f:
            grid = [linha.rstrip("\n") for linha in f]
    except FileNotFoundError:
        print(f"[LOADER] Arquivo .txt não encontrado: '{caminho}'")
        return None

    if not grid:
        print(f"[LOADER] Arquivo .txt vazio: '{caminho}'")
        return None

    T           = config.TILE_SIZE
    num_colunas = max(len(l) for l in grid)
    num_linhas  = len(grid)

    colisao:      list[TileRect]               = []
    moedas:       list[tuple[float, float]]    = []
    inimigos:     list[InimigoDado]            = []
    checkpoints:  list[CheckpointDado]         = []
    saida:        "SaidaDado | None"           = None
    insetos:            list[InsetoDado]             = []
    plataformas_moveis: list[PlataformaMovelDado]    = []
    armadilhas:         list[ArmadilhaDado]          = []
    objetos:            list[ObjDado]               = []
    spawn:              tuple[float, float] | None  = None

    for lin, linha in enumerate(grid):
        for col, tile in enumerate(linha):
            mx = col * T
            my = lin * T

            if tile == "#":
                colisao.append((mx, my, T, T))

            elif tile == "M":
                moedas.append((float(mx + T // 2), float(my + T // 2)))

            elif tile == "E":
                x_min, x_max = _patrulha_txt(grid, lin, col, num_colunas, T)
                inimigos.append(InimigoDado(
                    x=mx, y=my,
                    x_min=x_min, x_max=x_max,
                    velocidade=110.0,
                    tipo="patrulheiro",
                ))

            elif tile == "S":
                x_min, x_max = _patrulha_txt(grid, lin, col, num_colunas, T)
                inimigos.append(InimigoDado(
                    x=mx, y=my,
                    x_min=x_min, x_max=x_max,
                    velocidade=120.0,
                    tipo="cobra",
                ))

            elif tile == "I":
                # Inseto: posição topleft do tile em world-space.
                # Tipo padrão "wandering" — factory usa default.
                insetos.append(InsetoDado(x=mx, y=my))

            elif tile == "C":
                # Checkpoint: topleft do tile = posição do sprite.
                # O sprite tem HITBOX_W × HITBOX_H — posicionado no tile.
                checkpoints.append(CheckpointDado(x=mx, y=my))

            elif tile == "X":
                # Saída de fase: topleft do tile.
                # Apenas uma saída por fase — a última 'X' encontrada vence.
                saida = SaidaDado(x=mx, y=my)

            elif tile == "P":
                spawn = (float(mx), float(my))

    return MapData(
        largura_px  = num_colunas * T,
        altura_px   = num_linhas  * T,
        tile_size   = T,
        colisao     = colisao,
        spawn       = spawn,
        moedas      = moedas,
        inimigos    = inimigos,
        checkpoints = checkpoints,
        saida       = saida,
        insetos            = insetos,
        plataformas_moveis = plataformas_moveis,
        armadilhas         = armadilhas,
        objetos            = objetos,
    )


def _patrulha_txt(
    grid:        list[str],
    lin_inimigo: int,
    col_inimigo: int,
    num_colunas: int,
    T:           int,
) -> tuple[int, int]:
    """
    Calcula (x_min, x_max) de patrulha para um inimigo num grid .txt.

    Estratégia: scan de chão lateral
    ──────────────────────────────────
    A partir da coluna do inimigo, varre para esquerda e direita
    enquanto houver tile '#' na linha imediatamente abaixo (chão).
    Para no primeiro buraco ou na borda do mapa.

    Diagrama:
        linha N:    . . . E . . . . .
        linha N+1:  . # # # # # # . .
                      ←  scan  →
        x_min = col_esq × T
        x_max = (col_dir + 1) × T   ← borda direita do último tile

    Fallback: sem chão detectado → ±3 tiles (inimigo suspenso no ar).

    Parâmetros
    ──────────
    grid        : linhas do arquivo .txt
    lin_inimigo : índice de linha do inimigo
    col_inimigo : índice de coluna do inimigo
    num_colunas : largura do grid (para clamping)
    T           : config.TILE_SIZE em pixels
    """
    lin_chao = lin_inimigo + 1

    def tem_chao(col: int) -> bool:
        """True se (lin_chao, col) for tile sólido '#'."""
        if not (0 <= col < num_colunas):
            return False
        if lin_chao >= len(grid):
            return False
        row = grid[lin_chao]
        return col < len(row) and row[col] == "#"

    col_esq = col_inimigo
    while col_esq > 0 and tem_chao(col_esq - 1):
        col_esq -= 1

    col_dir = col_inimigo
    while col_dir < num_colunas - 1 and tem_chao(col_dir + 1):
        col_dir += 1

    # Fallback: inimigo sem chão detectado
    if col_esq == col_inimigo and col_dir == col_inimigo:
        col_esq = max(0,               col_inimigo - 3)
        col_dir = min(num_colunas - 1, col_inimigo + 3)

    return col_esq * T, (col_dir + 1) * T


# ══════════════════════════════════════════════════════════════════════
# LOADER TMX — Tiled Map Editor via pytmx
# ══════════════════════════════════════════════════════════════════════

# Nomes das camadas esperadas no arquivo .tmx.
# Centralizados como constantes para que renomear no Tiled exija apenas
# alterar aqui, sem caçar strings espalhadas pelo código.
_LAYER_COLISAO    = "colisao"      # TileLayer com tiles sólidos
_LAYER_DECORACAO  = "decoracao"    # TileLayer visual — ignorado no loader
_LAYER_OBJETOS    = "objetos"      # ObjectLayer com entidades

# Mapeamento nome de objeto → tipo semântico.
# Adicionar um novo tipo: incluir aqui + tratar em _processar_objeto_tmx().
_TIPOS_OBJETO: dict[str, str] = {
    "player_spawn": "player_spawn",
    "moeda":        "moeda",
    "inimigo":      "inimigo",
    "checkpoint":   "checkpoint",   # processado → MapData["checkpoints"]
    "saida_fase":   "saida_fase",   # processado → MapData["saida"]
    "inseto":         "inseto",         # processado → MapData["insetos"]
    "plataforma_movel":  "plataforma_movel",   # processado → MapData["plataformas_moveis"]
    "planta_carnivora":  "planta_carnivora",   # processado → MapData["armadilhas"]
    "pedra_rolante":     "pedra_rolante",      # processado → MapData["armadilhas"]
    "galho_caindo":      "galho_caindo",       # processado → MapData["armadilhas"]
}


def _carregar_tmx(caminho: str) -> MapData | None:
    """
    Carrega um mapa Tiled (.tmx) usando pytmx.

    Dependência opcional
    ─────────────────────
    pytmx é importado localmente para não quebrar o jogo em ambientes
    sem a biblioteca instalada. Apenas fases .tmx são afetadas.

    Camadas processadas
    ────────────────────
    TileLayer  "colisao"   → MapData["colisao"] (TileRects)
    ObjectLayer "objetos"  → MapData["spawn"], ["moedas"], ["inimigos"], ["objetos"]

    Conversão de escala
    ────────────────────
    O Tiled armazena posições em unidades do tilewidth do .tmx (ex: 16px).
    Convertemos para config.TILE_SIZE (40px) usando índices de grid:
        mundo_x = col_index × config.TILE_SIZE
        mundo_y = row_index × config.TILE_SIZE
    O índice é invariante: tile na coluna 3 é sempre a coluna 3,
    independente do tilewidth visual.

    Retorno
    ────────
    MapData preenchido, ou None em caso de erro.

    Parâmetros
    ──────────
    caminho : str   caminho para o arquivo .tmx
    """
    # ── Importação resiliente de pytmx ────────────────────────────────
    try:
        from pytmx.util_pygame import load_pygame as tmx_load_pygame
    except ImportError:
        print(
            "[LOADER] pytmx não instalado.\n"
            "         Execute: pip install pytmx\n"
            "         Fases .tmx estarão indisponíveis até a instalação."
        )
        return None

    # ── Carregamento do arquivo ───────────────────────────────────────
    try:
        tmx = tmx_load_pygame(caminho)
    except FileNotFoundError:
        print(f"[LOADER] Arquivo .tmx não encontrado: '{caminho}'")
        return None
    except Exception as exc:
        print(f"[LOADER] Erro ao parsear '{caminho}': {exc}")
        return None

    T = config.TILE_SIZE

    # Dimensões em pixels de mundo (índices × tamanho lógico)
    largura_px = tmx.width  * T
    altura_px  = tmx.height * T

    colisao:      list[TileRect]              = []
    moedas:       list[tuple[float, float]]   = []
    inimigos:     list[InimigoDado]           = []
    checkpoints:  list[CheckpointDado]        = []
    saida:        "SaidaDado | None"          = None
    insetos:            list[InsetoDado]            = []
    plataformas_moveis: list[PlataformaMovelDado]   = []
    armadilhas:         list[ArmadilhaDado]         = []
    objetos:            list[ObjDado]              = []
    spawn:              tuple[float, float] | None = None

    # ── Processa camadas ──────────────────────────────────────────────
    for layer in tmx.layers:
        nome = getattr(layer, "name", "").lower()

        # ── TileLayer de colisão ──────────────────────────────────────
        if nome == _LAYER_COLISAO:
            novos = _tiles_colisao_tmx(layer, tmx.width, tmx.height, T)
            colisao.extend(novos)

        # ── TileLayer de decoração ────────────────────────────────────
        elif nome == _LAYER_DECORACAO:
            pass   # ignorado no loader — apenas colisão importa aqui
                   # Futuro: retornar lista de blit decorativo

        # ── Object Layer ──────────────────────────────────────────────
        elif nome == _LAYER_OBJETOS:
            for obj in layer:
                # Passa tilewidth e tileheight do .tmx para que a função
                # converta pixel bruto → índice de grid → coordenada de mundo.
                # tmx.tilewidth é o tamanho visual do tile no Tiled (ex: 16 ou 32 px).
                resultado = _processar_objeto_tmx(
                    obj,
                    T       = T,
                    tmx_tw  = tmx.tilewidth,
                    tmx_th  = tmx.tileheight,
                    largura_px = largura_px,
                )
                if resultado is None:
                    continue

                tipo = resultado.get("tipo", "")

                if tipo == "player_spawn":
                    spawn = (float(resultado["x"]), float(resultado["y"]))
                elif tipo == "moeda":
                    moedas.append((float(resultado["x"]), float(resultado["y"])))
                elif tipo == "inimigo":
                    inimigos.append(InimigoDado(
                        x=resultado["x"],
                        y=resultado["y"],
                        x_min=resultado["props"].get("x_min", resultado["x"] - 5 * T),
                        x_max=resultado["props"].get("x_max", resultado["x"] + 5 * T),
                        velocidade=float(resultado["props"].get("velocidade", 110.0)),
                        tipo=str(resultado["props"].get("tipo", "patrulheiro")),
                        dano=int(resultado["props"].get("dano", 1)),
                    ))
                elif tipo == "checkpoint":
                    # Checkpoint: posição topleft no espaço do motor.
                    # Propriedades extras (ordem, nome) guardadas em props
                    # para uso futuro — não processadas agora.
                    checkpoints.append(CheckpointDado(
                        x=resultado["x"],
                        y=resultado["y"],
                    ))
                elif tipo == "inseto":
                    # Inseto: posição e propriedades do objeto Tiled.
                    insetos.append(InsetoDado(
                        x          = resultado["x"],
                        y          = resultado["y"],
                        tipo       = str(resultado["props"].get("tipo",       "wandering")),
                        velocidade = float(resultado["props"].get("velocidade", 28.0)),
                        area       = int(resultado["props"].get("area",        120)),
                    ))

                elif tipo in ("planta_carnivora", "pedra_rolante", "galho_caindo"):
                    # Armadilhas: posição + todas as props do Tiled passadas
                    # diretamente para create_trap() via ArmadilhaDado.
                    armadilhas.append(ArmadilhaDado(
                        tipo  = tipo,
                        x     = resultado["x"],
                        y     = resultado["y"],
                        props = resultado["props"],
                    ))

                elif tipo == "plataforma_movel":
                    # Plataforma móvel: posição, dimensões e parâmetros
                    # de movimento lidos das Custom Properties do Tiled.
                    # x_min/x_max/y_min/y_max em pixels do motor (não tiles).
                    p = resultado["props"]
                    plataformas_moveis.append(PlataformaMovelDado(
                        x             = resultado["x"],
                        y             = resultado["y"],
                        largura       = int(p.get("largura",       120)),
                        altura        = int(p.get("altura",         40)),
                        tipo_movimento= str(p.get("tipo_movimento", "horizontal")),
                        velocidade    = float(p.get("velocidade",    80.0)),
                        x_min         = int(p.get("x_min",          resultado["x"])),
                        x_max         = int(p.get("x_max",          resultado["x"] + 400)),
                        y_min         = int(p.get("y_min",          resultado["y"])),
                        y_max         = int(p.get("y_max",          resultado["y"] + 400)),
                    ))

                elif tipo == "saida_fase":
                    # Apenas uma saída por fase — última encontrada vence.
                    saida = SaidaDado(
                        x=resultado["x"],
                        y=resultado["y"],
                    )
                else:
                    # Tipo desconhecido / futuro → armazena genérico
                    objetos.append(ObjDado(
                        tipo=tipo,
                        x=resultado["x"],
                        y=resultado["y"],
                        props=resultado.get("props", {}),
                    ))

    return MapData(
        largura_px  = largura_px,
        altura_px   = altura_px,
        tile_size   = T,
        colisao     = colisao,
        spawn       = spawn,
        moedas      = moedas,
        inimigos    = inimigos,
        checkpoints = checkpoints,
        saida       = saida,
        insetos            = insetos,
        plataformas_moveis = plataformas_moveis,
        armadilhas         = armadilhas,
        objetos            = objetos,
    )


def _tiles_colisao_tmx(
    layer,
    largura_tiles: int,
    altura_tiles:  int,
    T:             int,
    regiao:        tuple[int, int, int, int] | None = None,
) -> list[TileRect]:
    """
    Extrai TileRects sólidos de uma TileLayer do pytmx.

    Cada célula com GID ≠ 0 é tratada como bloco sólido de colisão.
    A Surface visual do tile não é carregada aqui — apenas a posição.

    Parâmetro regiao (preparação para streaming)
    ─────────────────────────────────────────────
    Aceita (col_ini, col_fim, lin_ini, lin_fim) para carregar apenas um
    retângulo do grid. Quando None, carrega o mapa inteiro.
    API estável para futura implementação de chunks.

    Diagrama de conversão índice → mundo:
        col=2, row=1, T=40  →  Rect(80, 40, 40, 40)
        ┌──┬──┬──┬──┐
        │  │  │  │  │  row=0
        ├──┼──┼──┼──┤
        │  │  │██│  │  row=1, col=2  →  x=80, y=40
        └──┴──┴──┴──┘

    Parâmetros
    ──────────
    layer          : TileLayer do pytmx (iterável de TileElement)
    largura_tiles  : tmx.width  (colunas do grid)
    altura_tiles   : tmx.height (linhas do grid)
    T              : config.TILE_SIZE em pixels
    regiao         : opcional — (col_ini, col_fim, lin_ini, lin_fim)
    """
    # Determina o intervalo de iteração
    if regiao is not None:
        col_ini, col_fim, lin_ini, lin_fim = regiao
    else:
        col_ini, col_fim = 0, largura_tiles
        lin_ini, lin_fim = 0, altura_tiles

    resultado: list[TileRect] = []

    for lin in range(lin_ini, lin_fim):
        for col in range(col_ini, col_fim):
            try:
                gid = layer.data[lin][col]
            except (IndexError, AttributeError):
                continue

            if gid == 0:
                continue   # célula vazia — sem colisão

            # Posição de mundo: índice × tamanho lógico
            # independente do tilewidth visual do .tmx
            mx = col * T
            my = lin * T
            resultado.append((mx, my, T, T))

    return resultado


def _processar_objeto_tmx(
    obj,
    T:          int,
    tmx_tw:     int,
    tmx_th:     int,
    largura_px: int,
) -> ObjDado | None:
    """
    Converte um objeto pytmx em ObjDado com coordenadas no espaço do motor.

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    O PROBLEMA DAS DUAS ESCALAS
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    O Tiled trabalha em pixels visuais do tileset:
        tmx_tw = 16 px   →  coluna 2 = x_bruto = 32 px
        tmx_tw = 32 px   →  coluna 2 = x_bruto = 64 px

    O motor do Calango trabalha em pixels lógicos (config.TILE_SIZE):
        T = 40 px        →  coluna 2 = x_mundo = 80 px

    Se usarmos obj.x diretamente (int(obj.x)), o objeto aparecerá no
    lugar errado:

        Tiled 16px:  coluna 3 → obj.x = 48   → motor recebe x=48  ✗
        Esperado:    coluna 3 → índice = 3    → motor deveria ser 120  ✓

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    A SOLUÇÃO: ÍNDICE DE GRID COMO UNIDADE INVARIANTE
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    O índice de coluna/linha é o mesmo em qualquer escala — é a unidade
    que não muda ao trocar o tileset visual. A conversão é:

        Passo 1 — pixel bruto → índice de grid
        ────────────────────────────────────────
            col = round(obj.x / tmx_tw)
            row = round(obj.y / tmx_th)

        Usamos round() em vez de int() para evitar erros de dízima:
            obj.x = 47.9999...  →  int() = 47  →  col = 2  ✗ (off-by-one)
            obj.x = 47.9999...  →  round() = 48 →  col = 3  ✓

        Passo 2 — índice de grid → pixel de mundo (escala do motor)
        ─────────────────────────────────────────────────────────────
            mundo_x = col * T
            mundo_y = row * T

    Diagrama comparativo com tmx_tw=16, T=40:

        Tiled (16px/tile)        Motor (40px/tile)
        ┌──┬──┬──┬──┬──┐         ┌────┬────┬────┬────┬────┐
        │  │  │  │P │  │         │    │    │    │ P  │    │
        └──┴──┴──┴──┴──┘         └────┴────┴────┴────┴────┘
        col 0  1  2  3  4         col  0    1    2    3    4
        obj.x = 3 × 16 = 48      mundo_x = 3 × 40 = 120

    Sem a conversão:    x_mundo = int(48) = 48  px  ← errado
    Com a conversão:    col = round(48/16) = 3
                        x_mundo = 3 × 40  = 120 px  ← correto

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    CASO ESPECIAL: tmx_tw == T
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    Se o Tiled for configurado com tiles de 40×40 (igual ao motor),
    a conversão round(obj.x / 40) × 40 é idempotente e não altera
    o valor — sem custo e sem risco de regressão.

    Parâmetros
    ──────────
    obj        : TiledObject do pytmx
                 Atributos relevantes: obj.name (str), obj.x (float),
                 obj.y (float), obj.properties (dict)
    T          : int   — config.TILE_SIZE (tamanho lógico do motor, px)
    tmx_tw     : int   — tmx.tilewidth  (tamanho visual do tile no .tmx, px)
    tmx_th     : int   — tmx.tileheight (tamanho visual do tile no .tmx, px)
    largura_px : int   — largura do mapa em pixels de motor
                         (usado para clamping futuro de x_max em InimigoDado)

    Retorno
    ────────
    ObjDado com coordenadas em pixels do motor (espaço lógico), ou None
    caso obj.name seja vazio e o objeto não deva ser processado.
    """
    tipo = getattr(obj, "name", None) or ""
    tipo = tipo.strip().lower()

    # ── Conversão de escala: pixel bruto → índice de grid → pixel de motor ──
    #
    # Guarda anti-zero: se tmx_tw ou tmx_th forem 0 por algum bug do arquivo
    # .tmx, evitamos ZeroDivisionError e usamos o valor bruto como fallback.
    tw = tmx_tw if tmx_tw > 0 else T
    th = tmx_th if tmx_th > 0 else T

    col: int = round(obj.x / tw)   # índice de coluna no grid do Tiled
    row: int = round(obj.y / th)   # índice de linha   no grid do Tiled

    mundo_x: int = col * T         # pixel no espaço de mundo do motor
    mundo_y: int = row * T         # pixel no espaço de mundo do motor

    # ── Propriedades customizadas do Tiled ────────────────────────────
    # pytmx pode retornar PropertyDict (objeto com interface de dict)
    # ou dict padrão — normalizamos para dict simples.
    props_raw = getattr(obj, "properties", {}) or {}
    try:
        props: dict = dict(props_raw)
    except (TypeError, ValueError):
        props = {}

    return ObjDado(
        tipo  = tipo if tipo else "desconhecido",
        x     = mundo_x,
        y     = mundo_y,
        props = props,
    )


# ══════════════════════════════════════════════════════════════════════
# UTILITÁRIO DE DIAGNÓSTICO
# ══════════════════════════════════════════════════════════════════════

def inspecionar_mapa(dados: MapData) -> str:
    """
    Retorna um resumo legível de um MapData para debug no terminal.

    Uso:
        dados = carregar_mapa("fase1.txt")
        print(inspecionar_mapa(dados))

    Saída exemplo:
        ┌─ MapData ─────────────────────────────────┐
        │  dimensões : 3000 × 600 px  (tile: 40px)  │
        │  colisão   : 245 tiles                     │
        │  moedas    : 32                            │
        │  inimigos  : 7                             │
        │  spawn     : (40.0, 40.0)                  │
        │  objetos   : 0 genéricos                   │
        └────────────────────────────────────────────┘

    Parâmetros
    ──────────
    dados : MapData   resultado de carregar_mapa()
    """
    linhas = [
        "┌─ MapData ──────────────────────────────────────────┐",
        f"│  dimensões : {dados['largura_px']} × {dados['altura_px']} px"
        f"  (tile: {dados['tile_size']}px)",
        f"│  colisão   : {len(dados['colisao'])} tiles",
        f"│  moedas    : {len(dados['moedas'])}",
        f"│  inimigos  : {len(dados['inimigos'])}",
        f"│  spawn     : {dados['spawn']}",
        f"│  checkpoints: {len(dados['checkpoints'])}",
        f"│  saida      : {'sim' if dados['saida'] else 'não'}",
        f"│  insetos    : {len(dados['insetos'])}",
        f"│  plat.moveis: {len(dados['plataformas_moveis'])}",
        f"│  armadilhas : {len(dados['armadilhas'])}",
        f"│  objetos   : {len(dados['objetos'])} genéricos",
        "└────────────────────────────────────────────────────┘",
    ]
    return "\n".join(linhas)
