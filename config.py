"""
config.py
═════════
Módulo de configuração central do projeto "Plataforma 2D — Pygame".

Todas as constantes globais do jogo vivem aqui. A convenção é simples:
  • MAIÚSCULAS_COM_UNDERSCORE  →  constante imutável (PEP 8 § Naming)
  • Anotações de tipo opcionais →  documentam a intenção sem overhead

Por que centralizar?
────────────────────
Evita "números mágicos" espalhados pelo código. Ao precisar ajustar
velocidade, resolução ou uma cor, você edita um único lugar e a mudança
se propaga para todos os módulos automaticamente.

Organização
───────────
  1. Tela
  2. Mundo & Grid
  3. Taxa de Quadros
  4. Física do Jogador
  5. Paleta de Cores
  6. Caminhos de Assets
"""

import pathlib


# ══════════════════════════════════════════════════════════════════════
# 0. RAIZ DO PROJETO
# ══════════════════════════════════════════════════════════════════════
# pathlib.Path(__file__).parent resolve para a pasta que contém este
# arquivo, independente de onde o jogo é executado. Todos os caminhos
# de assets são construídos a partir daqui para garantir portabilidade
# entre Windows, macOS e Linux.

BASE_DIR: pathlib.Path = pathlib.Path(__file__).parent


# ══════════════════════════════════════════════════════════════════════
# 1. TELA
# ══════════════════════════════════════════════════════════════════════

SCREEN_WIDTH:  int = 800          # largura da janela em pixels
SCREEN_HEIGHT: int = 600          # altura da janela em pixels
TITLE:         str = "Plataforma 2D — Pygame"


# ══════════════════════════════════════════════════════════════════════
# 2. MUNDO & GRID
# ══════════════════════════════════════════════════════════════════════

# Cada caractere em fase1.txt ocupa um quadrado de TILE_SIZE × TILE_SIZE px.
# Com 75 colunas: 75 × 40 = 3 000 px → WORLD_WIDTH padrão.
TILE_SIZE:   int = 40

# Largura padrão do mundo em pixels.
# Usado pela câmera para calcular o clamp do offset.
# Valor sobrescrito dinamicamente quando o mapa real tem largura diferente.
WORLD_WIDTH: int = 3_000          # 3 000 px = 75 tiles × 40 px


# ══════════════════════════════════════════════════════════════════════
# 3. TAXA DE QUADROS
# ══════════════════════════════════════════════════════════════════════

# pygame.time.Clock.tick(FPS) dorme o tempo necessário para manter este
# alvo e retorna o delta time real em ms — convertido para segundos no loop.
FPS: int = 60


# ══════════════════════════════════════════════════════════════════════
# 4. FÍSICA DO JOGADOR
# ══════════════════════════════════════════════════════════════════════
# Todas as grandezas usam px/s ou px/s² para serem independentes do FPS.
# A integração de Euler no player.py garante:
#   vel += aceleração × dt
#   pos += vel       × dt

PLAYER_SPEED:        float = 250.0    # velocidade horizontal máxima (px/s)
PLAYER_GRAVITY:      float = 1_200.0  # aceleração gravitacional para baixo (px/s²)
PLAYER_JUMP_FORCE:   float = -550.0   # impulso inicial do pulo — negativo = para cima (px/s)
PLAYER_STOMP_BOUNCE: float = -350.0   # impulso após pisão em inimigo (px/s)


# ══════════════════════════════════════════════════════════════════════
# 5. PALETA DE CORES  (R, G, B)  —  valores 0–255
# ══════════════════════════════════════════════════════════════════════
# Agrupadas por função para facilitar a leitura e futuras trocas de tema.

# ── Neutras ───────────────────────────────────────────────────────────
BLACK    = (  0,   0,   0)
WHITE    = (255, 255, 255)

# ── Interface & HUD ───────────────────────────────────────────────────
YELLOW   = (255, 220,   0)   # score, título do menu, moedas
GOLD     = (255, 180,   0)   # borda das moedas, high score
RED      = (220,  50,  50)   # jogador, texto de Game Over

# ── Cenário ───────────────────────────────────────────────────────────
SKY_BLUE = (135, 206, 235)   # fundo do céu
GREEN    = ( 50, 200,  80)   # plataformas e chão

# ── Inimigos ──────────────────────────────────────────────────────────
PURPLE   = (160,  30, 200)   # corpo do inimigo patrulheiro
DARK_RED = (160,  20,  20)   # olhos e detalhes do inimigo

# ── Miscelânea ────────────────────────────────────────────────────────
BLUE     = ( 50, 100, 220)   # reservado para uso futuro (UI, efeitos)


# ══════════════════════════════════════════════════════════════════════
# 6. CAMINHOS DE ASSETS
# ══════════════════════════════════════════════════════════════════════
# Construídos com pathlib e convertidos para str para compatibilidade
# com pygame.mixer.music.load() e pygame.image.load(), que não aceitam
# objetos Path diretamente em todas as versões do Pygame.
#
# Estrutura esperada de pastas:
#   projeto/
#   ├── audio/
#   │   ├── musica_menu.ogg
#   │   ├── musica_fase.ogg
#   │   ├── sfx_pulo.wav
#   │   ├── sfx_moeda.wav
#   │   ├── sfx_morte.wav
#   │   ├── sfx_stomp.wav
#   │   └── sfx_vitoria.wav
#   ├── sprites/          ← reservado para spritesheets futuras
#   ├── fase1.txt
#   └── *.py

_AUDIO_DIR:   pathlib.Path = BASE_DIR / "audio"
_SPRITES_DIR: pathlib.Path = BASE_DIR / "sprites"

# Músicas de fundo (streaming — não carregadas na RAM)
MUSICA_MENU: str = str(_AUDIO_DIR / "musica_menu.ogg")
MUSICA_FASE: str = str(_AUDIO_DIR / "musica_fase.ogg")

# Efeitos sonoros (carregados na RAM para disparo imediato)
SFX_PULO:    str = str(_AUDIO_DIR / "sfx_pulo.wav")
SFX_MOEDA:   str = str(_AUDIO_DIR / "sfx_moeda.wav")
SFX_MORTE:   str = str(_AUDIO_DIR / "sfx_morte.wav")
SFX_STOMP:   str = str(_AUDIO_DIR / "sfx_stomp.wav")
SFX_VITORIA: str = str(_AUDIO_DIR / "sfx_vitoria.wav")

# Fases
FASE_1: str = str(BASE_DIR / "fase1.txt")
