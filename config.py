# config.py
# Centraliza todas as constantes do jogo.
# Alterar um valor aqui reflete em todo o projeto automaticamente.

# --- Tela ---
SCREEN_WIDTH  = 800
SCREEN_HEIGHT = 600
TITLE         = "Meu Jogo de Plataforma 2D"

# --- Mundo ---
# Largura total do nível em pixels. A câmera desliza dentro desse espaço.
# WORLD_WIDTH deve ser >= SCREEN_WIDTH (senão não há o que rolar).
WORLD_WIDTH = 3000

# Tamanho de um tile em pixels (usado pelo carregador de fase)
# Cada caractere em fase1.txt representa um quadrado de TILE_SIZE × TILE_SIZE px.
TILE_SIZE = 40

# --- Taxa de Quadros ---
FPS = 60  # O game loop tentará rodar exatamente 60 vezes por segundo

# --- Cores (R, G, B) ---
BLACK      = (0,   0,   0)
WHITE      = (255, 255, 255)
RED        = (220, 50,  50)
GREEN      = (50,  200, 80)
BLUE       = (50,  100, 220)
SKY_BLUE   = (135, 206, 235)  # cor de fundo padrão da cena
YELLOW     = (255, 220,  0)   # moedas e elementos dourados
GOLD       = (255, 180,  0)   # borda/detalhe das moedas
PURPLE     = (160,  30, 200)  # corpo do inimigo
DARK_RED   = (160,  20,  20)  # olhos/detalhe do inimigo
