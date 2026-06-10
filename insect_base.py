"""
entities/insects/insect_base.py
════════════════════════════════
Contrato base para todos os insetos do jogo.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RESPONSABILIDADE ÚNICA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

InsectBase define o contrato mínimo que o Game (main.py) precisa:
  • group.update(dt)            — atualiza física + IA
  • spritecollide(player, ...)  — detectar captura
  • insect.ativo                — False após capturado/morto
  • insect.VALOR                — pontuação ao capturar
  • insect.ser_capturado()      — hook de captura

O Game também pode usar insect.hitbox diretamente para interação
com a língua (tongue.hitbox.colliderect(insect.rect)).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
POSICIONAMENTO NA HIERARQUIA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  InsectBase (pygame.Sprite)
    └── WanderingInsect      — andador errante (fase 1)
    └── FlyingInsect         ⟨futuro⟩ — voa em loop
    └── FleeingInsect        ⟨futuro⟩ — foge ao detectar o player
    └── RareInsect           ⟨futuro⟩ — grande valor, difícil captura

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CAMPOS RESERVADOS PARA FUTURAS EXTENSÕES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  self.stun_timer   : float — congela IA (preenchido pela língua)
  self.capturado    : bool  — True quando língua o recolhe
  self.VALOR        : int   — pontuação ao capturar

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DEPENDÊNCIAS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  pygame — Sprite, Rect, Surface, draw

NÃO importa: main, player, tongue, enemies, hud, tilemap_loader.
Zero risco de dependência circular.
"""

from __future__ import annotations

import pygame


class InsectBase(pygame.sprite.Sprite):
    """
    Classe base para todos os insetos — herda de pygame.Sprite para
    compatibilidade total com Group.update(), Group.draw() e spritecollide().

    Não instanciar diretamente. Use InsectFactory.create_insect() ou
    uma subclasse concreta.
    """

    # ── Gameplay defaults ─────────────────────────────────────────────
    # Subclasses sobrescrevem como atributos de classe.
    VALOR:    int = 10    # pontos ao capturar
    LARGURA:  int = 12   # px — hitbox
    ALTURA:   int = 8    # px — hitbox

    def __init__(self, x: int, y: int) -> None:
        """
        Parâmetros
        ──────────
        x, y : topleft em world-space (pixels), fornecido pelo loader.
        """
        super().__init__()

        # ── Posição float autoritativa ────────────────────────────────
        self.fx: float = float(x)
        self.fy: float = float(y)

        # ── Velocidade ────────────────────────────────────────────────
        self.vel_x: float = 0.0
        self.vel_y: float = 0.0

        # ── Estado de vida / captura ──────────────────────────────────
        # ativo = False → remove do grupo no próximo frame do Game.
        # capturado separado de ativo permite futura animação de captura
        # (ativo=False dispara remoção; capturado distingue o motivo).
        self.ativo:     bool = True
        self.capturado: bool = False

        # ── Stun — preenchido pela língua ─────────────────────────────
        # Enquanto stun_timer > 0, update() não executa IA.
        # Zero nesta etapa — preparado para implementação futura.
        self.stun_timer: float = 0.0

        # ── Sprite surface e rect de hitbox ──────────────────────────
        # Subclasses DEVEM sobrescrever self.image em seu __init__.
        self.image: pygame.Surface = self._surface_fallback()
        self.rect:  pygame.Rect   = self.image.get_rect(topleft=(x, y))

    # ------------------------------------------------------------------
    # INTERFACE OBRIGATÓRIA
    # ------------------------------------------------------------------

    def update(self, dt: float, *args, **kwargs) -> None:
        """
        Subclasses DEVEM implementar.
        Template recomendado:
            1. _processar_stun(dt)
            2. if stun_timer > 0: return
            3. _executar_ia(dt)
            4. _sincronizar_rect()
            5. _atualizar_imagem(dt)
        """
        raise NotImplementedError(
            f"{type(self).__name__} deve implementar update(dt)."
        )

    # ------------------------------------------------------------------
    # HOOK DE CAPTURA — chamado pelo Game ao detectar colisão com língua
    # ------------------------------------------------------------------

    def ser_capturado(self) -> None:
        """
        Marca o inseto como capturado e inativo.

        Chamado pelo Game quando tongue.hitbox colide com self.rect.
        O Game remove o sprite do grupo após checar self.ativo == False.

        ⟨futuro⟩: subclasses sobrescrevem para disparar:
          • animação de captura
          • SFX específico
          • drop de item
          • contribuição para combinação de sabor
        """
        if not self.ativo:
            return
        self.capturado = True
        self.ativo     = False
        self.kill()   # remove de todos os grupos imediatamente

    # ------------------------------------------------------------------
    # HELPERS DISPONÍVEIS PARA SUBCLASSES
    # ------------------------------------------------------------------

    def _processar_stun(self, dt: float) -> None:
        """Decrementa stun_timer — chamar no início de update()."""
        if self.stun_timer > 0.0:
            self.stun_timer = max(0.0, self.stun_timer - dt)

    def _sincronizar_rect(self) -> None:
        """Aplica fx/fy → rect sem drift de arredondamento."""
        self.rect.x = int(self.fx)
        self.rect.y = int(self.fy)

    def _surface_fallback(self) -> pygame.Surface:
        """Surface de fallback magenta — sinaliza subclasse incompleta."""
        surf = pygame.Surface((self.LARGURA, self.ALTURA), pygame.SRCALPHA)
        surf.fill((255, 0, 255))
        return surf
