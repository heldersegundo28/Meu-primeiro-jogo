"""
plataforma_movel.py
═══════════════════
Sistema de plataformas móveis — módulo autônomo e desacoplado.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RESPONSABILIDADE ÚNICA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Este módulo gerencia exclusivamente o movimento da plataforma.
Ele NUNCA:
  • lê estado do Player
  • chama métodos do Game
  • importa main, player, camera, hud, telemetry ou enemies

A integração com o Player é feita inteiramente pelo Game (main.py):
  1. PlataformaMovel é adicionada ao grupo self.plataformas →
     o AABB existente do Player detecta colisão verticalmente
  2. O Game lê delta_x / delta_y e aplica ao Player externamente

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TIPOS DE MOVIMENTO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  "horizontal"  → oscila entre x_min e x_max; y fixo
  "vertical"    → oscila entre y_min e y_max; x fixo

Extensão futura "diagonal" ou "orbital":
  Adicionar novo ramo em _atualizar_posicao() — zero mudança na
  interface pública (delta_x, delta_y, rect continuam iguais).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TRANSPORTE DO PLAYER — PROTOCOLO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

A cada frame, a plataforma expõe:

  delta_x : deslocamento X ocorrido neste frame (positivo = direita)
  delta_y : deslocamento Y ocorrido neste frame (positivo = baixo)

O Game verifica se o Player está apoiado (player.no_chao e
player.rect.bottom ≈ plataforma.rect.top) e aplica o deslocamento:

  player.x      += plataforma.delta_x
  player.rect.x  = int(player.x)
  player.y      += plataforma.delta_y
  player.rect.y  = int(player.y)

Isso não altera vel_x / vel_y — apenas reposiciona o Player
junto com a plataforma, como um passageiro num elevador.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COLISÃO — INTEGRAÇÃO COM O SISTEMA EXISTENTE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PlataformaMovel é um pygame.Sprite com self.rect e self.image.
Ao adicioná-la ao grupo self.plataformas do Game, o AABB do Player
(player._colidir_eixo_y) detecta automaticamente a colisão —
zero alteração em player.py.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DEPENDÊNCIAS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  pygame  — Sprite, Rect, Surface, draw

NÃO importa: config, main, player, sprites, hud, enemies, tilemap_loader.
Todas as constantes visuais são atributos de classe.
"""

from __future__ import annotations

import pygame


class PlataformaMovel(pygame.sprite.Sprite):
    """
    Plataforma móvel oscilante — horizontal ou vertical.

    Herda de pygame.sprite.Sprite para integração direta com
    pygame.sprite.Group e pygame.sprite.spritecollide().
    Adicionada ao grupo self.plataformas do Game, o AABB do Player
    detecta colisão sem qualquer alteração em player.py.

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    ATRIBUTOS PÚBLICOS (usados pelo Game)
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

      self.rect     : pygame.Rect — hitbox e posição em world-space
      self.image    : pygame.Surface — visual da plataforma
      self.delta_x  : float — deslocamento X deste frame (px)
      self.delta_y  : float — deslocamento Y deste frame (px)

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    CONSTANTES VISUAIS
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

      COR_TOPO     : linha superior da plataforma (mais clara)
      COR_CORPO    : preenchimento principal
      COR_SOMBRA   : faixa inferior (efeito de profundidade)
      ESPESSURA_TOPO : px de destaque no topo
    """

    # ── Visual ───────────────────────────────────────────────────────
    COR_CORPO:       tuple = ( 90, 140,  70)   # verde-musgo
    COR_TOPO:        tuple = (140, 200, 110)   # verde mais claro no topo
    COR_SOMBRA:      tuple = ( 55,  90,  40)   # verde-escuro na base
    ESPESSURA_TOPO:  int   = 4                 # px da faixa de topo

    # ── Movimento ────────────────────────────────────────────────────
    TIPO_HORIZONTAL: str = "horizontal"
    TIPO_VERTICAL:   str = "vertical"

    def __init__(
        self,
        x:             int,
        y:             int,
        largura:       int,
        altura:        int,
        tipo_movimento: str,
        velocidade:    float,
        x_min:         int   = 0,
        x_max:         int   = 0,
        y_min:         int   = 0,
        y_max:         int   = 0,
    ) -> None:
        """
        Parâmetros
        ──────────
        x, y          : topleft inicial em world-space (pixels do motor)
        largura, altura: dimensões da hitbox (pixels)
        tipo_movimento: "horizontal" ou "vertical"
        velocidade    : px/s (sempre positivo; direção = sinal interno)
        x_min, x_max  : limites horizontais (pixels do motor)
        y_min, y_max  : limites verticais   (pixels do motor)
        """
        super().__init__()

        # ── Posição float autoritativa ────────────────────────────────
        # Mantida em float para acúmulo preciso de dt — sem drift.
        self.fx: float = float(x)
        self.fy: float = float(y)

        # ── Parâmetros de movimento ───────────────────────────────────
        self.tipo_movimento: str   = tipo_movimento.strip().lower()
        self.velocidade:     float = abs(velocidade)   # sempre positivo
        self.direcao:        float = 1.0               # +1 ou -1

        # ── Limites de oscilação ──────────────────────────────────────
        self.x_min: int = x_min
        self.x_max: int = x_max
        self.y_min: int = y_min
        self.y_max: int = y_max

        # ── Deltas de transporte (atualizados em update()) ─────────────
        # O Game lê estes valores para transportar o Player.
        # Zerados no início de cada frame antes da nova integração.
        self.delta_x: float = 0.0
        self.delta_y: float = 0.0

        # ── Posição spawn (para reset()) ─────────────────────────────
        self._spawn_x: int = x
        self._spawn_y: int = y

        # ── Surface e Rect ────────────────────────────────────────────
        self.image = self._construir_surface(largura, altura)
        self.rect  = self.image.get_rect(topleft=(x, y))

    # ------------------------------------------------------------------
    # INTERFACE PÚBLICA
    # ------------------------------------------------------------------

    def update(self, dt: float, *args, **kwargs) -> None:
        """
        Atualiza posição da plataforma e calcula deltas de transporte.

        Ordem de operações
        ──────────────────
        1. Guarda posição anterior (para calcular delta real)
        2. Integra posição: fx/fy += velocidade × direcao × dt
        3. Verifica limites → inverte direção se ultrapassou
           (abs()/-abs() idempotente: sem flip duplo em lag spikes)
        4. Sincroniza rect (float → int)
        5. Calcula delta_x / delta_y (deslocamento real deste frame)

        Por que guardar posição anterior ao invés de velocidade × dt?
        ────────────────────────────────────────────────────────────────
        Ao inverter no limite, o deslocamento real é menor que velocidade × dt.
        Se o Player recebesse velocidade × dt como delta, haveria um micro-salto
        visual no frame de inversão. Usar (pos_nova - pos_antiga) garante que
        o Player receba exatamente o quanto a plataforma se moveu.
        """
        # 1. Posição anterior
        fx_prev = self.fx
        fy_prev = self.fy

        # 2. Integração
        if self.tipo_movimento == self.TIPO_HORIZONTAL:
            self.fx += self.velocidade * self.direcao * dt
        elif self.tipo_movimento == self.TIPO_VERTICAL:
            self.fy += self.velocidade * self.direcao * dt

        # 3. Limites + inversão idempotente
        if self.tipo_movimento == self.TIPO_HORIZONTAL:
            if self.fx <= self.x_min:
                self.fx      = float(self.x_min)
                self.direcao = abs(self.direcao)   # força +1 (direita)
            elif self.fx + self.rect.width >= self.x_max:
                self.fx      = float(self.x_max - self.rect.width)
                self.direcao = -abs(self.direcao)  # força -1 (esquerda)

        elif self.tipo_movimento == self.TIPO_VERTICAL:
            if self.fy <= self.y_min:
                self.fy      = float(self.y_min)
                self.direcao = abs(self.direcao)   # força +1 (baixo)
            elif self.fy + self.rect.height >= self.y_max:
                self.fy      = float(self.y_max - self.rect.height)
                self.direcao = -abs(self.direcao)  # força -1 (cima)

        # 4. Sincronização rect
        self.rect.x = int(self.fx)
        self.rect.y = int(self.fy)

        # 5. Deltas reais deste frame
        self.delta_x = self.fx - fx_prev
        self.delta_y = self.fy - fy_prev

    def reset(self) -> None:
        """
        Reposiciona a plataforma no ponto de spawn original.

        Chamado por _construir_nivel() ao recarregar a fase — garante
        que a plataforma comece sempre na posição configurada no Tiled.
        """
        self.fx      = float(self._spawn_x)
        self.fy      = float(self._spawn_y)
        self.direcao = 1.0
        self.delta_x = 0.0
        self.delta_y = 0.0
        self.rect.topleft = (self._spawn_x, self._spawn_y)

    # ------------------------------------------------------------------
    # VISUAL
    # ------------------------------------------------------------------

    def _construir_surface(self, largura: int, altura: int) -> pygame.Surface:
        """
        Gera a Surface procedural da plataforma.

        Layout vertical:
          [ESPESSURA_TOPO px]  ← faixa clara (topo da plataforma)
          [resto]              ← corpo principal
          [4 px]               ← sombra inferior

        A faixa de topo sinaliza visualmente onde o Player deve pousar.
        """
        surf = pygame.Surface((largura, altura))
        surf.fill(self.COR_CORPO)

        # Faixa de topo
        pygame.draw.rect(
            surf, self.COR_TOPO,
            (0, 0, largura, self.ESPESSURA_TOPO),
        )
        # Faixa de sombra (base)
        pygame.draw.rect(
            surf, self.COR_SOMBRA,
            (0, altura - 4, largura, 4),
        )
        return surf
