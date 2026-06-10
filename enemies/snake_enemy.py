"""
snake_enemy.py
════════════
Inimigo "cobra" simples — patrulha horizontal com aparência própria.

Comportamento
─────────────
  • patrulha entre x_min e x_max
  • inverte ao colidir com os limites
  • animação de corpo ondulado em 4 frames
  • usa fallback procedural em vez de spritesheet
"""

from __future__ import annotations

import pygame
import config
from enemies.enemy_base import EnemyBase


class SnakeEnemy(EnemyBase):
    """Inimigo cobra — patrulheiro horizontal com animação ondulada."""

    WIDTH:  int = 32
    HEIGHT: int = 18

    _TOTAL_FRAMES:   int   = 4
    _INTERVALO_ANIM: float = config.VELOCIDADE_ANIMACAO

    def __init__(
        self,
        x: int,
        y: int,
        x_min: int,
        x_max: int,
        velocidade: float = 120.0,
        dano: int = 1,
    ) -> None:
        super().__init__(x, y, dano=dano)

        self.velocidade: float = velocidade
        self.x_min: int = x_min
        self.x_max: int = x_max

        self._frame_anim: int = 0
        self._tempo_anim: float = 0.0

        self._frames_dir, self._frames_esq = self._gerar_frames_procedurais()
        self.image = self._frame_corrente()
        self.rect = self.image.get_rect(topleft=(x, y))

    def _frame_corrente(self) -> pygame.Surface:
        frames = self._frames_dir if self.velocidade >= 0 else self._frames_esq
        return frames[self._frame_anim]

    def _gerar_frames_procedurais(
        self,
    ) -> tuple[list[pygame.Surface], list[pygame.Surface]]:
        w, h = self.WIDTH, self.HEIGHT
        frames_dir: list[pygame.Surface] = []

        for fase in range(self._TOTAL_FRAMES):
            surf = pygame.Surface((w, h), pygame.SRCALPHA)
            surf.fill((0, 0, 0, 0))

            # Corpo e cabeça
            pygame.draw.rect(surf, config.GREEN, (0, 6, w, 8))
            pygame.draw.rect(surf, config.PURPLE, (0, 6, w, 8), 2)
            pygame.draw.circle(surf, config.GREEN, (w - 8, 10), 7)
            pygame.draw.circle(surf, config.PURPLE, (w - 8, 10), 5)

            # Marcações de corpo ondulado
            for i in range(0, w - 10, 8):
                offset = 1 if ((i // 8) + fase) % 2 == 0 else -1
                pygame.draw.ellipse(
                    surf,
                    config.PURPLE,
                    (i + 2, 7 + offset, 6, 4),
                )

            # Olhos
            olho_y = 6 if fase % 2 == 0 else 7
            pygame.draw.circle(surf, config.WHITE, (w - 11, olho_y), 2)
            pygame.draw.circle(surf, config.BLACK, (w - 11, olho_y), 1)

            frames_dir.append(surf)

        frames_esq = [pygame.transform.flip(frame, True, False) for frame in frames_dir]
        return frames_dir, frames_esq

    def _atualizar_animacao(self, dt: float) -> None:
        self._tempo_anim += dt
        while self._tempo_anim >= self._INTERVALO_ANIM:
            self._tempo_anim -= self._INTERVALO_ANIM
            self._frame_anim = (self._frame_anim + 1) % self._TOTAL_FRAMES
        self.image = self._frame_corrente()

    def update(self, dt: float, *args, **kwargs) -> None:
        if not self.vivo:
            return

        self._processar_stun(dt)
        if self.stun_timer > 0:
            return

        self.fx += self.velocidade * dt
        self._sincronizar_rect()

        if self.rect.left <= self.x_min:
            self.rect.left = self.x_min
            self.fx = float(self.rect.x)
            self.velocidade = abs(self.velocidade)

        elif self.rect.right >= self.x_max:
            self.rect.right = self.x_max
            self.fx = float(self.rect.x)
            self.velocidade = -abs(self.velocidade)

        self._atualizar_animacao(dt)
