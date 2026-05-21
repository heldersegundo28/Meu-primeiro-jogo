# main.py
# Ponto de entrada do jogo. Contém a classe Game e o game loop principal.

import sys
import pygame
import config
from player   import Player
from sprites  import Plataforma
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

        # HUD simples: posição X no mundo (útil para depuração)
        fonte = pygame.font.SysFont(None, 28)
        hud = fonte.render(
            f"X mundo: {int(self.player.x)}  |  offset: {int(self.camera.offset_x)}",
            True,
            config.BLACK,
        )
        self.screen.blit(hud, (10, 10))

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
