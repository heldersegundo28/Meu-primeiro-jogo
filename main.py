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
        pygame.mixer.init()   # inicializa subsistema de áudio separadamente
        self.screen = pygame.display.set_mode(
            (config.SCREEN_WIDTH, config.SCREEN_HEIGHT)
        )
        pygame.display.set_caption(config.TITLE)
        self.clock   = pygame.time.Clock()
        self.running = True

        # --- Áudio ----------------------------------------------------
        self._inicializar_sons()
        self._musica_atual: str = ""   # rastreia o arquivo em reprodução

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

        # Música do menu toca ao abrir o jogo
        self._tocar_musica(config.MUSICA_MENU, volume=0.40)

    # ══════════════════════════════════════════════════════════════════
    # ÁUDIO
    # ══════════════════════════════════════════════════════════════════

    def _inicializar_sons(self):
        """
        Carrega efeitos sonoros e guarda em self.sons.

        Estrutura de self.sons
        ───────────────────────
        Dicionário  chave → pygame.mixer.Sound | None
        Valor None significa "arquivo não encontrado" — _tocar_som()
        checa isso e simplesmente não faz nada, mantendo o jogo silencioso
        sem lançar exceções.

        Nomenclatura de arquivos
        ─────────────────────────
        Coloque os arquivos na pasta 'audio/' ao lado dos .py:
            audio/sfx_pulo.wav
            audio/sfx_moeda.wav
            audio/sfx_morte.wav
        Formatos suportados pelo pygame.mixer: WAV, OGG, MP3 (plataforma-dependente).
        OGG é o mais portátil e livre de royalties — recomendado.

        Por que try/except por arquivo, não um único bloco?
        ─────────────────────────────────────────────────────
        Um único try/except pararia de carregar no primeiro arquivo
        ausente. Capturando individualmente, cada som faz seu próprio
        fallback — os demais continuam carregando normalmente.
        """
        def _carregar(caminho: str, volume: float) -> "pygame.mixer.Sound | None":
            try:
                som = pygame.mixer.Sound(caminho)
                som.set_volume(volume)
                return som
            except (FileNotFoundError, pygame.error) as e:
                print(f"[ÁUDIO] Som não encontrado: '{caminho}' ({e})")
                return None

        self.sons: dict = {
            # Chave          Arquivo                  Volume
            "pulo":    _carregar(config.SFX_PULO,    0.35),
            "moeda":   _carregar(config.SFX_MOEDA,   0.45),
            "morte":   _carregar(config.SFX_MORTE,   0.55),
            "stomp":   _carregar(config.SFX_STOMP,   0.50),
            "vitoria": _carregar(config.SFX_VITORIA, 0.60),
        }

    def _tocar_som(self, chave: str):
        """
        Dispara um efeito sonoro pelo nome da chave.
        Não faz nada (silenciosamente) se o som não foi carregado.

        Uso:  self._tocar_som("moeda")
        """
        som = self.sons.get(chave)
        if som is not None:
            som.play()

    def _tocar_musica(self, arquivo: str, volume: float = 0.40):
        """
        Toca um arquivo de música em loop infinito.

        Evita reiniciar a faixa se ela já estiver tocando — útil quando
        _resetar_jogo() é chamado enquanto a música de fase já está ativa.

        pygame.mixer.music é um canal dedicado, separado dos canais de
        efeitos (mixer.Sound). Isso permite ajuste de volume independente
        e troca de faixa sem interromper os SFX em reprodução.
        """
        if arquivo == self._musica_atual and pygame.mixer.music.get_busy():
            return   # já tocando — não reinicia

        try:
            pygame.mixer.music.load(arquivo)
            pygame.mixer.music.set_volume(volume)
            pygame.mixer.music.play(-1)   # -1 = loop infinito
            self._musica_atual = arquivo
        except (FileNotFoundError, pygame.error) as e:
            print(f"[ÁUDIO] Música não encontrada: '{arquivo}' ({e})")
            self._musica_atual = ""

    def _parar_musica(self):
        """Para a música de fundo imediatamente e limpa o rastreador."""
        pygame.mixer.music.stop()
        self._musica_atual = ""

    # ------------------------------------------------------------------
    def _construir_nivel(self, arquivo: str = config.FASE_1):
        """
        Inicializa os grupos e delega a construção ao carregador de fase.
        Separado do __init__ para permitir reset sem recriar a janela.
        """
        self.camera = Camera()
        self.score  = 0

        self.plataformas = pygame.sprite.Group()
        self.moedas      = pygame.sprite.Group()
        self.inimigos    = pygame.sprite.Group()

        # Spawn padrão — sobrescrito por 'P' no mapa
        self._spawn_x: float = float(config.TILE_SIZE)
        self._spawn_y: float = float(config.TILE_SIZE)

        self._carregar_fase(arquivo)

        # Player criado DEPOIS do carregamento para usar o spawn lido do mapa
        self.player = Player(self._spawn_x, self._spawn_y)

        # Total de moedas para a barra de progresso no HUD
        self._total_moedas = len(self.moedas)

    # ------------------------------------------------------------------
    def _carregar_fase(self, nome_arquivo: str):
        """
        Lê um arquivo de texto e popula os grupos de sprites.

        Formato do arquivo
        ──────────────────
        Cada caractere é um tile de config.TILE_SIZE × config.TILE_SIZE px.
        O índice de coluna 'col' e de linha 'lin' viram coordenadas de mundo:
            mundo_x = col * TILE_SIZE
            mundo_y = lin * TILE_SIZE

        Legenda de tiles
        ──────────────────
          '.'  espaço vazio (céu) — ignorado
          '#'  plataforma sólida
          'M'  moeda (centralizada no tile)
          'E'  inimigo patrulheiro
          'P'  spawn do jogador — não cria sprite, só guarda posição

        Patrulha dos inimigos
        ──────────────────────
        Para definir os limites de patrulha automaticamente, o método
        escaneia horizontalmente a partir da coluna do inimigo e procura
        até onde há plataforma sólida na linha imediatamente abaixo.
        Se não encontrar, usa ±3 tiles como fallback seguro.

        Erros de arquivo
        ──────────────────
        Se o arquivo não existir, imprime aviso e retorna sem travar o jogo.
        """
        T = config.TILE_SIZE

        try:
            with open(nome_arquivo, encoding="utf-8") as f:
                linhas = [linha.rstrip("\n") for linha in f.readlines()]
        except FileNotFoundError:
            print(f"[ERRO] Arquivo de fase não encontrado: '{nome_arquivo}'")
            return

        # Grid como lista de strings para consultar tiles vizinhos
        grid = linhas
        num_colunas = max(len(l) for l in grid) if grid else 0

        for lin, linha in enumerate(grid):
            for col, tile in enumerate(linha):

                mundo_x = col * T
                mundo_y = lin * T

                # ── Plataforma ────────────────────────────────────────
                if tile == "#":
                    self.plataformas.add(
                        Plataforma(mundo_x, mundo_y, T, T)
                    )

                # ── Moeda ─────────────────────────────────────────────
                elif tile == "M":
                    # Centraliza a moeda no tile
                    self.moedas.add(Moeda(mundo_x + T // 2, mundo_y + T // 2))

                # ── Inimigo ───────────────────────────────────────────
                elif tile == "E":
                    x_min, x_max = self._limites_patrulha(
                        grid, lin, col, num_colunas
                    )
                    self.inimigos.add(
                        Inimigo(mundo_x, mundo_y, x_min, x_max, velocidade=110.0)
                    )

                # ── Spawn do jogador ──────────────────────────────────
                elif tile == "P":
                    self._spawn_x = float(mundo_x)
                    self._spawn_y = float(mundo_y)

    # ------------------------------------------------------------------
    def _limites_patrulha(
        self,
        grid: list,
        lin_inimigo: int,
        col_inimigo: int,
        num_colunas: int,
    ) -> tuple:
        """
        Calcula x_min e x_max de patrulha para um inimigo.

        Varre para a esquerda e direita enquanto houver tile '#' na linha
        diretamente abaixo do inimigo (lin_inimigo + 1). Para no primeiro
        buraco ou na borda do mapa.

        Retorna (x_min, x_max) em pixels de mundo.
        """
        T        = config.TILE_SIZE
        lin_chao = lin_inimigo + 1

        def tem_chao(col: int) -> bool:
            if col < 0 or col >= num_colunas:
                return False
            if lin_chao >= len(grid):
                return False
            linha = grid[lin_chao]
            return col < len(linha) and linha[col] == "#"

        # Varre esquerda
        col_esq = col_inimigo
        while col_esq > 0 and tem_chao(col_esq - 1):
            col_esq -= 1

        # Varre direita
        col_dir = col_inimigo
        while col_dir < num_colunas - 1 and tem_chao(col_dir + 1):
            col_dir += 1

        # Fallback: sem chão detectado → ±3 tiles
        if col_esq == col_inimigo and col_dir == col_inimigo:
            col_esq = max(0,               col_inimigo - 3)
            col_dir = min(num_colunas - 1, col_inimigo + 3)

        return col_esq * T, (col_dir + 1) * T

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
                self._tocar_som("stomp")   # SFX: pisão confirmado

        if not pisou_algum:
            self._ir_para_game_over()

    def _ir_para_game_over(self):
        """Registra high score, dispara SFX de morte e muda para GAME_OVER."""
        if self.score > self.high_score:
            self.high_score = self.score
        self._parar_musica()
        self._tocar_som("morte")
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
                        self._resetar_jogo()
                        self._tocar_musica(config.MUSICA_FASE, volume=0.35)

            # ── JOGANDO ───────────────────────────────────────────────
            elif self.estado == "JOGANDO":
                self.player.handle_jump(event)

            # ── GAME_OVER ─────────────────────────────────────────────
            elif self.estado == "GAME_OVER":
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        self._resetar_jogo()
                        self._tocar_musica(config.MUSICA_FASE, volume=0.35)
                    elif event.key == pygame.K_m:
                        self._parar_musica()
                        self.estado = "MENU"
                        self._tocar_musica(config.MUSICA_MENU, volume=0.40)

            # ── VITÓRIA ───────────────────────────────────────────────
            elif self.estado == "VITORIA":
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        self._resetar_jogo()
                        self._tocar_musica(config.MUSICA_FASE, volume=0.35)
                    elif event.key == pygame.K_m:
                        self._parar_musica()
                        self.estado = "MENU"
                        self._tocar_musica(config.MUSICA_MENU, volume=0.40)

    # ══════════════════════════════════════════════════════════════════
    # 2. ATUALIZAÇÃO — só roda lógica quando estado == "JOGANDO"
    # ══════════════════════════════════════════════════════════════════

    def update(self, dt: float):
        # Mundo congelado em qualquer estado que não seja JOGANDO
        if self.estado != "JOGANDO":
            return

        self.player.update(dt, self.plataformas)
        self.inimigos.update(dt)

        # ── SFX: pulo ─────────────────────────────────────────────────
        # player.pulou é levantada em handle_jump e zerada aqui — garante
        # que o som dispara exatamente uma vez por pressionamento.
        if self.player.pulou:
            self._tocar_som("pulo")
            self.player.pulou = False

        # ── Moedas ────────────────────────────────────────────────────
        coletadas    = pygame.sprite.spritecollide(self.player, self.moedas, dokill=True)
        if coletadas:
            self._tocar_som("moeda")
            self.score += len(coletadas) * 10

        # Inimigos — pisão ou Game Over
        self._checar_colisao_inimigos()

        # ── Vitória: todas as moedas coletadas ─────────────────────────
        if len(self.moedas) == 0:
            if self.score > self.high_score:
                self.high_score = self.score
            self._parar_musica()
            self._tocar_som("vitoria")
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
