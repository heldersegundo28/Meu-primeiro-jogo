# main.py
# Ponto de entrada do jogo. Contém a classe Game e o game loop principal.

import sys
import pygame
import config
from player   import Player
from sprites  import Plataforma, Moeda, Inimigo
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

        # --- Inimigos -------------------------------------------------
        # Inimigo(x, y, x_min, x_max, velocidade)
        # x, y   → topleft do sprite em coords de mundo
        # x_min  → borda esquerda da patrulha (rect.left mínimo)
        # x_max  → borda direita  da patrulha (rect.right máximo)
        # Posicionamos cada inimigo em plataformas longas o suficiente
        # para a patrulha ser visível e desafiadora.
        self.inimigos = pygame.sprite.Group()

        inimigos_dados = [
            # (  x,    y,  x_min,  x_max,  vel)   plataforma base
            (  810,  310,    800,   1000,  110),  # plat longa x=800
            (  860,  310,    800,   1000,  150),  # segundo inimigo, mais rápido
            ( 1960,  210,   1950,   2150,  130),  # plat alta x=1950
            ( 2050,  210,   1950,   2150,   90),  # segundo, mais lento
            ( 2610,  360,   2600,   2780,  120),  # planície x=2600
            ( 1090,  220,   1080,   1220,  100),  # subida x=1080
            ( 1690,  390,   1680,   1860,  140),  # retorno x=1680
        ]
        for x, y, xmin, xmax, vel in inimigos_dados:
            self.inimigos.add(Inimigo(x, y, xmin, xmax, vel))

        # --- Spawn do jogador (usado no respawn) ----------------------
        # Guardamos a posição inicial para poder reiniciar sem recriar tudo.
        self._spawn_x: float = float(config.SCREEN_WIDTH // 2 - 20)
        self._spawn_y: float = 100.0

    # ------------------------------------------------------------------
    # COLISÃO COM INIMIGOS — pisão vs. toque lateral/frontal
    # ------------------------------------------------------------------
    def _checar_colisao_inimigos(self):
        """
        Distingue duas situações para cada inimigo tocado neste frame:

        ① PISÃO (stomp) — jogador elimina o inimigo
           Condições simultâneas:
             a) vel_y > 0          → jogador está caindo (não subindo)
             b) player.rect.bottom ≤ inimigo.rect.centery
                                   → a base do jogador ainda está acima
                                      da linha média do inimigo
           Resultado: inimigo.kill(), +50 pontos, impulso vertical.

        ② TOQUE LATERAL / POR BAIXO — inimigo elimina o jogador
           Qualquer colisão que não satisfaça as condições acima.
           Resultado: respawn.

        Por que 'rect.centery' como limiar e não 'rect.top'?
        ──────────────────────────────────────────────────────
        Usar rect.top seria muito restritivo: o jogador precisaria
        pousar no pixel exato do topo, o que em 60 FPS pode ser
        facilmente "pulado" em um único frame rápido.
        Usar rect.centery dá uma janela de tolerância de metade da
        altura do inimigo, tornando o pisão confiável sem parecer
        injusto — é a mesma técnica usada no Super Mario Bros.
        """

        # dokill=False porque decidimos aqui se mata, não o Pygame
        colididos = pygame.sprite.spritecollide(
            self.player, self.inimigos, dokill=False
        )
        if not colididos:
            return

        p = self.player
        pisou_algum = False

        for inimigo in colididos:
            caindo          = p.vel_y > 0
            base_acima_meio = p.rect.bottom <= inimigo.rect.centery

            if caindo and base_acima_meio:
                # ── Pisão confirmado ──────────────────────────────────
                inimigo.kill()                      # remove de todos os grupos
                self.score += 50                    # bônus de eliminação
                p.vel_y     = -350.0                # impulso: mini-pulo pós-pisão
                p.no_chao   = False                 # permite encadear pulos
                pisou_algum = True
            # else: colisão lateral/inferior — tratado após o loop

        # Se houve ao menos um pisão, não aplicamos o respawn —
        # o jogador pode ter acertado dois inimigos no mesmo frame.
        if not pisou_algum:
            self._respawn()

    # ------------------------------------------------------------------
    # RESPAWN
    # ------------------------------------------------------------------
    def _respawn(self):
        """
        Reinicia o jogador na posição de spawn sem recriar o nível.

        O que é resetado:
          • posição e velocidade do jogador
          • câmera (volta ao início)
          • score zerado

        O que é PRESERVADO (decisão de design):
          • moedas já coletadas permanecem coletadas
            → penalidade é perder o score, não refazer tudo
          • inimigos continuam onde estão

        Para um reset completo de fase, chame self.__init__() em vez
        disso — mas isso recria a janela, o que causa um flash visível.
        A abordagem abaixo é instantânea e sem artefatos visuais.
        """
        # Reseta estado do jogador
        self.player.x      = self._spawn_x
        self.player.y      = self._spawn_y
        self.player.vel_x  = 0.0
        self.player.vel_y  = 0.0
        self.player.no_chao = False
        self.player.rect.topleft = (int(self._spawn_x), int(self._spawn_y))

        # Reseta câmera para o início do mundo
        self.camera.offset_x = 0.0

        # Penalidade: perde o score acumulado
        self.score = 0

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

        # Atualiza inimigos (movimento de patrulha)
        self.inimigos.update(dt)

        # Colisão jogador ↔ moedas
        # spritecollide retorna a lista de moedas tocadas neste frame.
        # dokill=True remove cada moeda tocada dos seus grupos automaticamente
        # — não é necessário chamar moeda.kill() manualmente.
        coletadas = pygame.sprite.spritecollide(
            self.player, self.moedas, dokill=True
        )
        self.score += len(coletadas) * 10   # +10 por moeda (usa Moeda.VALOR implicitamente)

        # Colisão jogador ↔ inimigos — dois desfechos possíveis
        self._checar_colisao_inimigos()

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

        # Inimigos
        for inimigo in self.inimigos:
            self.screen.blit(inimigo.image, self.camera.aplicar(inimigo.rect))

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
