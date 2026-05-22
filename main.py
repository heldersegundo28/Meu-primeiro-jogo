# main.py
# Ponto de entrada do jogo — gerencia a Máquina de Estados principal.
#
# Estados possíveis (self.estado)
# ─────────────────────────────────────────────────────────────────────
#   "MENU"      → tela inicial; nada se move; aguarda ESPAÇO ou ESC
#   "JOGANDO"   → gameplay ativo; física, colisões e câmera rodam
#   "GAME_OVER" → jogador morreu; cena congelada; aguarda R ou M
#   "VITORIA"   → todas as moedas coletadas; aguarda R ou M
#
# Por que strings e não Enum ou constantes inteiras?
# ─────────────────────────────────────────────────────────────────────
# Strings são legíveis nos prints de debug, sem precisar importar nada
# extra. Para projetos maiores, um Enum é preferível (evita typos).
# Neste estágio do aprendizado, strings tornam o fluxo explícito.

import sys
import pygame
import config
from player  import Player
from sprites import Plataforma, Moeda, Inimigo
from camera  import Camera


# ═════════════════════════════════════════════════════════════════════
class Game:
# ═════════════════════════════════════════════════════════════════════

    # ------------------------------------------------------------------
    # INICIALIZAÇÃO
    # ------------------------------------------------------------------
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode(
            (config.SCREEN_WIDTH, config.SCREEN_HEIGHT)
        )
        pygame.display.set_caption(config.TITLE)
        self.clock   = pygame.time.Clock()
        self.running = True

        # --- Máquina de Estados ---------------------------------------
        self.estado     = "MENU"   # estado inicial
        self.high_score = 0        # persiste entre partidas na mesma sessão

        # --- Fontes (criadas uma vez, reutilizadas em todo frame) -----
        self.fonte_titulo   = pygame.font.SysFont(None, 90)
        self.fonte_subtitulo = pygame.font.SysFont(None, 42)
        self.fonte_hud      = pygame.font.SysFont(None, 30)
        self.fonte_score    = pygame.font.SysFont(None, 36)

        # --- Overlay semi-transparente para Game Over / Vitória -------
        # Surface do tamanho da tela com suporte a alfa por pixel.
        # Preenchida com preto a 170/255 (~66% opaco) — deixa o cenário
        # visível ao fundo, dando contexto sem distrair do texto.
        self._overlay = pygame.Surface(
            (config.SCREEN_WIDTH, config.SCREEN_HEIGHT), pygame.SRCALPHA
        )
        self._overlay.fill((0, 0, 0, 170))

        # --- Construção do nível --------------------------------------
        self._construir_nivel()

    # ------------------------------------------------------------------
    def _construir_nivel(self):
        """
        Cria (ou recria) todos os objetos do nível: câmera, plataformas,
        jogador, moedas e inimigos.

        Separado do __init__ para podermos chamar em 'resetar_jogo()'
        sem recriar a janela — evita o flash visual de reinicializar
        o display do Pygame.
        """
        self.camera = Camera()
        self.score  = 0

        # ── Plataformas ───────────────────────────────────────────────
        self.plataformas = pygame.sprite.Group()
        for x, y, w, h in [
            (    0,  540,  3000,  20),  # chão contínuo
            (  100,  400,   180,  18),  # início
            (  380,  320,   150,  18),
            (  600,  430,   120,  18),
            (  800,  350,   200,  18),  # longa — inimigos aqui
            ( 1080,  260,   140,  18),
            ( 1300,  380,   160,  18),
            ( 1500,  300,   100,  18),  # pequena, desafiadora
            ( 1680,  430,   180,  18),
            ( 1950,  250,   200,  18),  # alta — inimigos aqui
            ( 2200,  370,   150,  18),
            ( 2420,  280,   120,  18),
            ( 2600,  400,   180,  18),  # planície — inimigos aqui
            ( 2820,  320,   160,  18),
            ( 2900,  420,    80,  18),  # chegada
        ]:
            self.plataformas.add(Plataforma(x, y, w, h))

        # ── Jogador ───────────────────────────────────────────────────
        self._spawn_x = float(config.SCREEN_WIDTH // 2 - 20)
        self._spawn_y = 100.0
        self.player   = Player(self._spawn_x, self._spawn_y)

        # ── Moedas ────────────────────────────────────────────────────
        self.moedas = pygame.sprite.Group()
        for cx, cy in [
            ( 150, 370), ( 200, 370), ( 250, 370),
            ( 430, 290), ( 460, 290),
            ( 640, 400),
            ( 850, 320), ( 900, 320), ( 950, 320),
            (1110, 230), (1150, 230),
            (1360, 350),
            (1520, 270), (1540, 270), (1560, 270),
            (1740, 400), (1790, 400),
            (2010, 220), (2050, 220), (2090, 220), (2130, 220),
            (2260, 340), (2300, 340),
            (2460, 250), (2500, 250),
            (2650, 370), (2700, 370), (2730, 370),
            (2860, 290),
            (2910, 390), (2930, 390), (2950, 390),
        ]:
            self.moedas.add(Moeda(cx, cy))

        # Guarda o total para a barra de progresso no HUD
        self._total_moedas = len(self.moedas)

        # ── Inimigos ──────────────────────────────────────────────────
        self.inimigos = pygame.sprite.Group()
        for x, y, xmin, xmax, vel in [
            (  810, 310,   800, 1000, 110),
            (  860, 310,   800, 1000, 150),
            ( 1960, 210,  1950, 2150, 130),
            ( 2050, 210,  1950, 2150,  90),
            ( 2610, 360,  2600, 2780, 120),
            ( 1090, 220,  1080, 1220, 100),
            ( 1690, 390,  1680, 1860, 140),
        ]:
            self.inimigos.add(Inimigo(x, y, xmin, xmax, vel))

    # ------------------------------------------------------------------
    def _resetar_jogo(self):
        """
        Reconstrói o nível e volta ao estado JOGANDO.
        Preserva self.high_score — ele sobrevive entre partidas.
        """
        self._construir_nivel()
        self.estado = "JOGANDO"

    # ══════════════════════════════════════════════════════════════════
    # COLISÕES (helpers chamados apenas quando estado == "JOGANDO")
    # ══════════════════════════════════════════════════════════════════

    def _checar_colisao_inimigos(self):
        """
        Pisão (stomp) → mata o inimigo, +50, mini-impulso.
        Toque lateral/inferior → Game Over.
        """
        colididos = pygame.sprite.spritecollide(
            self.player, self.inimigos, dokill=False
        )
        if not colididos:
            return

        p = self.player
        pisou_algum = False

        for inimigo in colididos:
            if p.vel_y > 0 and p.rect.bottom <= inimigo.rect.centery:
                inimigo.kill()
                self.score  += 50
                p.vel_y      = -350.0
                p.no_chao    = False
                pisou_algum  = True

        if not pisou_algum:
            self._ir_para_game_over()

    def _ir_para_game_over(self):
        """Registra high score e muda para o estado GAME_OVER."""
        if self.score > self.high_score:
            self.high_score = self.score
        self.estado = "GAME_OVER"

    # ══════════════════════════════════════════════════════════════════
    # 1. EVENTOS  — roteados pelo estado atual
    # ══════════════════════════════════════════════════════════════════

    def handle_events(self):
        for event in pygame.event.get():

            # ESC e fechar janela sempre funcionam
            if event.type == pygame.QUIT:
                self.running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.running = False

            # ── MENU ──────────────────────────────────────────────────
            if self.estado == "MENU":
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        self._resetar_jogo()   # constrói o nível e começa

            # ── JOGANDO ───────────────────────────────────────────────
            elif self.estado == "JOGANDO":
                self.player.handle_jump(event)

            # ── GAME_OVER ─────────────────────────────────────────────
            elif self.estado == "GAME_OVER":
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        self._resetar_jogo()
                    elif event.key == pygame.K_m:
                        self.estado = "MENU"

            # ── VITÓRIA ───────────────────────────────────────────────
            elif self.estado == "VITORIA":
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        self._resetar_jogo()
                    elif event.key == pygame.K_m:
                        self.estado = "MENU"

    # ══════════════════════════════════════════════════════════════════
    # 2. ATUALIZAÇÃO — só roda lógica quando estado == "JOGANDO"
    # ══════════════════════════════════════════════════════════════════

    def update(self, dt: float):
        # Mundo congelado em qualquer estado que não seja JOGANDO
        if self.estado != "JOGANDO":
            return

        self.player.update(dt, self.plataformas)
        self.inimigos.update(dt)

        # Moedas
        coletadas    = pygame.sprite.spritecollide(self.player, self.moedas, dokill=True)
        self.score  += len(coletadas) * 10

        # Inimigos — pisão ou Game Over
        self._checar_colisao_inimigos()

        # Vitória: todas as moedas coletadas
        if len(self.moedas) == 0:
            if self.score > self.high_score:
                self.high_score = self.score
            self.estado = "VITORIA"
            return   # câmera não precisa atualizar neste frame

        # Câmera — sempre depois do jogador
        self.camera.update(self.player.rect)

    # ══════════════════════════════════════════════════════════════════
    # 3. RENDERIZAÇÃO — cada estado tem sua rotina de draw
    # ══════════════════════════════════════════════════════════════════

    def draw(self):
        if self.estado == "MENU":
            self._draw_menu()
        elif self.estado == "JOGANDO":
            self._draw_jogo()
            self._draw_hud()
        elif self.estado == "GAME_OVER":
            self._draw_jogo()          # cenário ao fundo (congelado)
            self._draw_overlay()
            self._draw_game_over()
        elif self.estado == "VITORIA":
            self._draw_jogo()
            self._draw_overlay()
            self._draw_vitoria()

        pygame.display.flip()

    # ------------------------------------------------------------------
    # Rotinas de draw por tela
    # ------------------------------------------------------------------

    def _draw_menu(self):
        """Tela inicial: fundo escuro, título, subtítulo e high score."""
        SW, SH = config.SCREEN_WIDTH, config.SCREEN_HEIGHT
        self.screen.fill(config.BLACK)

        # Gradiente simples: faixa azul-marinho no topo
        faixa = pygame.Surface((SW, SH // 2))
        faixa.fill((15, 15, 45))
        self.screen.blit(faixa, (0, 0))

        # Título
        self._blit_centralizado(
            self.fonte_titulo, config.TITLE,
            config.YELLOW, SW // 2, SH // 2 - 100,
        )

        # Subtítulo
        self._blit_centralizado(
            self.fonte_subtitulo, "Pressione ESPAÇO para Iniciar",
            config.WHITE, SW // 2, SH // 2 + 10,
        )

        # Controles
        self._blit_centralizado(
            self.fonte_hud, "← → / A D   Mover      ESPAÇO / ↑ / W   Pular",
            (180, 180, 180), SW // 2, SH // 2 + 65,
        )

        # High score (só aparece se o jogador já jogou ao menos uma vez)
        if self.high_score > 0:
            self._blit_centralizado(
                self.fonte_subtitulo, f"High Score: {self.high_score}",
                config.GOLD, SW // 2, SH // 2 + 120,
            )

    def _draw_jogo(self):
        """Renderiza o cenário completo com offset da câmera."""
        self.screen.fill(config.SKY_BLUE)

        for plat in self.plataformas:
            self.screen.blit(plat.image, self.camera.aplicar(plat.rect))

        for moeda in self.moedas:
            self.screen.blit(moeda.image, self.camera.aplicar(moeda.rect))

        for inimigo in self.inimigos:
            self.screen.blit(inimigo.image, self.camera.aplicar(inimigo.rect))

        rect_tela = self.camera.aplicar(self.player.rect)
        self.player.draw(self.screen, rect_tela)

    def _draw_hud(self):
        """HUD em jogo: score (canto superior direito) + debug (canto esquerdo)."""
        SW = config.SCREEN_WIDTH

        # Score com sombra
        self._blit_com_sombra(
            self.fonte_score, f"Score: {self.score}",
            config.YELLOW, SW - 10, 10, ancora="topright",
        )

        # Barra de progresso de moedas
        moedas_restantes = len(self.moedas)
        coletadas        = self._total_moedas - moedas_restantes
        barra_w_total    = 160
        barra_h          = 10
        barra_x, barra_y = 10, 38

        pygame.draw.rect(self.screen, (80, 80, 80),
                         (barra_x, barra_y, barra_w_total, barra_h), border_radius=4)
        if self._total_moedas > 0:
            progresso = int(barra_w_total * coletadas / self._total_moedas)
            if progresso > 0:
                pygame.draw.rect(self.screen, config.YELLOW,
                                 (barra_x, barra_y, progresso, barra_h), border_radius=4)

        label = self.fonte_hud.render(
            f"Moedas: {coletadas}/{self._total_moedas}", True, config.WHITE
        )
        self.screen.blit(label, (barra_x, barra_y + 14))

        # Linha de debug (canto superior esquerdo)
        debug = self.fonte_hud.render(
            f"X: {int(self.player.x)}  "
            f"anim: {self.player.estado_animacao}[{self.player.frame_atual}]  "
            f"inimigos: {len(self.inimigos)}",
            True, config.BLACK,
        )
        self.screen.blit(debug, (10, 10))

    def _draw_overlay(self):
        """Overlay escuro semi-transparente sobre o cenário congelado."""
        self.screen.blit(self._overlay, (0, 0))

    def _draw_game_over(self):
        """Painel de Game Over centralizado sobre o overlay."""
        SW, SH = config.SCREEN_WIDTH, config.SCREEN_HEIGHT
        cy = SH // 2

        self._blit_centralizado(
            self.fonte_titulo, "GAME OVER",
            config.RED, SW // 2, cy - 110,
        )
        self._blit_centralizado(
            self.fonte_subtitulo, f"Score: {self.score}",
            config.WHITE, SW // 2, cy - 20,
        )
        if self.score >= self.high_score and self.score > 0:
            self._blit_centralizado(
                self.fonte_hud, "★  Novo High Score!  ★",
                config.GOLD, SW // 2, cy + 25,
            )
        self._blit_centralizado(
            self.fonte_subtitulo, f"High Score: {self.high_score}",
            config.GOLD, SW // 2, cy + 60,
        )
        self._blit_centralizado(
            self.fonte_hud, "[R] Tentar Novamente      [M] Menu Principal",
            (200, 200, 200), SW // 2, cy + 115,
        )

    def _draw_vitoria(self):
        """Painel de vitória centralizado sobre o overlay."""
        SW, SH = config.SCREEN_WIDTH, config.SCREEN_HEIGHT
        cy = SH // 2

        self._blit_centralizado(
            self.fonte_titulo, "VITÓRIA!",
            config.YELLOW, SW // 2, cy - 110,
        )
        self._blit_centralizado(
            self.fonte_subtitulo, "Todas as moedas coletadas!",
            config.WHITE, SW // 2, cy - 25,
        )
        self._blit_centralizado(
            self.fonte_subtitulo, f"Score Final: {self.score}",
            config.WHITE, SW // 2, cy + 20,
        )
        if self.score >= self.high_score:
            self._blit_centralizado(
                self.fonte_hud, "★  Novo High Score!  ★",
                config.GOLD, SW // 2, cy + 65,
            )
        self._blit_centralizado(
            self.fonte_hud, "[R] Jogar Novamente      [M] Menu Principal",
            (200, 200, 200), SW // 2, cy + 115,
        )

    # ------------------------------------------------------------------
    # Utilitários de renderização de texto
    # ------------------------------------------------------------------

    def _blit_centralizado(self, fonte, texto, cor, cx, cy, ancora="center"):
        """Renderiza texto centrado em (cx, cy) com sombra preta."""
        self._blit_com_sombra(fonte, texto, cor, cx, cy, ancora)

    def _blit_com_sombra(self, fonte, texto, cor, x, y, ancora="center"):
        """
        Renderiza texto com sombra 2px deslocada para legibilidade.

        ancora pode ser "center", "topright", "topleft" —
        passa direto para get_rect() como kwarg.
        """
        surf   = fonte.render(texto, True, cor)
        sombra = fonte.render(texto, True, config.BLACK)
        rect   = surf.get_rect(**{ancora: (x, y)})
        self.screen.blit(sombra, rect.move(2, 2))
        self.screen.blit(surf,   rect)

    # ══════════════════════════════════════════════════════════════════
    # GAME LOOP
    # ══════════════════════════════════════════════════════════════════

    def run(self):
        while self.running:
            dt = self.clock.tick(config.FPS) / 1000.0

            self.handle_events()
            self.update(dt)
            self.draw()

        pygame.quit()
        sys.exit()


# ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    Game().run()
