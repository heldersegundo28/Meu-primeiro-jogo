"""
enemies/enemy_base.py
═════════════════════
Contrato base para todos os inimigos do jogo.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILOSOFIA DE DESIGN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EnemyBase define o CONTRATO mínimo que o Game (main.py) precisa para:
  1. Atualizar todos os inimigos:       group.update(dt)
  2. Detectar colisão com o player:     spritecollide(player, inimigos)
  3. Consultar propriedades de dano:    enemy.dano
  4. Remover um inimigo morto:          enemy.kill()

Nada mais é imposto. Cada subclasse tem liberdade total de implementar
movimento, animação, IA e comportamento de forma completamente diferente.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
POR QUE NÃO USAR ABC (Abstract Base Class)?
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

pygame.sprite.Sprite já usa __init_subclass__ e metaclasse própria.
Combinar com ABCMeta causaria conflito de metaclasse sem benefício real
— pygame já garante que .image e .rect sejam acessíveis para blit/collide.

Em vez de métodos abstratos formais, usamos NotImplementedError com
mensagens explicativas. O efeito prático é idêntico: instanciar EnemyBase
diretamente levanta erro; subclasses que esquecem de implementar também.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONTRATO PÚBLICO (o que main.py pode acessar em qualquer inimigo)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Herdado de pygame.sprite.Sprite:
  self.image  : pygame.Surface   — frame atual para blit
  self.rect   : pygame.Rect      — hitbox em world-space
  self.kill() : → None           — remove de todos os grupos

Definido aqui (EnemyBase):
  self.dano       : int          — dano causado ao player no contato
  self.vivo       : bool         — False após morrer (pré-animação de morte)
  self.vel_x      : float        — velocidade horizontal atual (px/s)
  self.vel_y      : float        — velocidade vertical atual (px/s)
  self.fx         : float        — posição X float autoritativa (anti-drift)
  self.fy         : float        — posição Y float autoritativa

Definido aqui como "deve implementar":
  update(dt)                     — física + animação do frame
  receber_dano(quantidade)       — reduz HP, dispara morte se necessário

Hooks opcionais (implementação default = no-op):
  ao_morrer()                    — efeito de morte, partículas, score
  ao_pisar()                     — reação ao stomp do player

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PREPARAÇÃO PARA SISTEMAS FUTUROS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Campos reservados (presentes mas não usados ainda):
  self.knockback_vel  : tuple[float,float]  — impulso de knockback pendente
  self.stun_timer     : float               — segundos de stun restantes
  self.hp             : int                 — pontos de vida (1 = morte imediata)
  self.hp_max         : int                 — HP máximo

Para ativar knockback no futuro:
    enemy.knockback_vel = (-200.0, -100.0)
    # update() aplica e zera em 1 frame

Para ativar stun:
    enemy.stun_timer = 0.5   # segundos
    # update() não executa lógica de IA enquanto stun_timer > 0

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DEPENDÊNCIAS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  pygame  — Sprite base class
  config  — constantes de cor para fallback visual

NÃO importa: main, player, sprites, hud, telemetry, tilemap_loader.
"""

from __future__ import annotations

import pygame
import config


class EnemyBase(pygame.sprite.Sprite):
    """
    Classe base para todos os inimigos.

    Herda de pygame.sprite.Sprite para compatibilidade total com
    pygame.sprite.Group, spritecollide() e draw().

    Não instanciar diretamente — use uma subclasse concreta
    ou crie via EnemyFactory.create_enemy().
    """

    # ── Constantes com valores default ───────────────────────────────
    # Subclasses podem sobrescrever como atributos de classe.
    DANO_CONTATO: int = 1    # dano padrão ao tocar o player
    HP_MAX:       int = 1    # vida padrão (1 = morre em 1 hit)

    def __init__(
        self,
        x:     int,
        y:     int,
        *,
        dano:  int   = DANO_CONTATO,
        hp:    int   = HP_MAX,
    ) -> None:
        """
        Inicializa posição, física base e campos de sistema futuros.

        Parâmetros
        ──────────
        x, y  : topleft em world-space (pixels)
        dano  : dano causado ao player por frame de contato
        hp    : pontos de vida iniciais
        """
        super().__init__()

        # ── Posição float autoritativa ────────────────────────────────
        # rect é derivado destes floats — sem drift de arredondamento.
        self.fx: float = float(x)
        self.fy: float = float(y)

        # ── Física ────────────────────────────────────────────────────
        self.vel_x: float = 0.0
        self.vel_y: float = 0.0

        # ── Status de combate ─────────────────────────────────────────
        self.dano:   int  = dano
        self.hp:     int  = hp
        self.hp_max: int  = hp
        self.vivo:   bool = True

        # ── Campos para sistemas futuros (reservados, não usados ainda)
        # Knockback: aplicado em update() e zerado no mesmo frame.
        self.knockback_vel: tuple[float, float] = (0.0, 0.0)
        # Stun: update() não processa IA enquanto stun_timer > 0.
        self.stun_timer:    float = 0.0

        # ── image e rect: subclasses DEVEM atribuir em seu __init__ ──
        # Fallback de segurança para que group.draw() não levante KeyError.
        self.image: pygame.Surface = self._surface_fallback()
        self.rect:  pygame.Rect    = self.image.get_rect(topleft=(x, y))

    # ------------------------------------------------------------------
    # INTERFACE OBRIGATÓRIA — subclasses devem implementar
    # ------------------------------------------------------------------

    def update(self, dt: float, *args, **kwargs) -> None:
        """
        Atualiza física e animação para este frame.

        Subclasses DEVEM sobrescrever este método.
        A assinatura *args, **kwargs garante compatibilidade com
        pygame.sprite.Group.update(dt) sem loop explícito.

        Template recomendado para subclasses:
        ────────────────────────────────────────
            def update(self, dt, *args, **kwargs):
                if not self.vivo:
                    return
                self._processar_stun(dt)     # respeita stun_timer
                if self.stun_timer > 0:
                    return
                self._executar_ia(dt)        # lógica específica
                self._sincronizar_rect()     # fx/fy → rect
                self._atualizar_animacao(dt) # troca self.image
        """
        raise NotImplementedError(
            f"{type(self).__name__} deve implementar update(dt). "
            "Veja o template na docstring de EnemyBase.update()."
        )

    # ------------------------------------------------------------------
    # INTERFACE RECOMENDADA — subclasses devem implementar
    # ------------------------------------------------------------------

    def receber_dano(self, quantidade: int = 1) -> None:
        """
        Reduz HP e dispara morte se necessário.

        Implementação default: morte imediata (HP_MAX=1).
        Subclasses com HP > 1 devem sobrescrever para feedback visual,
        i-frames, mudança de comportamento, etc.
        """
        if not self.vivo:
            return
        self.hp -= quantidade
        if self.hp <= 0:
            self._executar_morte()

    # ------------------------------------------------------------------
    # HOOKS OPCIONAIS — subclasses podem sobrescrever
    # ------------------------------------------------------------------

    def ao_morrer(self) -> None:
        """
        Hook chamado uma vez quando o inimigo morre.

        Uso futuro: emitir partículas, tocar SFX, dropar item,
        incrementar score externo, etc.

        Default: no-op — compatível com inimigos simples.
        """
        pass

    def ao_pisar(self) -> None:
        """
        Hook chamado quando o player executa stomp sobre este inimigo.

        Uso futuro: animação de achatamento, SFX específico,
        comportamento diferente de morte normal.

        Default: chama receber_dano(1) — stomp mata em 1 hit.
        """
        self.receber_dano(1)

    # ------------------------------------------------------------------
    # HELPERS INTERNOS — disponíveis para subclasses
    # ------------------------------------------------------------------

    def _executar_morte(self) -> None:
        """
        Marca como morto e chama hooks de morte.

        Subclasses com animação de morte devem sobrescrever:
          • setar self.vivo = False mas NÃO chamar kill()
          • chamar kill() ao fim da animação
        Subclasses sem animação de morte: comportamento default (kill imediato).
        """
        self.vivo = False
        self.ao_morrer()
        self.kill()

    def _processar_stun(self, dt: float) -> None:
        """
        Decrementa stun_timer. Subclasses chamam isto no início de update().

        Enquanto stun_timer > 0, a IA não deve executar — o inimigo
        fica parado ou com velocidade zerada (decisão da subclasse).
        """
        if self.stun_timer > 0:
            self.stun_timer = max(0.0, self.stun_timer - dt)

    def _sincronizar_rect(self) -> None:
        """
        Aplica fx/fy → rect.x/rect.y.

        Centraliza a conversão float→int para que subclasses não
        repitam a linha e possam mudar a estratégia de arredondamento
        em um único lugar.
        """
        self.rect.x = int(self.fx)
        self.rect.y = int(self.fy)

    def _surface_fallback(self) -> pygame.Surface:
        """
        Gera uma Surface mínima de fallback (magenta 16×16).

        Usada quando a subclasse não atribuiu self.image antes de
        chamar super().__init__(). Visível em tela — sinaliza que
        a subclasse está incompleta.
        """
        surf = pygame.Surface((16, 16), pygame.SRCALPHA)
        surf.fill((255, 0, 255))   # magenta = "falta implementação"
        return surf
