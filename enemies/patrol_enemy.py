"""
enemies/patrol_enemy.py
═══════════════════════
Inimigo patrulheiro horizontal — primeiro inimigo concreto do jogo.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COMPORTAMENTO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  • Anda horizontalmente entre x_min e x_max em velocidade constante
  • Inverte direção ao atingir cada limite (inversão idempotente via
    abs()/-abs() — não *= -1, que causaria flip duplo em lag spikes)
  • Animação de caminhada sincronizada com a direção de movimento
  • Tenta carregar spritesheet; usa fallback procedural se ausente

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RELAÇÃO COM sprites.Inimigo
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PatrolEnemy é a migração direta de sprites.Inimigo para a nova
arquitetura de inimigos. A lógica física e de animação é idêntica.
sprites.Inimigo permanece em sprites.py como alias de compatibilidade
para que código legado não quebre — mas main.py passa a usar
create_enemy() que retorna PatrolEnemy.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DEPENDÊNCIAS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  pygame, config, spritesheet.Spritesheet, enemies.enemy_base.EnemyBase

NÃO importa: main, player, hud, telemetry, tilemap_loader.
"""

from __future__ import annotations

import pygame
import config
from spritesheet        import Spritesheet
from enemies.enemy_base import EnemyBase


class PatrolEnemy(EnemyBase):
    """
    Patrulheiro horizontal com animação de caminhada por spritesheet.

    Física — dt-physics e inversão idempotente
    ────────────────────────────────────────────
    Posição acumulada em self.fx (float herdado de EnemyBase)
    → rect.x via _sincronizar_rect(). Inversão com abs()/-abs()
    em vez de *= -1: se dois frames de inversão ocorrerem no mesmo
    update() (lag spike), o sinal final é determinístico.

    Animação de caminhada — timer próprio
    ──────────────────────────────────────
    Timer interno _tempo_anim acumulado em update() — não depende
    do clock do Game. Ao atingir _INTERVALO_ANIM, avança _frame_anim
    e atribui a self.image. Frames pré-calculados no __init__
    (direita e esquerda espelhada) — zero transform.flip() no loop quente.

    Stun
    ─────
    Quando stun_timer > 0 (herdado de EnemyBase), update() congela
    o movimento mas mantém a animação pausada no frame atual.
    Ativar: enemy.stun_timer = 0.5  # segundos
    """

    # ── Dimensões da hitbox (pixels) ────────────────────────────────
    WIDTH:  int = 30
    HEIGHT: int = 40

    # ── Animação ────────────────────────────────────────────────────
    _LINHA_CAMINHADA: int   = 0
    _TOTAL_FRAMES:    int   = 4
    _INTERVALO_ANIM:  float = config.VELOCIDADE_ANIMACAO

    def __init__(
        self,
        x:          int,
        y:          int,
        x_min:      int,
        x_max:      int,
        velocidade: float = 110.0,
        dano:       int   = 1,
    ) -> None:
        """
        Parâmetros
        ──────────
        x, y        : topleft em world-space (pixels)
        x_min       : limite esquerdo da patrulha (rect.left mínimo)
        x_max       : limite direito  da patrulha (rect.right máximo)
        velocidade  : px/s; positivo = começa indo para a direita
        dano        : dano ao player por frame de contato
        """
        # EnemyBase inicializa fx, fy, vel_x, vel_y, dano, hp, image fallback
        super().__init__(x, y, dano=dano)

        # ── Parâmetros de patrulha ────────────────────────────────────
        self.velocidade: float = velocidade   # alias semântico de vel_x
        self.x_min:      int   = x_min
        self.x_max:      int   = x_max

        # ── Animação ─────────────────────────────────────────────────
        self._frame_anim: int   = 0
        self._tempo_anim: float = 0.0

        # Frames pré-calculados — zero flip no loop quente
        self._frames_dir: list[pygame.Surface]
        self._frames_esq: list[pygame.Surface]
        self._frames_dir, self._frames_esq = self._carregar_frames()

        # Atribui image e rect reais (sobrescreve o fallback de EnemyBase)
        self.image = self._frame_corrente()
        self.rect  = self.image.get_rect(topleft=(x, y))

    # ------------------------------------------------------------------
    # CARREGAMENTO DE FRAMES
    # ------------------------------------------------------------------

    def _carregar_frames(
        self,
    ) -> tuple[list[pygame.Surface], list[pygame.Surface]]:
        """
        Carrega (frames_dir, frames_esq) da spritesheet ou usa fallback.

        Retorna uma tupla para que __init__ desempacote em uma linha
        sem efeitos colaterais no método.
        """
        escala = (self.WIDTH, self.HEIGHT)
        fw     = config.FRAME_WIDTH
        fh     = config.FRAME_HEIGHT

        try:
            sheet = Spritesheet(config.SPRITE_INIMIGO)
            if not sheet.carregada:
                raise pygame.error("Spritesheet usou fallback")

            frames_dir = sheet.get_sequencia(
                self._LINHA_CAMINHADA, self._TOTAL_FRAMES,
                fw, fh, escala=escala,
            )
            frames_esq = sheet.get_sequencia(
                self._LINHA_CAMINHADA, self._TOTAL_FRAMES,
                fw, fh, escala=escala, espelhar_x=True,
            )
            return frames_dir, frames_esq

        except (FileNotFoundError, pygame.error):
            return self._gerar_frames_procedurais()

    def _gerar_frames_procedurais(
        self,
    ) -> tuple[list[pygame.Surface], list[pygame.Surface]]:
        """
        Frames procedurais de fallback — ciclo de caminhada de 4 frames.

        Cada frame varia a posição das pernas:
          0 → perna esq. baixa,  perna dir. alta
          1 → posição neutra
          2 → perna esq. alta,   perna dir. baixa
          3 → posição neutra
        """
        w, h = self.WIDTH, self.HEIGHT
        _OFFSETS: list[tuple[int, int]] = [(6, -6), (0, 0), (-6, 6), (0, 0)]
        frames_dir: list[pygame.Surface] = []

        for oe, od in _OFFSETS:
            surf = pygame.Surface((w, h), pygame.SRCALPHA)
            surf.fill(config.PURPLE)
            pygame.draw.line(surf, (200, 60, 240), (2, 0), (w - 3, 0), 2)
            pygame.draw.rect(surf, config.DARK_RED, ( 5, 8, 7, 7))
            pygame.draw.rect(surf, config.DARK_RED, (18, 8, 7, 7))
            pygame.draw.rect(surf, config.WHITE,    ( 9, 9, 2, 2))
            pygame.draw.rect(surf, config.WHITE,    (22, 9, 2, 2))
            pygame.draw.line(surf, config.DARK_RED, (7, 26), (23, 26), 2)
            cx   = w // 2
            base = h - 2
            plen = 8
            pygame.draw.line(surf, config.BLACK,
                             (cx - 6, base), (cx - 6, base + plen + oe), 3)
            pygame.draw.line(surf, config.BLACK,
                             (cx + 6, base), (cx + 6, base + plen + od), 3)
            frames_dir.append(surf)

        frames_esq = [
            pygame.transform.flip(f, True, False) for f in frames_dir
        ]
        return frames_dir, frames_esq

    # ------------------------------------------------------------------
    # ANIMAÇÃO
    # ------------------------------------------------------------------

    def _frame_corrente(self) -> pygame.Surface:
        """Retorna o frame atual baseado na direção e no índice."""
        frames = self._frames_dir if self.velocidade >= 0 else self._frames_esq
        return frames[self._frame_anim]

    def _atualizar_animacao(self, dt: float) -> None:
        """
        Avança o cronômetro e troca frame quando necessário.

        Usa -= em vez de = 0 para preservar o "troco" de tempo —
        ritmo constante mesmo sob variação de FPS.
        """
        self._tempo_anim += dt
        while self._tempo_anim >= self._INTERVALO_ANIM:
            self._tempo_anim -= self._INTERVALO_ANIM
            self._frame_anim  = (self._frame_anim + 1) % self._TOTAL_FRAMES
        self.image = self._frame_corrente()

    # ------------------------------------------------------------------
    # UPDATE — implementação obrigatória de EnemyBase
    # ------------------------------------------------------------------

    def update(self, dt: float, *args, **kwargs) -> None:
        """
        Física de patrulha + stun + animação.

        Ordem de operações
        ───────────────────
        1. Guarda early-return se morto
        2. Decrementa stun_timer (herdado de EnemyBase)
        3. Se stunado: mantém posição, não anima
        4. Integração:  fx += velocidade × dt
        5. Sincroniza:  rect.x ← int(fx)
        6. Limite esq.: corrige + inverte para direita
        7. Limite dir.: corrige + inverte para esquerda
        8. Animação:    avança cronômetro → troca self.image

        Animação por último porque depende do sinal final de
        self.velocidade — que pode ter sido invertido nos passos 6/7.
        """
        if not self.vivo:
            return

        # Passo 2: stun
        self._processar_stun(dt)
        if self.stun_timer > 0:
            return   # parado mas vivo — sem animação, sem movimento

        # Passo 4: integração
        self.fx += self.velocidade * dt

        # Passo 5: sincronização
        self._sincronizar_rect()

        # Passo 6: limite esquerdo
        if self.rect.left <= self.x_min:
            self.rect.left  = self.x_min
            self.fx         = float(self.rect.x)
            self.velocidade = abs(self.velocidade)   # força direita

        # Passo 7: limite direito
        elif self.rect.right >= self.x_max:
            self.rect.right = self.x_max
            self.fx         = float(self.rect.x)
            self.velocidade = -abs(self.velocidade)  # força esquerda

        # Passo 8: animação
        self._atualizar_animacao(dt)
