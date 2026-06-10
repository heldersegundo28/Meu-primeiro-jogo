"""
sprites.py
══════════
Sprites do cenário e NPCs — Plataforma, Moeda e Inimigo.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
O SISTEMA DE SPRITES DO PYGAME
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

pygame.sprite.Sprite conecta objetos ao sistema de gerenciamento em
lote do Pygame. Todo sprite deve expor dois atributos:

  self.image : pygame.Surface  — o que será desenhado
  self.rect  : pygame.Rect     — posição e hitbox em world-space
                                 (NUNCA modificado pela câmera)

O loop de draw em main.py itera sobre cada grupo e aplica
camera.aplicar(sprite.rect) para obter o Rect em screen-space
antes do blit — preservando as coordenadas de mundo intactas.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ESTRATÉGIA DE VISUAL — PIXEL ART COM FALLBACK PROCEDURAL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Cada classe tenta carregar sua imagem de config.SPRITE_*.
Se o arquivo não existir, cai para um visual procedural equivalente
ao da versão anterior — o jogo nunca trava por falta de arte.

  Plataforma  →  tileset.png  (escalado para largura × altura exatos)
  Moeda       →  moeda.png    (escalado para TAMANHO × TAMANHO)
  Inimigo     →  inimigo.png  (spritesheet com frames de caminhada)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TILING vs. SCALE EM PLATAFORMAS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Duas abordagens existem para cobrir uma plataforma longa (ex.: 3000px):

  A) transform.scale — estica o tile de 40×40 para 3000×40.
     Simples. Distorce a textura se as proporções mudarem.
     Adequado para tiles de pedra/terra com textura uniforme.

  B) Tiling — repete o tile original várias vezes lado a lado.
     Sem distorção. Custo: um blit por repetição no __init__.
     Adequado para tiles com padrão repetitivo visível.

Este módulo implementa AMBAS:
  _construir_image_scale()  → opção A (padrão quando tile é pequeno)
  _construir_image_tiling() → opção B (acionada quando tile cabe N×)

A escolha automática baseia-se no tamanho do tile carregado vs. a
largura da plataforma — veja Plataforma.__init__ para a lógica.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ANIMAÇÃO DO INIMIGO — TIMER PRÓPRIO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

O Inimigo gerencia seu próprio cronômetro de animação em vez de
delegar para o Game. Isso respeita o princípio de encapsulamento:
cada sprite é responsável pela sua própria apresentação visual.

A troca de frame ocorre em update(dt) — mesmo método que move o
personagem. Ao final, self.image é substituído pelo frame correto
(com flip se necessário), mantendo o contrato do sistema de sprites:
"blit self.image em self.rect".
"""

from __future__ import annotations

import warnings

import pygame

import config
from spritesheet import Spritesheet


# ══════════════════════════════════════════════════════════════════════
# PLATAFORMA
# ══════════════════════════════════════════════════════════════════════

class Plataforma(pygame.sprite.Sprite):
    """
    Bloco sólido e estático do cenário com textura de pixel art.

    Carregamento de textura
    ────────────────────────
    Tenta carregar config.SPRITE_CENARIO (sprites/tileset.png).
    Em caso de falha, usa o visual procedural de fallback (verde sólido
    com linha de borda) — comportamento idêntico à versão anterior.

    Cobertura de superfícies longas
    ─────────────────────────────────
    O tile carregado tem tamanho fixo (ex.: 40×40 px). Para cobrir uma
    plataforma de 3000×40, usamos uma das duas estratégias (ver docstring
    do módulo). A escolha é feita automaticamente em __init__.

    Extensão futura
    ────────────────
    Subclasses (PlataformaMovel, Armadilha) podem sobrescrever update(dt)
    sem mudar o contrato image/rect — a física e o draw de main.py
    permanecem inalterados.
    """

    # ── Fallback procedural (usado se o PNG não existir) ───────────────
    _COR_FALLBACK:  tuple = config.GREEN
    _COR_BORDA:     tuple = (30, 150, 50)

    # Proporção da plataforma acima da qual usamos tiling em vez de scale.
    # Se largura_plataforma / largura_tile >= _LIMITE_TILING → tiling.
    # Valor 2 significa: se a plataforma é ≥ 2× o tile, repetimos.
    _LIMITE_TILING: int   = 2

    def __init__(
        self,
        x:       int,
        y:       int,
        largura: int,
        altura:  int,
    ) -> None:
        """
        Parâmetros
        ──────────
        x, y         : topleft em world-space (pixels)
        largura, altura : dimensões do bloco (pixels)
        """
        super().__init__()

        self.image = self._construir_image(largura, altura)
        self.rect  = self.image.get_rect(topleft=(x, y))

    # ------------------------------------------------------------------
    def _construir_image(
        self, largura: int, altura: int
    ) -> pygame.Surface:
        """
        Retorna a Surface final da plataforma.

        Tenta carregar o tileset; em caso de erro usa fallback procedural.
        A lógica de escolha scale/tiling fica aqui, isolada do __init__.
        """
        try:
            tile = pygame.image.load(config.SPRITE_CENARIO).convert_alpha()
            return self._cobrir_com_tile(tile, largura, altura)

        except (FileNotFoundError, pygame.error) as exc:
            warnings.warn(
                f"[Plataforma] Tileset não encontrado: '{config.SPRITE_CENARIO}'"
                f" — {exc}. Usando fallback procedural.",
                UserWarning,
                stacklevel=3,
            )
            return self._fallback_procedural(largura, altura)

    def _cobrir_com_tile(
        self,
        tile:    pygame.Surface,
        largura: int,
        altura:  int,
    ) -> pygame.Surface:
        """
        Cobre a superfície da plataforma com o tile, escolhendo a
        estratégia ideal conforme as proporções.

        Estratégia A — scale
        ─────────────────────
        Usada quando o tile é quase do mesmo tamanho da plataforma
        (razão < _LIMITE_TILING). Estira o tile para preencher tudo.
        Simples e sem distorção perceptível em tiles uniformes.

        Estratégia B — tiling
        ──────────────────────
        Usada quando a plataforma é muito maior que o tile. Redimensiona
        o tile para a altura exata da plataforma e o repete lado a lado.
        Preserva o aspecto original do tile sem distorção horizontal.

        Comparação visual:
            Scale:   [████████████████████████████]  (tile esticado)
            Tiling:  [████][████][████][████][████]  (tile repetido)
        """
        tw = tile.get_width()

        # Redimensiona a altura do tile para bater com a plataforma
        # (independente da estratégia escolhida para o eixo X).
        tile_ajustado = pygame.transform.scale(tile, (tw, altura))

        if largura // tw < self._LIMITE_TILING:
            # ── Estratégia A: scale ────────────────────────────────────
            return pygame.transform.scale(tile_ajustado, (largura, altura))

        else:
            # ── Estratégia B: tiling ───────────────────────────────────
            # Cria uma surface opaca do tamanho total e repete o tile.
            # convert() (sem alpha) é mais rápido em blit para plataformas
            # que cobrem grandes áreas do cenário.
            surface = pygame.Surface((largura, altura))
            x = 0
            while x < largura:
                surface.blit(tile_ajustado, (x, 0))
                x += tw
            return surface

    def _fallback_procedural(self, largura: int, altura: int) -> pygame.Surface:
        """
        Visual procedural idêntico à versão pré-spritesheet:
        bloco verde com linha escura no topo.
        """
        surf = pygame.Surface((largura, altura))
        surf.fill(self._COR_FALLBACK)
        if altura >= 4:
            pygame.draw.line(surf, self._COR_BORDA, (0, 0), (largura - 1, 0), 2)
        return surf


# ══════════════════════════════════════════════════════════════════════
# MOEDA
# ══════════════════════════════════════════════════════════════════════

class Moeda(pygame.sprite.Sprite):
    """
    Coletável que concede pontos ao toque do jogador.

    Carregamento de imagem
    ────────────────────────
    Carrega config.SPRITE_MOEDA (sprites/moeda.png) e escala para
    TAMANHO × TAMANHO pixels. Se o arquivo não existir, usa o círculo
    procedural com canal alfa da versão anterior.

    Hitbox quadrada
    ─────────────────
    self.rect é o bounding box da imagem. Ligeiramente mais permissivo
    que o contorno exato, mas imperceptível em gameplay e mais eficiente
    do que colisão circular (collide_circle calcula distância euclidiana
    a cada frame por moeda).
    """

    TAMANHO: int = 24    # pixels; o PNG é escalado para este tamanho
    VALOR:   int = 10    # pontos concedidos ao coletar (lido por Game)

    def __init__(self, x: int, y: int) -> None:
        """
        Parâmetros
        ──────────
        x, y : centro da moeda em world-space.

        Usar o centro facilita o posicionamento:
            cx = tile_x + TILE_SIZE // 2
            cy = tile_y + TILE_SIZE // 2
        get_rect(center=...) ajusta o topleft automaticamente.
        """
        super().__init__()

        self.image = self._carregar_imagem()
        self.rect  = self.image.get_rect(center=(x, y))

    # ------------------------------------------------------------------
    def _carregar_imagem(self) -> pygame.Surface:
        """
        Tenta carregar o PNG; usa fallback procedural em caso de erro.

        convert_alpha() é obrigatório: a moeda tem áreas transparentes
        (fora do círculo/sprite). Sem ele o Pygame converte o formato a
        cada blit — 60× por segundo × 32 moedas = 1.920 conversões/s.
        """
        try:
            img = pygame.image.load(config.SPRITE_MOEDA).convert_alpha()
            return pygame.transform.scale(img, (self.TAMANHO, self.TAMANHO))

        except (FileNotFoundError, pygame.error) as exc:
            warnings.warn(
                f"[Moeda] Imagem não encontrada: '{config.SPRITE_MOEDA}'"
                f" — {exc}. Usando fallback procedural.",
                UserWarning,
                stacklevel=3,
            )
            return self._fallback_procedural()

    def _fallback_procedural(self) -> pygame.Surface:
        """
        Círculo amarelo com anel dourado e ponto de reflexo — idêntico
        ao visual da versão pré-spritesheet.
        """
        d = self.TAMANHO
        r = d // 2
        surf = pygame.Surface((d, d), pygame.SRCALPHA)
        pygame.draw.circle(surf, config.YELLOW,        (r, r), r)
        pygame.draw.circle(surf, config.GOLD,          (r, r), r, 2)
        pygame.draw.circle(surf, (255, 255, 200), (r - 3, r - 3), 2)
        return surf


# ══════════════════════════════════════════════════════════════════════
# INIMIGO
# ══════════════════════════════════════════════════════════════════════

class Inimigo(pygame.sprite.Sprite):
    """
    Patrulheiro horizontal com animação de caminhada por spritesheet.

    Física — dt-physics e inversão idempotente
    ────────────────────────────────────────────
    Posição acumulada em self.fx (float) → rect.x (int truncado).
    Inversão com abs()/-abs() em vez de *= -1 (idempotente — ver
    docstring do módulo de versão anterior para explicação completa).

    Animação de caminhada — timer próprio
    ──────────────────────────────────────
    O Inimigo mantém seu próprio cronômetro (_tempo_anim) em vez de
    depender do Game. A cada frame, update():
      1. Acumula dt em _tempo_anim.
      2. Quando _tempo_anim >= _INTERVALO_ANIM, avança _frame_anim.
      3. Seleciona o frame correto de _frames_dir ou _frames_esq
         conforme o sinal de self.velocidade.
      4. Atribui a self.image — mantendo o contrato do sistema de sprites.

    Flip direcional pré-calculado
    ──────────────────────────────
    Assim como em Player, os frames espelhados são calculados UMA vez
    no __init__ (não 60× por segundo). O draw() em main.py faz apenas
    um blit de self.image — zero transform.flip() no loop quente.

    Layout esperado de inimigo.png
    ────────────────────────────────
      ┌──────┬──────┬──────┬──────┐
      │ cam0 │ cam1 │ cam2 │ cam3 │  ← linha 0 (caminhada)
      └──────┴──────┴──────┴──────┘
      Cada célula: FRAME_WIDTH × FRAME_HEIGHT px (default 32×32)

    Compatibilidade com Group.update()
    ────────────────────────────────────
    Assinatura update(self, dt, *args, **kwargs) — aceita argumentos
    extras silenciosamente para que o Game possa chamar
    inimigos.update(dt) sem loop dedicado.
    """

    WIDTH:  int = 30
    HEIGHT: int = 40

    # Linha da spritesheet com a animação de caminhada
    _LINHA_CAMINHADA: int   = 0
    _TOTAL_FRAMES:    int   = 4
    # Segundos por frame de animação — valor maior = animação mais lenta
    _INTERVALO_ANIM:  float = config.VELOCIDADE_ANIMACAO

    def __init__(
        self,
        x:          int,
        y:          int,
        x_min:      int,
        x_max:      int,
        velocidade: float = 110.0,
    ) -> None:
        """
        Parâmetros
        ──────────
        x, y        : topleft em world-space (pixels)
        x_min       : limite esquerdo da patrulha — rect.left mínimo
        x_max       : limite direito  da patrulha — rect.right máximo
        velocidade  : px/s; positivo = começa indo para a direita
        """
        super().__init__()

        # ── Física ────────────────────────────────────────────────────
        # fx: float autoritativo da posição X — rect.x é derivado dele.
        self.fx:         float = float(x)
        self.velocidade: float = velocidade
        self.x_min:      int   = x_min
        self.x_max:      int   = x_max

        # ── Animação ──────────────────────────────────────────────────
        self._frame_anim: int   = 0
        self._tempo_anim: float = 0.0

        # Carrega os frames pré-calculados (com e sem flip)
        self._frames_dir: list[pygame.Surface]
        self._frames_esq: list[pygame.Surface]
        self._frames_dir, self._frames_esq = self._carregar_frames()

        # ── Image e Rect iniciais ─────────────────────────────────────
        # self.image começa com o primeiro frame da direção inicial.
        self.image = self._frame_corrente()
        self.rect  = self.image.get_rect(topleft=(x, y))

    # ------------------------------------------------------------------
    # CARREGAMENTO
    # ------------------------------------------------------------------

    def _carregar_frames(
        self,
    ) -> tuple[list[pygame.Surface], list[pygame.Surface]]:
        """
        Carrega e retorna (frames_dir, frames_esq).

        Tenta usar a spritesheet; usa fallback procedural em caso de erro.

        Por que retornar uma tupla em vez de atribuir diretamente?
        ─────────────────────────────────────────────────────────────
        Permite que __init__ desempacote em uma linha clara:
            self._frames_dir, self._frames_esq = self._carregar_frames()
        e deixa o método com responsabilidade única (carregar/retornar),
        sem efeitos colaterais em self.
        """
        escala = (self.WIDTH, self.HEIGHT)
        fw     = config.FRAME_WIDTH
        fh     = config.FRAME_HEIGHT

        try:
            sheet = Spritesheet(config.SPRITE_INIMIGO)

            if not sheet.carregada:
                # Spritesheet retornou fallback magenta — usa procedural
                raise pygame.error("Spritesheet usou fallback")

            frames_dir = sheet.get_sequencia(
                self._LINHA_CAMINHADA,
                self._TOTAL_FRAMES,
                fw, fh,
                escala=escala,
            )
            frames_esq = sheet.get_sequencia(
                self._LINHA_CAMINHADA,
                self._TOTAL_FRAMES,
                fw, fh,
                escala=escala,
                espelhar_x=True,
            )
            return frames_dir, frames_esq

        except (FileNotFoundError, pygame.error):
            # Spritesheet não disponível — gera frames procedurais
            return self._gerar_frames_procedurais()

    def _gerar_frames_procedurais(
        self,
    ) -> tuple[list[pygame.Surface], list[pygame.Surface]]:
        """
        Cria _TOTAL_FRAMES surfaces procedurais como fallback.

        Cada frame varia levemente a posição das pernas para simular
        o ciclo de caminhada sem nenhum arquivo externo.

        Visual por frame:
          0 → perna esq. baixa,  perna dir. alta
          1 → ambas na posição neutra
          2 → perna esq. alta,   perna dir. baixa
          3 → ambas na posição neutra

        As surfaces são produzidas para a direita (→) e depois
        espelhadas horizontalmente para a esquerda (←).
        """
        w, h     = self.WIDTH, self.HEIGHT
        # Offsets verticais por frame: (delta_esq, delta_dir)
        _OFFSETS: list[tuple[int, int]] = [(6, -6), (0, 0), (-6, 6), (0, 0)]

        frames_dir: list[pygame.Surface] = []

        for oe, od in _OFFSETS:
            surf = pygame.Surface((w, h), pygame.SRCALPHA)

            # Corpo roxo
            surf.fill(config.PURPLE)
            pygame.draw.line(surf, (200, 60, 240), (2, 0), (w - 3, 0), 2)

            # Olhos + brilho
            pygame.draw.rect(surf, config.DARK_RED, ( 5, 8, 7, 7))
            pygame.draw.rect(surf, config.DARK_RED, (18, 8, 7, 7))
            pygame.draw.rect(surf, config.WHITE,    ( 9, 9, 2, 2))
            pygame.draw.rect(surf, config.WHITE,    (22, 9, 2, 2))

            # Boca
            pygame.draw.line(surf, config.DARK_RED, (7, 26), (23, 26), 2)

            # Pernas animadas
            cx   = w // 2
            base = h - 2
            plen = 8
            pygame.draw.line(surf, config.BLACK,
                             (cx - 6, base), (cx - 6, base + plen + oe), 3)
            pygame.draw.line(surf, config.BLACK,
                             (cx + 6, base), (cx + 6, base + plen + od), 3)

            frames_dir.append(surf)

        # Espelha cada frame para gerar a sequência de esquerda
        frames_esq = [
            pygame.transform.flip(f, True, False) for f in frames_dir
        ]
        return frames_dir, frames_esq

    # ------------------------------------------------------------------
    # ANIMAÇÃO
    # ------------------------------------------------------------------

    def _frame_corrente(self) -> pygame.Surface:
        """
        Retorna o frame do estado atual (direção + índice).

        Encapsula a lógica de seleção em um único ponto — se a estrutura
        de armazenamento mudar, apenas este método precisa ser atualizado.
        """
        frames = self._frames_dir if self.velocidade >= 0 else self._frames_esq
        return frames[self._frame_anim]

    def _atualizar_animacao(self, dt: float) -> None:
        """
        Avança o cronômetro e troca o frame quando necessário.

        Usa -= em vez de = 0 para preservar o "troco" de tempo —
        mesmo princípio de player.py: ritmo constante sob variação de FPS.

        O while cobre lag spikes onde dois frames deveriam avançar
        no mesmo update.
        """
        self._tempo_anim += dt
        while self._tempo_anim >= self._INTERVALO_ANIM:
            self._tempo_anim  -= self._INTERVALO_ANIM
            self._frame_anim   = (self._frame_anim + 1) % self._TOTAL_FRAMES

        # Atualiza self.image com o frame correto após avanço ou
        # mudança de direção (velocidade pode ter invertido neste frame)
        self.image = self._frame_corrente()

    # ------------------------------------------------------------------
    # UPDATE — física + animação
    # ------------------------------------------------------------------

    def update(self, dt: float, *args, **kwargs) -> None:
        """
        Executa física de patrulha e animação para este frame.

        Ordem de operações
        ───────────────────
        1. Integração    fx += velocidade × dt      (Euler explícito)
        2. Sincronização rect.x ← int(fx)
        3. Limite esq.   corrige posição → inverte para direita
        4. Limite dir.   corrige posição → inverte para esquerda
        5. Animação      avança cronômetro → troca self.image

        A animação fica por último porque depende do sinal final de
        self.velocidade — que pode ter sido invertido nos passos 3/4.
        Se _atualizar_animacao fosse chamada antes, o frame exibido
        corresponderia à direção do frame ANTERIOR à inversão.

        Parâmetros
        ──────────
        dt             : delta time em segundos
        *args, **kwargs: ignorados — compatibilidade com Group.update()
        """
        # ── Passo 1-2: integração e sincronização ─────────────────────
        self.fx    += self.velocidade * dt
        self.rect.x = int(self.fx)

        # ── Passo 3: limite esquerdo ───────────────────────────────────
        if self.rect.left <= self.x_min:
            self.rect.left  = self.x_min
            self.fx         = float(self.rect.x)   # anti-drift
            self.velocidade = abs(self.velocidade)  # força direita (+)

        # ── Passo 4: limite direito ────────────────────────────────────
        elif self.rect.right >= self.x_max:
            self.rect.right = self.x_max
            self.fx         = float(self.rect.x)   # anti-drift
            self.velocidade = -abs(self.velocidade) # força esquerda (-)

        # ── Passo 5: animação ─────────────────────────────────────────
        self._atualizar_animacao(dt)


# ══════════════════════════════════════════════════════════════════════
# CHECKPOINT
# ══════════════════════════════════════════════════════════════════════

class Checkpoint(pygame.sprite.Sprite):
    """
    Marcador de ponto de retorno — posição de respawn alternativa ao spawn
    original da fase.

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    RESPONSABILIDADE
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    Este sprite SÓ conhece sua própria posição e estado visual.
    Quem decide ativar, salvar e usar o respawn é o Game (main.py).
    O Player nunca importa ou referencia Checkpoint.

    Dependências: apenas pygame. Nenhuma importação de config, player ou
    main — zero risco de dependência circular.

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    CONTRATO PÚBLICO
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

      self.rect  : pygame.Rect   — hitbox e posição em world-space
      self.image : pygame.Surface — frame atual (idle ou ativo)
      self.ativo : bool           — True após primeiro toque do jogador

    O Game usa self.rect para colisão e self.ativo para decidir se é o
    respawn mais recente. Não há mais estado público além desses três.

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    VISUAL PROCEDURAL (sem assets externos)
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    Dois estados visuais construídos proceduralmente em __init__:

      idle  — bandeira cinza-azulada: checkpoint existe mas não foi tocado
      ativo — bandeira amarela dourada: checkpoint ativado pelo jogador

    Construídos uma única vez em __init__ e armazenados como _img_idle
    e _img_ativo. A troca em ativar() é uma atribuição simples — sem
    Surface.fill() no loop quente, sem alocação por frame.

    Estrutura visual (16×32 px padrão):
        ┌──────────────────────┐
        │  poste vertical      │  linha cinza-escuro, 2px
        │  bandeira no topo    │  retângulo colorido 10×8 px
        │  base pequena        │  retângulo escuro 6×4 px
        └──────────────────────┘

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    PONTO DE SPAWN REAL (respawn_x / respawn_y)
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    O Player deve reaparacer COM OS PÉS NA BASE do checkpoint, não no
    topleft do rect. Por isso o Game lê (respawn_x, respawn_y) — que
    apontam para o centro-base do sprite — e não rect.topleft.

    O Player é instanciado com Player(x, y) onde (x,y) é o TOPLEFT do
    hitbox. Portanto:

        respawn_x = rect.centerx - Player.WIDTH // 2
        respawn_y = rect.bottom  - Player.HEIGHT

    Esses valores são calculados uma vez em __init__ e armazenados como
    atributos Read-Only. O Game nunca recalcula — apenas lê.
    """

    # ── Dimensões visuais ─────────────────────────────────────────────
    # Separadas da hitbox para facilitar ajuste de arte futura.
    # A hitbox (HITBOX_W × HITBOX_H) define a colisão; o visual pode ser
    # maior ou menor sem afetar o gameplay.
    HITBOX_W: int = 16    # largura da zona de ativação (pixels)
    HITBOX_H: int = 32    # altura da zona de ativação (pixels)

    # ── Cores procedurais (estado idle e ativo) ───────────────────────
    _COR_POSTE:        tuple = ( 80,  80,  90)   # cinza-escuro
    _COR_BASE:         tuple = ( 60,  60,  70)   # base do poste
    _COR_BANDEIRA_OFF:      tuple = (100, 120, 160)   # cinza-azulado (idle)
    _COR_BANDEIRA_ON:       tuple = (255, 200,  50)   # amarelo dourado: respawn atual
    _COR_BANDEIRA_ANTERIOR: tuple = ( 80, 160,  80)   # verde apagado: visitado, não atual

    def __init__(self, x: int, y: int) -> None:
        """
        Parâmetros
        ──────────
        x, y : topleft em coordenadas de mundo (pixels).
                O loader garante que esses valores já estão no espaço
                lógico do motor (col × TILE_SIZE, row × TILE_SIZE).
        """
        super().__init__()

        # ── Constrói as três surfaces uma única vez ──────────────────
        # idle     : bandeira cinza-azulada — ainda não tocado
        # ativo    : bandeira amarela dourada — respawn atual
        # anterior : bandeira verde apagada — visitado mas superado por novo checkpoint
        self._img_idle     = self._construir_surface(ativo=False)
        self._img_ativo    = self._construir_surface(ativo=True)
        self._img_anterior = self._construir_surface(ativo=False,
                                                     cor_override=self._COR_BANDEIRA_ANTERIOR)

        # ── Estado inicial: não ativado ───────────────────────────────
        self.ativo: bool = False
        self.image       = self._img_idle

        # ── Rect de hitbox em world-space ─────────────────────────────
        self.rect: pygame.Rect = pygame.Rect(x, y, self.HITBOX_W, self.HITBOX_H)

        # ── Posição de respawn: pés do Player na base do checkpoint ───
        # Importamos Player.WIDTH/HEIGHT via duck typing: como a classe
        # Player vive em player.py (que não é importado aqui para evitar
        # dependência circular), usamos valores físicos fixos.
        # Se o tamanho do Player mudar, estes offsets devem ser ajustados.
        # Alternativa futura: passar player_width/height como parâmetro.
        _PLAYER_W = 40   # Player.WIDTH  — mantido em sincronia manual
        _PLAYER_H = 60   # Player.HEIGHT — mantido em sincronia manual

        self.respawn_x: float = float(self.rect.centerx - _PLAYER_W // 2)
        self.respawn_y: float = float(self.rect.bottom  - _PLAYER_H)

    # ------------------------------------------------------------------
    # CONSTRUÇÃO VISUAL
    # ------------------------------------------------------------------

    def _construir_surface(
        self,
        ativo: bool,
        cor_override: tuple | None = None,
    ) -> pygame.Surface:
        """
        Gera a Surface do checkpoint proceduralmente.

        Retorna uma Surface SRCALPHA (transparente fora do sprite) com:
          - Poste vertical centralizado
          - Bandeira no topo (cor varia pelo parâmetro ativo)
          - Base no rodapé do poste

        Parâmetros
        ──────────
        ativo        : True = bandeira amarela (respawn atual)
        cor_override : se fornecida, usa esta cor em vez da padrão
                       (ex: verde apagado para estado 'anterior')

        Por que SRCALPHA?
        ─────────────────
        O checkpoint tem forma de bandeira — não é retangular. SRCALPHA
        permite que os cantos da bounding box fiquem transparentes,
        evitando o efeito de "caixa sólida" em fundos coloridos.
        """
        w, h   = self.HITBOX_W, self.HITBOX_H
        surf   = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 0))   # totalmente transparente

        if cor_override is not None:
            cor_bandeira = cor_override
        else:
            cor_bandeira = self._COR_BANDEIRA_ON if ativo else self._COR_BANDEIRA_OFF

        # ── Poste (linha vertical 2px, do topo ao fundo) ─────────────
        poste_x = w // 2 - 1   # centralizado
        pygame.draw.rect(surf, self._COR_POSTE, (poste_x, 0, 2, h - 4))

        # ── Bandeira (retângulo 10×8 px, partindo do topo do poste) ───
        # Posicionada à direita do poste para leitura clara.
        pygame.draw.rect(surf, cor_bandeira, (poste_x + 2, 2, 10, 8))

        # ── Base (bloco 6×4 px na base do poste) ─────────────────────
        pygame.draw.rect(surf, self._COR_BASE, (poste_x - 2, h - 4, 6, 4))

        return surf

    # ------------------------------------------------------------------
    # ATIVAÇÃO
    # ------------------------------------------------------------------

    def ativar(self) -> None:
        """
        Marca este checkpoint como ativo e atualiza o visual.

        Chamado SOMENTE pelo Game (main.py) ao detectar colisão com
        o Player. O Checkpoint nunca se autoativa.

        Idempotente: chamar ativar() num checkpoint já ativo não causa
        efeito colateral — a atribuição de image é inofensiva.
        """
        self.ativo = True
        self.image = self._img_ativo

    def marcar_como_anterior(self) -> None:
        """
        Rebaixa este checkpoint de 'respawn atual' para 'visitado mas superado'.

        Chamado pelo Game quando um checkpoint posterior é ativado.
        Mantém self.ativo = True (foi tocado) mas muda o visual para
        verde apagado — comunica ao jogador que não é mais o respawn ativo.

        Por que não desativar (ativo = False)?
        ─────────────────────────────────────────
        self.ativo = False reabriria o checkpoint para nova ativação,
        o que alteraria o respawn retroativamente. O estado 'anterior'
        é puramente visual — o checkpoint permanece tocado.
        """
        self.image = self._img_anterior


# ══════════════════════════════════════════════════════════════════════
# SAÍDA DE FASE
# ══════════════════════════════════════════════════════════════════════

class SaidaFase(pygame.sprite.Sprite):
    """
    Marcador visual da saída de fase — ponto de chegada que conclui o nível.

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    RESPONSABILIDADE ÚNICA
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    Este sprite SÓ sabe onde está e como se desenha.
    Quem detecta a colisão, decide avançar de fase e protege contra
    múltiplos disparos é exclusivamente o Game (main.py).
    O Player nunca importa nem referencia SaidaFase.

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    CONTRATO PÚBLICO
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

      self.rect  : pygame.Rect    — hitbox em world-space (colisão + draw)
      self.image : pygame.Surface — visual do portal/saída

    Não há estado mutável além dos herdados de Sprite. O Game controla
    tudo — este sprite apenas existe para ser colidido e renderizado.

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    VISUAL PROCEDURAL
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    Construído proceduralmente sem assets externos — o jogo não trava
    por arquivo ausente.

    Estrutura visual (LARGURA × ALTURA pixels):

        ┌─────────────────────────┐
        │  moldura externa        │  borda verde-escuro 3px
        │  ┌─────────────────┐   │
        │  │ fundo gradiente │   │  verde-escuro translúcido
        │  │                 │   │
        │  │   ► ► ►         │   │  setas verdes claras (→ direção saída)
        │  │                 │   │
        │  └─────────────────┘   │
        │  "SAÍDA" centralizado   │  texto branco pequeno
        └─────────────────────────┘

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    DIMENSÕES E HITBOX
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    LARGURA = 2 tiles   ALTURA = 3 tiles   (baseado em TILE_SIZE implícito)

    A hitbox coincide com o visual inteiro — intencionalmente permissiva.
    O jogador deve conseguir alcançar a saída sem precisão milimétrica.
    Para ajustar: alterar LARGURA e ALTURA sem mexer em mais nada.
    """

    # ── Dimensões da hitbox (e do visual) — em pixels ─────────────────
    # Expressas em múltiplos de tile (40 px) para alinhar ao grid do mapa.
    # 2 tiles largo × 3 tiles alto = 80 × 120 px.
    LARGURA: int = 80    # 2 × TILE_SIZE
    ALTURA:  int = 120   # 3 × TILE_SIZE

    # ── Cores procedurais ─────────────────────────────────────────────
    _COR_FUNDO:    tuple = ( 10,  60,  10, 180)   # verde-escuro translúcido (RGBA)
    _COR_MOLDURA:  tuple = ( 50, 200,  80)         # verde médio (RGB)
    _COR_SETA:     tuple = (150, 255, 150)         # verde claro (RGB)
    _COR_TEXTO:    tuple = (255, 255, 255)         # branco puro (RGB)

    def __init__(self, x: int, y: int) -> None:
        """
        Parâmetros
        ──────────
        x, y : topleft em coordenadas de mundo (pixels).
               Fornecidos pelo loader já convertidos para o espaço lógico
               do motor (col × TILE_SIZE, row × TILE_SIZE).
        """
        super().__init__()

        self.image = self._construir_surface()
        self.rect  = pygame.Rect(x, y, self.LARGURA, self.ALTURA)

    # ------------------------------------------------------------------
    # CONSTRUÇÃO VISUAL
    # ------------------------------------------------------------------

    def _construir_surface(self) -> pygame.Surface:
        """
        Gera a Surface do portal de saída proceduralmente.

        Pipeline
        ─────────
        1. Surface SRCALPHA (transparência total)
        2. Fundo verde-escuro translúcido (RGBA fill com subsurface)
        3. Moldura retangular (borda 3px)
        4. Três setas "►" distribuídas verticalmente
        5. Texto "SAÍDA" centralizado na base

        Por que SRCALPHA?
        ─────────────────
        Permite que o fundo do portal seja semi-transparente, deixando
        o cenário atrás visível — sinaliza "passagem" sem bloquear a view.

        Por que setas desenhadas com rects e não com font?
        ────────────────────────────────────────────────────
        pygame.font.SysFont() pode ter latência de I/O no __init__ se
        chamado repetidamente. As setas geométricas custam apenas
        pygame.draw.polygon() — zero I/O, zero dependência de sistema.
        O texto "SAÍDA" usa SysFont uma única vez e é aceitável.
        """
        w, h = self.LARGURA, self.ALTURA
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 0))   # limpa para transparente

        # ── Fundo semi-transparente ───────────────────────────────────
        fundo = pygame.Surface((w - 6, h - 6), pygame.SRCALPHA)
        fundo.fill(self._COR_FUNDO)
        surf.blit(fundo, (3, 3))

        # ── Moldura (borda 3px) ───────────────────────────────────────
        pygame.draw.rect(surf, self._COR_MOLDURA, (0, 0, w, h), 3)

        # ── Setas geométricas (triângulos apontando direita) ──────────
        # Três setas distribuídas em y: 25%, 50%, 75% da altura.
        # Cada seta: triângulo isósceles 16×12 px centralizado em x.
        cx    = w // 2          # centro horizontal
        sw    = 16              # largura da seta
        sh    = 12              # altura da seta
        for frac in (0.28, 0.50, 0.72):
            sy = int(h * frac)  # y do centro da seta
            pontos = [
                (cx + sw // 2, sy),            # ponta direita
                (cx - sw // 2, sy - sh // 2),  # canto superior esquerdo
                (cx - sw // 2, sy + sh // 2),  # canto inferior esquerdo
            ]
            pygame.draw.polygon(surf, self._COR_SETA, pontos)

        # ── Texto "SAÍDA" na base ─────────────────────────────────────
        # SysFont size 14: pequeno o suficiente para caber em 80px de largura.
        try:
            fonte = pygame.font.SysFont(None, 14)
            txt   = fonte.render("SAÍDA", True, self._COR_TEXTO)
            tx    = (w - txt.get_width())  // 2
            ty    = h - txt.get_height() - 5
            surf.blit(txt, (tx, ty))
        except Exception:
            pass   # font falhou → visual sem texto, jogo não trava

        return surf
