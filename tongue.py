"""
tongue.py
═════════
Sistema da Língua do Calango — módulo autônomo e desacoplado.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RESPONSABILIDADE ÚNICA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Este módulo gerencia o ciclo de vida completo da língua:
  • Máquina de estados (IDLE → EXTENDING → ACTIVE → RETRACTING → IDLE)
  • Física de extensão/retração baseada em Delta Time
  • Hitbox em world-space para futuras colisões
  • Renderização procedural em screen-space

O módulo NUNCA:
  • modifica vel_x/vel_y do Player
  • lê estado de câmera diretamente (recebe offsets como parâmetro)
  • decide o que acontece ao colidir (quem decide é o Game, via lingua.hitbox)
  • importa main, hud, telemetry, tilemap_loader, sprites

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MÁQUINA DE ESTADOS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  IDLE
    Língua recolhida. Aceita disparo via disparar().
    hitbox = None (sem colisão ativa).
    cooldown_timer decrementa aqui.

  EXTENDING
    Língua cresce em direção ao alvo a TONGUE_SPEED px/s.
    hitbox ativo (segmento crescente).
    Ao atingir TONGUE_RANGE → transita para ACTIVE.

  ACTIVE
    Língua estendida no comprimento máximo.
    hitbox ativo (posição fixa = ponta final).
    Dura TONGUE_ACTIVE_TIME segundos → transita para RETRACTING.
    ⟨futuro⟩: colisão com interagível aqui dispara captura.

  RETRACTING
    Língua retrai em direção à origem a TONGUE_SPEED px/s.
    hitbox ativo durante retração (permite capturar no retorno).
    Ao comprimento = 0 → transita para IDLE e inicia cooldown.

  Diagrama:

    IDLE ─── disparar() ──► EXTENDING
                                │ comprimento >= RANGE
                                ▼
                             ACTIVE
                                │ active_timer <= 0
                                ▼
                           RETRACTING
                                │ comprimento <= 0
                                ▼
                              IDLE ──► cooldown

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HITBOX
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

A hitbox é um pygame.Rect estreito em world-space que representa o
segmento atual da língua. O Game pode passar self.lingua.hitbox para
pygame.sprite.spritecollide() sem qualquer alteração neste módulo.

  hitbox = None   → língua inativa (IDLE após cooldown)
  hitbox = Rect   → língua estendendo/ativa/retraindo

Dimensões:
  Horizontal: largura = comprimento_atual, altura = TONGUE_HEIGHT
  A hitbox é atualizada a cada update() — sempre reflete o segmento real.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RENDERIZAÇÃO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

draw(surface, origem_screen, cam_offset_x, cam_offset_y, ox, oy)

  origem_screen : posição da boca do calango em screen-space
                  (calculada pelo Game com camera.aplicar + shake)
  cam_offset_x  : camera.offset_x (para converter ponta world → screen)
  cam_offset_y  : camera.offset_y
  ox, oy        : offset de shake

A língua é desenhada como duas linhas paralelas (espessura visual)
com círculo na ponta — procedural, sem assets.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DEPENDÊNCIAS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  pygame  — Rect, draw
  enum    — TongueState

NÃO importa: config, main, player, hud, sprites, enemies, tilemap_loader.
Todas as constantes são atributos de classe — sem dependência de config.py.
Isso permite usar Lingua em testes unitários sem inicializar pygame.display.
"""

from __future__ import annotations

import pygame
from enum import Enum, auto


# ══════════════════════════════════════════════════════════════════════
# ESTADO DA LÍNGUA
# ══════════════════════════════════════════════════════════════════════

class TongueState(Enum):
    """
    Estado da Máquina de Estados da Língua.

    Por que Enum e não constantes string/int?
    ──────────────────────────────────────────
    • Comparação com `is` — sem typo silencioso
    • repr() legível em debugging: <TongueState.EXTENDING>
    • O type-checker infere o tipo correto
    • Adicionar estado (ex: CONGELADA, CARREGANDO) = uma linha
    """
    IDLE       = auto()
    EXTENDING  = auto()
    ACTIVE     = auto()
    RETRACTING = auto()


# ══════════════════════════════════════════════════════════════════════
# LÍNGUA
# ══════════════════════════════════════════════════════════════════════

class Lingua:
    """
    Sistema autônomo da língua do calango.

    Instanciada pelo Player em __init__ como self.lingua = Lingua().
    Atualizada pelo Game via self.player.lingua.update(dt, origem_x, origem_y, direcao).
    Desenhada pelo Game via self.player.lingua.draw(...).

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    CONSTANTES DE GAMEPLAY
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    TONGUE_RANGE       : distância máxima da língua (px)
    TONGUE_SPEED       : velocidade de extensão/retração (px/s)
    TONGUE_ACTIVE_TIME : tempo que fica estendida ao máximo (s)
    TONGUE_COOLDOWN    : intervalo entre disparos (s)

    TONGUE_HEIGHT      : altura da hitbox (px) — não visual
    TONGUE_THICKNESS   : espessura da linha desenhada (px)
    TONGUE_COLOR       : cor RGB da língua
    TONGUE_TIP_RADIUS  : raio do círculo na ponta
    TONGUE_TIP_COLOR   : cor da ponta
    """

    # ── Gameplay ─────────────────────────────────────────────────────
    TONGUE_RANGE:       float = 180.0   # px — alcance máximo
    TONGUE_SPEED:       float = 600.0   # px/s — velocidade de extensão/retração
    TONGUE_ACTIVE_TIME: float = 0.08    # s — tempo parado no máximo alcance
    TONGUE_COOLDOWN:    float = 0.25    # s — pausa entre disparos

    # ── Hitbox ────────────────────────────────────────────────────────
    TONGUE_HEIGHT: int = 8    # px — altura da hitbox (colisão generosa)

    # ── Visual ────────────────────────────────────────────────────────
    TONGUE_THICKNESS:  int   = 3              # px
    TONGUE_COLOR:      tuple = (220, 60, 60)  # vermelho-escuro
    TONGUE_TIP_RADIUS: int   = 5              # px
    TONGUE_TIP_COLOR:  tuple = (240, 90, 90)  # vermelho-claro

    def __init__(self) -> None:
        # ── Estado ────────────────────────────────────────────────────
        self.estado: TongueState = TongueState.IDLE

        # ── Física ────────────────────────────────────────────────────
        # comprimento_atual cresce em EXTENDING e decresce em RETRACTING.
        # direcao: +1 = direita, -1 = esquerda. Extensão futura: vetor (dx, dy).
        self.comprimento_atual: float = 0.0
        self.direcao:           int   = 1   # +1 direita, -1 esquerda

        # Posição world-space da origem (boca) — atualizada a cada update()
        # para seguir o Player mesmo durante extensão.
        self.origem_x: float = 0.0
        self.origem_y: float = 0.0

        # ── Timers ────────────────────────────────────────────────────
        self.active_timer:   float = 0.0   # tempo restante no estado ACTIVE
        self.cooldown_timer: float = 0.0   # tempo restante de cooldown pós-retração

        # ── Hitbox em world-space ─────────────────────────────────────
        # None quando IDLE e cooldown zerado — sem custo de colisão.
        # Rect válido durante EXTENDING, ACTIVE e RETRACTING.
        # O Game usa diretamente: pygame.sprite.spritecollide(
        #     lingua_sprite_wrapper, grupo, False) — ou checagem manual.
        self.hitbox: pygame.Rect | None = None

    # ------------------------------------------------------------------
    # INTERFACE PÚBLICA — chamada pelo Game
    # ------------------------------------------------------------------

    @property
    def ativa(self) -> bool:
        """True quando a língua está em qualquer estado fora do IDLE com cooldown zerado."""
        return self.estado is not TongueState.IDLE

    @property
    def pode_disparar(self) -> bool:
        """True quando pode aceitar um novo disparo."""
        return (self.estado is TongueState.IDLE
                and self.cooldown_timer <= 0.0)

    def disparar(self, origem_x: float, origem_y: float, direcao: int) -> bool:
        """
        Inicia a extensão da língua.

        Chamado pelo Player (via handle_lingua) quando K_x é pressionado.
        Retorna True se o disparo foi aceito, False se bloqueado por cooldown
        ou estado incorreto.

        Parâmetros
        ──────────
        origem_x, origem_y : posição da boca em world-space
        direcao            : +1 (direita) ou -1 (esquerda)
        """
        if not self.pode_disparar:
            return False

        self.estado            = TongueState.EXTENDING
        self.comprimento_atual = 0.0
        self.direcao           = direcao
        self.origem_x          = origem_x
        self.origem_y          = origem_y
        self.active_timer      = 0.0
        return True

    def update(
        self,
        dt:       float,
        origem_x: float,
        origem_y: float,
    ) -> None:
        """
        Atualiza a máquina de estados da língua para este frame.

        A origem (boca do calango) é passada a cada frame para que a
        língua "siga" o Player enquanto estende — sem lag visual.

        Parâmetros
        ──────────
        dt              : delta time em segundos
        origem_x/y      : posição world-space atual da boca do Player
        """
        # Atualiza origem sempre — a língua segue a boca do Player
        self.origem_x = origem_x
        self.origem_y = origem_y

        if self.estado is TongueState.IDLE:
            self._atualizar_cooldown(dt)

        elif self.estado is TongueState.EXTENDING:
            self._atualizar_extending(dt)

        elif self.estado is TongueState.ACTIVE:
            self._atualizar_active(dt)

        elif self.estado is TongueState.RETRACTING:
            self._atualizar_retracting(dt)

        # Atualiza hitbox world-space para o frame
        self._atualizar_hitbox()

    def draw(
        self,
        surface:      pygame.Surface,
        origem_screen: tuple[int, int],
        cam_offset_x:  float,
        cam_offset_y:  float,
        ox:            int = 0,
        oy:            int = 0,
    ) -> None:
        """
        Renderiza a língua em screen-space.

        Deve ser chamado ANTES de player.draw() para que a língua
        apareça "atrás" do sprite do calango.

        Parâmetros
        ──────────
        surface        : pygame.Surface de destino (screen)
        origem_screen  : (x, y) em screen-space da boca do calango
                         = camera.aplicar(player.rect).move(ox, oy).midright
                           (ou midleft se virado_esquerda)
        cam_offset_x   : camera.offset_x (para converter ponta world→screen)
        cam_offset_y   : camera.offset_y
        ox, oy         : offset de screen shake
        """
        if self.estado is TongueState.IDLE or self.comprimento_atual <= 0:
            return

        # ── Posição da ponta em screen-space ──────────────────────────
        ponta_world_x = self.origem_x + self.direcao * self.comprimento_atual
        ponta_world_y = self.origem_y

        ponta_screen_x = int(ponta_world_x - cam_offset_x + ox)
        ponta_screen_y = int(ponta_world_y - cam_offset_y + oy)

        ox_screen, oy_screen = origem_screen

        # ── Linha principal ────────────────────────────────────────────
        pygame.draw.line(
            surface,
            self.TONGUE_COLOR,
            (ox_screen, oy_screen),
            (ponta_screen_x, ponta_screen_y),
            self.TONGUE_THICKNESS,
        )

        # ── Círculo na ponta ──────────────────────────────────────────
        # Indica a hitbox ativa — referência visual para o jogador.
        pygame.draw.circle(
            surface,
            self.TONGUE_TIP_COLOR,
            (ponta_screen_x, ponta_screen_y),
            self.TONGUE_TIP_RADIUS,
        )

    # ------------------------------------------------------------------
    # HOOKS PARA INTERAÇÕES — chamados pelo Game ao detectar colisão
    # ------------------------------------------------------------------

    def ao_tocar_interagivel(self, objeto: object) -> None:
        """
        Hook chamado pelo Game quando a hitbox da língua colide com
        um objeto interagível (inseto, fruta, interruptor, inimigo).

        Default: inicia retração imediata.
        ⟨futuro⟩: subclasses ou parâmetros configuram comportamento
        (captura, stun, puxão, bônus de score).

        Parâmetros
        ──────────
        objeto : qualquer sprite/objeto que implementa a interface
                 de interação — o módulo tongue não importa seus tipos.
        """
        # Retração imediata ao tocar — o Game adiciona lógica de captura
        if self.estado in (TongueState.EXTENDING, TongueState.ACTIVE):
            self._iniciar_retracao()

    # ------------------------------------------------------------------
    # ESTADOS INTERNOS
    # ------------------------------------------------------------------

    def _atualizar_cooldown(self, dt: float) -> None:
        """Decrementa cooldown quando IDLE."""
        if self.cooldown_timer > 0.0:
            self.cooldown_timer = max(0.0, self.cooldown_timer - dt)

    def _atualizar_extending(self, dt: float) -> None:
        """
        Avança o comprimento da língua.

        Usa += em vez de = para acumular o dt "troco" — ritmo constante
        mesmo sob variação de FPS (mesmo padrão da animação de inimigos).
        """
        self.comprimento_atual += self.TONGUE_SPEED * dt

        if self.comprimento_atual >= self.TONGUE_RANGE:
            self.comprimento_atual = self.TONGUE_RANGE
            self.estado            = TongueState.ACTIVE
            self.active_timer      = self.TONGUE_ACTIVE_TIME

    def _atualizar_active(self, dt: float) -> None:
        """
        Mantém língua estendida pelo TONGUE_ACTIVE_TIME.

        ⟨futuro⟩: aqui verificar colisão com interagível a cada frame
        e chamar ao_tocar_interagivel() se houver hit.
        """
        self.active_timer -= dt
        if self.active_timer <= 0.0:
            self._iniciar_retracao()

    def _atualizar_retracting(self, dt: float) -> None:
        """Retrai o comprimento da língua até zero."""
        self.comprimento_atual -= self.TONGUE_SPEED * dt

        if self.comprimento_atual <= 0.0:
            self.comprimento_atual = 0.0
            self.estado            = TongueState.IDLE
            self.cooldown_timer    = self.TONGUE_COOLDOWN
            self.hitbox            = None   # desativa colisão

    def _iniciar_retracao(self) -> None:
        """Transição limpa para RETRACTING de qualquer estado ativo."""
        self.estado       = TongueState.RETRACTING
        self.active_timer = 0.0

    # ------------------------------------------------------------------
    # HITBOX
    # ------------------------------------------------------------------

    def _atualizar_hitbox(self) -> None:
        """
        Recalcula a hitbox em world-space para o comprimento atual.

        Horizontal:
          direcao = +1 (direita): Rect(origem_x, y, comprimento, HEIGHT)
          direcao = -1 (esquerda): Rect(origem_x - comprimento, y, comprimento, HEIGHT)

        Vertical (futuro): quando a língua puder ir para cima/baixo,
        a hitbox rotaciona — basta mudar aqui sem tocar em update() ou draw().

        None quando IDLE com comprimento zero — sem custo de colisão.
        """
        if self.estado is TongueState.IDLE or self.comprimento_atual <= 0:
            self.hitbox = None
            return

        comp = int(self.comprimento_atual)
        cy   = int(self.origem_y) - self.TONGUE_HEIGHT // 2

        if self.direcao > 0:
            self.hitbox = pygame.Rect(
                int(self.origem_x), cy,
                comp, self.TONGUE_HEIGHT,
            )
        else:
            self.hitbox = pygame.Rect(
                int(self.origem_x) - comp, cy,
                comp, self.TONGUE_HEIGHT,
            )
