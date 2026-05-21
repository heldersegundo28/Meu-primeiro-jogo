# main.py
# Ponto de entrada do jogo. Contém a classe Game e o game loop principal.

import sys
import pygame
import config
from player import Player
from sprites import Plataforma


class Game:
    """Classe principal que encapsula todo o estado e a lógica do jogo."""

    def __init__(self):
        # --- Inicialização do Pygame ---
        pygame.init()
        self.screen = pygame.display.set_mode(
            (config.SCREEN_WIDTH, config.SCREEN_HEIGHT)
        )
        pygame.display.set_caption(config.TITLE)

        # Clock controla o FPS e fornece o delta time (dt)
        self.clock = pygame.time.Clock()
        self.running = True

        # --- Plataformas -----------------------------------------------
        # pygame.sprite.Group agrupa sprites para desenho e colisão em lote.
        self.plataformas = pygame.sprite.Group()

        plataformas_dados = [
            # (x,   y,   largura, altura)  — descrição
            (  0,  540,  800,     20),   # chão — cobre toda a largura
            (100,  400,  180,     18),   # plataforma flutuante esquerda
            (480,  300,  150,     18),   # plataforma flutuante direita
        ]
        for x, y, w, h in plataformas_dados:
            self.plataformas.add(Plataforma(x, y, w, h))

        # --- Jogador ---------------------------------------------------
        # Começa no topo da tela, cai e pousa no chão ao iniciar
        self.player = Player(
            x=config.SCREEN_WIDTH // 2 - 20,
            y=100,
        )

    # ------------------------------------------------------------------
    # 1. EVENTOS — "O que o jogador quer fazer?"
    # ------------------------------------------------------------------
    def handle_events(self):
        """
        Lê e processa todos os eventos gerados pelo sistema operacional
        e pelo jogador (teclado, mouse, fechar janela, etc.).
        Deve ser chamado uma vez por frame, antes de qualquer atualização.
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:          # Botão [X] da janela
                self.running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:   # ESC também encerra
                    self.running = False

            # Repassa o evento ao jogador (ele filtra o que lhe interessa)
            self.player.handle_jump(event)

    # ------------------------------------------------------------------
    # 2. ATUALIZAÇÃO — "O que muda no mundo a cada frame?"
    # ------------------------------------------------------------------
    def update(self, dt):
        """
        Avança a lógica do jogo em um passo de tempo (dt = delta time).
        Aqui ficará: física, colisões, IA, animações, pontuação, etc.

        Parâmetro dt (segundos desde o último frame) torna o movimento
        independente do FPS — ex.: velocidade * dt = pixels/segundo reais.
        """
        self.player.update(dt, self.plataformas)

    # ------------------------------------------------------------------
    # 3. RENDERIZAÇÃO — "O que o jogador vai ver?"
    # ------------------------------------------------------------------
    def draw(self):
        """
        Desenha o estado atual do jogo na tela.
        Ordem importa: o que for desenhado por último fica na frente.

        Padrão obrigatório:
          1. Limpa a tela (fill)       ← apaga o frame anterior
          2. Desenha todos os objetos
          3. Inverte os buffers (flip) ← exibe o frame concluído
        """
        # 3a. Limpa o frame anterior com a cor de fundo
        self.screen.fill(config.SKY_BLUE)

        # 3b. Desenha os objetos do jogo (ordem = profundidade: fundo → frente)

        # Plataformas (Group.draw usa image+rect de cada sprite automaticamente)
        self.plataformas.draw(self.screen)

        self.player.draw(self.screen)

        # 3c. Envia o buffer preparado para o monitor (double buffering)
        pygame.display.flip()

    # ------------------------------------------------------------------
    # GAME LOOP
    # ------------------------------------------------------------------
    def run(self):
        """
        Loop principal: roda indefinidamente até self.running = False.
        Sequência garantida a cada frame:
            eventos → atualização → renderização
        """
        while self.running:
            # clock.tick(FPS) dorme o tempo necessário para manter o FPS
            # alvo e retorna os milissegundos desde o último frame.
            dt = self.clock.tick(config.FPS) / 1000.0  # converte para segundos

            self.handle_events()
            self.update(dt)
            self.draw()

        self.quit()

    def quit(self):
        """Encerra o Pygame e fecha o processo de forma limpa."""
        pygame.quit()
        sys.exit()


# ------------------------------------------------------------------
# PONTO DE ENTRADA
# ------------------------------------------------------------------
if __name__ == "__main__":
    game = Game()
    game.run()
