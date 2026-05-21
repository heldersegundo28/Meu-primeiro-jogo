# main.py
# Ponto de entrada do jogo. Contém a classe Game e o game loop principal.

import sys
import pygame
import config
from player   import Player
from sprites  import Plataforma, Moeda
from camera   import Camera


class Game:
    """Classe principal que encapsula todo o estado e a lógica do jogo."""

    def __init__(self):
        # --- Inicialização do Pygame ---
        pygame.init()
        self.screen = pygame.display.set_mode(
            (config.SCREEN_WIDTH, config.SCREEN_HEIGHT)
        )
        pygame.display.set_caption(config.TITLE)

        self.clock   = pygame.time.Clock()
        self.running = True

        # --- Câmera ---------------------------------------------------
        self.camera = Camera()

        # --- Plataformas ----------------------------------------------
        # O nível se estende por WORLD_WIDTH (3000px).
        # Coordenadas são de mundo — a câmera cuida do ajuste na tela.
        self.plataformas = pygame.sprite.Group()

        plataformas_dados = [
            # (  x,    y,  largura, altura)   descrição
            (    0,  540,   3000,     20),  # chão contínuo ao longo de todo o mundo
            (  100,  400,    180,     18),  # plataforma baixa — início
            (  380,  320,    150,     18),  # degrau intermediário
            (  600,  430,    120,     18),  # desce um pouco
            (  800,  350,    200,     18),  # longa após o primeiro gap
            ( 1080,  260,    140,     18),  # subida
            ( 1300,  380,    160,     18),  # descida
            ( 1500,  300,    100,     18),  # plataforma pequena (desafiadora)
            ( 1680,  430,    180,     18),  # retorno ao nível médio
            ( 1950,  250,    200,     18),  # plataforma alta
            ( 2200,  370,    150,     18),  # zigue-zague
            ( 2420,  280,    120,     18),  # subida acentuada
            ( 2600,  400,    180,     18),  # planície
            ( 2820,  320,    160,     18),  # penúltima
            ( 2900,  420,     80,     18),  # chegada — pequena e difícil
        ]
        for x, y, w, h in plataformas_dados:
            self.plataformas.add(Plataforma(x, y, w, h))

        # --- Jogador --------------------------------------------------
        self.player = Player(
            x=config.SCREEN_WIDTH // 2 - 20,
            y=100,
        )

        # --- Pontuação ------------------------------------------------
        self.score = 0

        # --- Moedas ---------------------------------------------------
        # Cada moeda é posicionada pelo CENTRO (x, y).
        # Convenção de level design: y = topo_da_plataforma - 30
        # para a moeda flutuar visivelmente acima do bloco.
        self.moedas = pygame.sprite.Group()

        moedas_dados = [
            # Início do mundo — tutorial implícito
            ( 150,  370),  # acima da plataforma (100, 400)
            ( 200,  370),
            ( 250,  370),
            # Degrau intermediário
            ( 430,  290),  # acima de (380, 320)
            ( 460,  290),
            # Plataforma que desce
            ( 640,  400),  # acima de (600, 430)
            # Plataforma longa
            ( 850,  320),  # acima de (800, 350)
            ( 900,  320),
            ( 950,  320),
            # Subida — recompensa por alcançar plataforma alta
            (1110,  230),  # acima de (1080, 260)
            (1150,  230),
            # Descida
            (1360,  350),  # acima de (1300, 380)
            # Plataforma pequena — desafiadora, recompensa maior
            (1520,  270),  # acima de (1500, 300)
            (1540,  270),
            (1560,  270),
            # Retorno ao nível médio
            (1740,  400),  # acima de (1680, 430)
            (1790,  400),
            # Plataforma alta — prêmio por alcançar o topo
            (2010,  220),  # acima de (1950, 250)
            (2050,  220),
            (2090,  220),
            (2130,  220),
            # Zigue-zague
            (2260,  340),  # acima de (2200, 370)
            (2300,  340),
            # Subida acentuada
            (2460,  250),  # acima de (2420, 280)
            (2500,  250),
            # Planície
            (2650,  370),  # acima de (2600, 400)
            (2700,  370),
            (2730,  370),
            # Penúltima
            (2860,  290),  # acima de (2820, 320)
            # Chegada — 3 moedas no bloco difícil final
            (2910,  390),  # acima de (2900, 420)
            (2930,  390),
            (2950,  390),
        ]
        for cx, cy in moedas_dados:
            self.moedas.add(Moeda(cx, cy))

    # ------------------------------------------------------------------
    # 1. EVENTOS
    # ------------------------------------------------------------------
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False

            self.player.handle_jump(event)

    # ------------------------------------------------------------------
    # 2. ATUALIZAÇÃO
    # ------------------------------------------------------------------
    def update(self, dt: float):
        self.player.update(dt, self.plataformas)

        # Colisão jogador ↔ moedas
        # spritecollide retorna a lista de moedas tocadas neste frame.
        # dokill=True remove cada moeda tocada dos seus grupos automaticamente
        # — não é necessário chamar moeda.kill() manualmente.
        coletadas = pygame.sprite.spritecollide(
            self.player, self.moedas, dokill=True
        )
        self.score += len(coletadas) * 10   # +10 por moeda (usa Moeda.VALOR implicitamente)

        # A câmera sempre atualiza DEPOIS do jogador para ler a posição final.
        self.camera.update(self.player.rect)

    # ------------------------------------------------------------------
    # 3. RENDERIZAÇÃO
    # ------------------------------------------------------------------
    def draw(self):
        self.screen.fill(config.SKY_BLUE)

        # Plataformas — desenhamos manualmente para aplicar o offset da câmera.
        # Group.draw() não permite ajuste de posição, por isso iteramos.
        #
        # Por que não usar Group.draw() aqui?
        # ─────────────────────────────────────
        # Group.draw() usa sprite.rect diretamente — que está em coordenadas
        # de mundo. Para aplicar o offset da câmera precisamos de um rect
        # temporário ajustado, o que exige o loop manual abaixo.
        for plat in self.plataformas:
            self.screen.blit(plat.image, self.camera.aplicar(plat.rect))

        # Jogador
        rect_tela = self.camera.aplicar(self.player.rect)
        pygame.draw.rect(self.screen, self.player.COLOR, rect_tela)

        # Moedas — mesmo padrão das plataformas: blit com offset da câmera
        for moeda in self.moedas:
            self.screen.blit(moeda.image, self.camera.aplicar(moeda.rect))

        # --- HUD ------------------------------------------------------
        # Criamos a fonte uma vez por frame. Para produção, mova para __init__.
        fonte      = pygame.font.SysFont(None, 30)
        fonte_score = pygame.font.SysFont(None, 36)

        # Linha de debug (cinza claro, canto superior esquerdo)
        debug = fonte.render(
            f"X: {int(self.player.x)}  offset: {int(self.camera.offset_x)}"
            f"  moedas: {len(self.moedas)}",
            True,
            config.BLACK,
        )
        self.screen.blit(debug, (10, 10))

        # Score em destaque (canto superior direito)
        score_surf = fonte_score.render(f"Score: {self.score}", True, config.YELLOW)
        # Alinha pela borda direita com margem de 10px
        score_rect = score_surf.get_rect(topright=(config.SCREEN_WIDTH - 10, 10))
        # Sombra para legibilidade sobre o céu
        sombra = fonte_score.render(f"Score: {self.score}", True, config.BLACK)
        self.screen.blit(sombra, score_rect.move(2, 2))
        self.screen.blit(score_surf, score_rect)

        pygame.display.flip()

    # ------------------------------------------------------------------
    # GAME LOOP
    # ------------------------------------------------------------------
    def run(self):
        while self.running:
            dt = self.clock.tick(config.FPS) / 1000.0

            self.handle_events()
            self.update(dt)
            self.draw()

        self.quit()

    def quit(self):
        pygame.quit()
        sys.exit()


# ------------------------------------------------------------------
# PONTO DE ENTRADA
# ------------------------------------------------------------------
if __name__ == "__main__":
    game = Game()
    game.run()
