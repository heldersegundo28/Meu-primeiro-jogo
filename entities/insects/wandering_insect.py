"""
entities/insects/wandering_insect.py
═════════════════════════════════════
Inseto errante — primeiro inseto concreto do jogo.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COMPORTAMENTO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  • Anda em linha reta a velocidade baixa
  • Muda de direção aleatoriamente a cada WANDER_CHANGE_MIN~MAX segundos
  • Mantém-se dentro de uma área circular de raio `area` ao redor do
    ponto de spawn (origin_x, origin_y) — não vaga pela fase inteira
  • Se sair da área: inverte vel_x para voltar (sem teleporte)
  • Visual: elipse amarronzada + 2 antenas procedurais

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PARÂMETROS CONFIGURÁVEIS (TMX → factory → __init__)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  velocidade : px/s de movimento (default = 28.0)
  area       : raio máximo em px a partir do spawn (default = 120)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ANIMAÇÃO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Dois frames pré-gerados proceduralmente em __init__ (legs_up / legs_down)
alternados por timer — simula caminhada sem spritesheet externa.
A troca de frame espelha a surface horizontalmente quando vel_x < 0.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DEPENDÊNCIAS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  pygame, random, entities.insects.insect_base.InsectBase

NÃO importa: main, player, tongue, config, hud, enemies.
"""

from __future__ import annotations

import random
import pygame

from entities.insects.insect_base import InsectBase


class WanderingInsect(InsectBase):
    """
    Inseto errante com movimentação orgânica baseada em Delta Time.

    Física dt-based
    ────────────────
    fx acumula velocidade × dt — sem lag em framerates altos/baixos.
    Restrição de área por comparação de distância ao origin: se
    abs(fx - origin_x) > area, vel_x inverte. Simples e barato.

    Timing de mudança de direção
    ─────────────────────────────
    change_timer decrementa a cada frame. Ao zerar, escolhe nova vel_x
    aleatória dentro de [-velocidade, -velocidade/3] ∪ [+velocidade/3, +velocidade]
    — garante que o inseto nunca fique parado, mas varie o ritmo.

    Stun
    ─────
    Quando stun_timer > 0 (preenchido pela língua no futuro), o update()
    paralisa a IA mas mantém a surface atual — inseto "congelado".
    """

    # ── Dimensões visuais ─────────────────────────────────────────────
    LARGURA: int = 14
    ALTURA:  int = 9

    # ── Animação ──────────────────────────────────────────────────────
    _FRAME_INTERVAL:    float = 0.18   # s entre frames de animação
    _ANIM_FRAMES:       int   = 2      # legs_up, legs_down

    # ── IA: wander timing ─────────────────────────────────────────────
    _WANDER_CHANGE_MIN: float = 0.8    # s mínimo entre mudanças de dir.
    _WANDER_CHANGE_MAX: float = 2.4    # s máximo entre mudanças de dir.

    # ── Cores procedurais ─────────────────────────────────────────────
    _COR_CORPO:   tuple = (160, 100,  50)   # marrom-avermelhado
    _COR_CABECA:  tuple = (190, 120,  60)
    _COR_ANTENA:  tuple = ( 80,  50,  20)
    _COR_PATAS:   tuple = ( 90,  60,  25)

    # ── Pontuação ─────────────────────────────────────────────────────
    VALOR: int = 10

    def __init__(
        self,
        x:          int,
        y:          int,
        velocidade: float = 28.0,
        area:       int   = 120,
    ) -> None:
        """
        Parâmetros
        ──────────
        x, y        : topleft em world-space
        velocidade  : px/s — magnitude do movimento
        area        : raio em px ao redor do spawn (confina o inseto)
        """
        super().__init__(x, y)

        # ── Parâmetros de comportamento ───────────────────────────────
        self.velocidade: float = velocidade
        self.area:       int   = area

        # ── Ponto de origem (confinamento de área) ────────────────────
        # Mantido como float para comparação contínua; nunca muda.
        self.origin_x: float = float(x)
        self.origin_y: float = float(y)

        # ── IA: estado inicial ────────────────────────────────────────
        self.vel_x         = random.choice([-1, 1]) * velocidade
        self.change_timer  = random.uniform(
            self._WANDER_CHANGE_MIN, self._WANDER_CHANGE_MAX
        )

        # ── Animação ──────────────────────────────────────────────────
        self._frame_idx:   int   = 0
        self._frame_timer: float = 0.0

        # Dois frames pré-gerados (legs_up / legs_down)
        self._frames_dir: list[pygame.Surface] = self._gerar_frames()
        self._frames_esq: list[pygame.Surface] = [
            pygame.transform.flip(f, True, False) for f in self._frames_dir
        ]

        # Sobrescreve image/rect do fallback de InsectBase
        self.image = self._frames_dir[0]
        self.rect  = self.image.get_rect(topleft=(x, y))

    # ------------------------------------------------------------------
    # UPDATE — implementação obrigatória de InsectBase
    # ------------------------------------------------------------------

    def update(self, dt: float, *args, **kwargs) -> None:
        """
        Ordem:
          1. Stun (paralisa IA sem matar)
          2. Wander timer (decide nova direção)
          3. Confinamento de área (inverte se saiu)
          4. Integração de posição
          5. Sincronização rect
          6. Animação
        """
        if not self.ativo:
            return

        # 1. Stun
        self._processar_stun(dt)
        if self.stun_timer > 0.0:
            return

        # 2. Timer de mudança de direção
        self.change_timer -= dt
        if self.change_timer <= 0.0:
            self._escolher_nova_direcao()

        # 3. Confinamento: se ultrapassou a área, vira para dentro
        distancia = self.fx - self.origin_x
        if distancia > self.area:
            self.vel_x = -abs(self.vel_x)
        elif distancia < -self.area:
            self.vel_x = abs(self.vel_x)

        # 4. Integração
        self.fx += self.vel_x * dt

        # 5. Rect
        self._sincronizar_rect()

        # 6. Animação
        self._atualizar_animacao(dt)

    # ------------------------------------------------------------------
    # IA INTERNA
    # ------------------------------------------------------------------

    def _escolher_nova_direcao(self) -> None:
        """
        Escolhe nova velocidade com magnitude variável.

        Garante que vel_x nunca seja zero — o inseto sempre se move.
        Magnitude entre 30% e 100% da velocidade nominal para variar o ritmo.
        """
        fator    = random.uniform(0.3, 1.0)
        sinal    = random.choice([-1, 1])
        self.vel_x    = sinal * self.velocidade * fator
        self.change_timer = random.uniform(
            self._WANDER_CHANGE_MIN, self._WANDER_CHANGE_MAX
        )

    # ------------------------------------------------------------------
    # ANIMAÇÃO
    # ------------------------------------------------------------------

    def _atualizar_animacao(self, dt: float) -> None:
        """Avança frame de animação e espelha pela direção de vel_x."""
        self._frame_timer += dt
        if self._frame_timer >= self._FRAME_INTERVAL:
            self._frame_timer -= self._FRAME_INTERVAL
            self._frame_idx    = (self._frame_idx + 1) % self._ANIM_FRAMES

        frames = self._frames_dir if self.vel_x >= 0 else self._frames_esq
        self.image = frames[self._frame_idx % len(frames)]

    def _gerar_frames(self) -> list[pygame.Surface]:
        """
        Gera dois frames procedurais de caminhada.

        Frame 0 (legs_up):   patas dobradas para cima
        Frame 1 (legs_down): patas estendidas para baixo

        Anatomia: elipse de corpo + semicírculo de cabeça + 3 patas/lado + 2 antenas.
        """
        frames = []
        w, h = self.LARGURA, self.ALTURA

        for frame_i in range(self._ANIM_FRAMES):
            surf = pygame.Surface((w, h + 6), pygame.SRCALPHA)
            surf.fill((0, 0, 0, 0))

            # Corpo: elipse central
            corpo_rect = pygame.Rect(2, 3, w - 4, h - 4)
            pygame.draw.ellipse(surf, self._COR_CORPO, corpo_rect)

            # Cabeça: pequena elipse à direita
            cab_w, cab_h = 5, 4
            pygame.draw.ellipse(
                surf, self._COR_CABECA,
                pygame.Rect(w - cab_w, h // 2 - cab_h // 2, cab_w, cab_h),
            )

            # Antenas (2 linhas a partir da cabeça)
            ax = w - 3
            ay = h // 2 - 1
            pygame.draw.line(surf, self._COR_ANTENA, (ax, ay), (ax + 5, ay - 3), 1)
            pygame.draw.line(surf, self._COR_ANTENA, (ax, ay), (ax + 5, ay - 5), 1)

            # Patas: 3 pares (offsetY varia entre frames)
            pata_y_offset = -1 if frame_i == 0 else 1
            for px in (4, w // 2, w - 6):
                # Pata superior
                pygame.draw.line(
                    surf, self._COR_PATAS,
                    (px, h // 2),
                    (px - 3, h // 2 - 3 + pata_y_offset), 1,
                )
                # Pata inferior
                pygame.draw.line(
                    surf, self._COR_PATAS,
                    (px, h // 2),
                    (px - 3, h // 2 + 3 - pata_y_offset), 1,
                )

            frames.append(surf)

        return frames
