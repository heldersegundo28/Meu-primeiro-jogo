"""
traps.py
════════
Sistema modular de armadilhas ambientais.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RESPONSABILIDADE ÚNICA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Este módulo contém toda a lógica das armadilhas.
Ele NUNCA:
  • chama player.tomar_dano() diretamente
  • lê self.vidas do Game
  • importa main, player, hud, camera, enemies, tilemap_loader

O canal de saída é is_dangerous() + self.rect — o Game detecta
colisão e aplica o dano, exatamente como faz com inimigos.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PONTOS DE EXTENSÃO DE GAME FEEL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Cada armadilha expõe uma One-Frame Flag para o Game despachar
efeitos adicionais sem acoplamento:

  just_activated : bool — True no frame em que a armadilha ativa
                          (ex: planta abre, pedra começa a rolar)
                          → Game pode disparar screen shake, SFX, partículas

Padrão idêntico ao just_landed e just_lost_tail do Player.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HIERARQUIA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ArmadilhaBase (pygame.Sprite)
    ├── PlantaCarnivora   — área de ativação + janela de ataque
    ├── PedraRolante      — roll horizontal acionado por proximidade
    └── GalhoCaindo       — queda cronometrada acionada por detecção

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DEPENDÊNCIAS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  pygame  — Sprite, Rect, Surface, draw, Color
  enum    — estados de FSM

NÃO importa: config, main, player, sprites, hud, enemies, tilemap_loader.
"""

from __future__ import annotations

import math
from enum import Enum, auto

import pygame


# ══════════════════════════════════════════════════════════════════════
# FACTORY PÚBLICA
# ══════════════════════════════════════════════════════════════════════

def create_trap(dados: dict) -> "ArmadilhaBase | None":
    """
    Instancia a armadilha correta para o tipo informado.

    Parâmetros
    ──────────
    dados : dict com campos obrigatórios "tipo", "x", "y"
            e campo opcional "props" (dict de propriedades do Tiled).

    Retorno
    ───────
    Subclasse concreta de ArmadilhaBase ou None se tipo desconhecido.

    Para adicionar novo tipo:
        1. Criar subclasse de ArmadilhaBase neste arquivo
        2. Adicionar ao _REGISTRY abaixo — ÚNICA mudança necessária
    """
    tipo  = dados.get("tipo", "")
    props = dados.get("props", {})
    x, y  = dados["x"], dados["y"]

    cls = _REGISTRY.get(tipo)
    if cls is None:
        print(
            f"[Traps] AVISO: tipo '{tipo}' não reconhecido. "
            f"Tipos: {sorted(_REGISTRY.keys())}. "
            f"Armadilha ignorada em ({x}, {y})."
        )
        return None

    return cls(x, y, props)


# ══════════════════════════════════════════════════════════════════════
# BASE
# ══════════════════════════════════════════════════════════════════════

class ArmadilhaBase(pygame.sprite.Sprite):
    """
    Contrato base para todas as armadilhas.

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    INTERFACE PÚBLICA (o que o Game usa em qualquer armadilha)
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

      update(dt, player_rect)  — avança estado; player_rect é leitura pura
      is_dangerous()           — True quando a hitbox deve causar dano
      reset()                  — volta ao estado inicial (nova fase/retry)
      self.rect                — hitbox de dano (None = sem colisão ativa)
      self.image               — frame visual atual
      self.just_activated      — One-Frame Flag: True no frame de ativação
    """

    def __init__(self, x: int, y: int) -> None:
        super().__init__()
        self._spawn_x: int = x
        self._spawn_y: int = y
        self.just_activated: bool = False   # One-Frame Flag para game feel

        # Subclasses devem atribuir image e rect em seu __init__
        self.image: pygame.Surface = pygame.Surface((0, 0))
        self.rect:  pygame.Rect   = pygame.Rect(x, y, 0, 0)

    def update(self, dt: float, player_rect: pygame.Rect) -> None:
        """Subclasses DEVEM implementar."""
        raise NotImplementedError(f"{type(self).__name__} deve implementar update()")

    def is_dangerous(self) -> bool:
        """True quando a armadilha deve causar dano ao tocar o Player."""
        raise NotImplementedError

    def reset(self) -> None:
        """Restaura ao estado inicial. Subclasses devem chamar super()."""
        self.just_activated = False

    def _fallback_surface(self, w: int, h: int, cor: tuple) -> pygame.Surface:
        """Surface sólida de fallback — subclasses usam para placeholder visual."""
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.fill(cor)
        return surf


# ══════════════════════════════════════════════════════════════════════
# TIPO 1 — PLANTA CARNÍVORA
# ══════════════════════════════════════════════════════════════════════

class _EstadoPlanta(Enum):
    IDLE     = auto()   # aguardando; hitbox inativa
    ATACANDO = auto()   # janela de dano ativa
    RECARGA  = auto()   # cooldown pós-ataque; hitbox inativa


class PlantaCarnivora(ArmadilhaBase):
    """
    Planta fixa com área de ativação e janela de dano cronometrada.

    FSM
    ────
    IDLE ──(player entra no alcance)──► ATACANDO
                                            │ TEMPO_ATAQUE s
                                            ▼
                                         RECARGA
                                            │ tempo_recarga s
                                            ▼
                                          IDLE

    Hitbox de dano: ativa apenas em ATACANDO.
    Área de ativação: círculo invisible de raio alcance (não é hitbox de dano).
    """

    # ── Constantes visuais ────────────────────────────────────────────
    LARGURA:      int   = 30
    ALTURA:       int   = 40
    TEMPO_ATAQUE: float = 0.4    # s de janela perigosa

    COR_CAULE:    tuple = ( 50, 120,  50)
    COR_BOCA_OFF: tuple = ( 30,  90,  30)
    COR_BOCA_ON:  tuple = (220,  60,  60)   # vermelho ao atacar
    COR_DENTE:    tuple = (240, 240, 220)

    def __init__(self, x: int, y: int, props: dict) -> None:
        super().__init__(x, y)

        self.alcance:       int   = int(props.get("alcance",      120))
        self.tempo_recarga: float = float(props.get("tempo_recarga", 2.0))

        self._estado:  _EstadoPlanta = _EstadoPlanta.IDLE
        self._timer:   float         = 0.0

        # Surfaces pré-geradas
        self._surf_idle   = self._gerar_surface(atacando=False)
        self._surf_ataque = self._gerar_surface(atacando=True)

        self.image = self._surf_idle
        self.rect  = self.image.get_rect(bottomleft=(x, y))

    # ------------------------------------------------------------------

    def update(self, dt: float, player_rect: pygame.Rect) -> None:
        self.just_activated = False

        if self._estado is _EstadoPlanta.IDLE:
            # Detecta proximidade pelo centro do player
            dx = player_rect.centerx - self.rect.centerx
            dy = player_rect.centery - self.rect.centery
            if math.hypot(dx, dy) <= self.alcance:
                self._estado        = _EstadoPlanta.ATACANDO
                self._timer         = self.TEMPO_ATAQUE
                self.image          = self._surf_ataque
                self.just_activated = True   # ← game feel hook

        elif self._estado is _EstadoPlanta.ATACANDO:
            self._timer -= dt
            if self._timer <= 0.0:
                self._estado = _EstadoPlanta.RECARGA
                self._timer  = self.tempo_recarga
                self.image   = self._surf_idle

        elif self._estado is _EstadoPlanta.RECARGA:
            self._timer -= dt
            if self._timer <= 0.0:
                self._estado = _EstadoPlanta.IDLE

    def is_dangerous(self) -> bool:
        return self._estado is _EstadoPlanta.ATACANDO

    def reset(self) -> None:
        super().reset()
        self._estado = _EstadoPlanta.IDLE
        self._timer  = 0.0
        self.image   = self._surf_idle
        self.rect.bottomleft = (self._spawn_x, self._spawn_y)

    # ------------------------------------------------------------------

    def _gerar_surface(self, atacando: bool) -> pygame.Surface:
        """
        Planta procedural: caule + boca (fechada idle, aberta atacando).

        Estrutura vertical:
          topo 60% → boca (cor varia com estado)
          base 40% → caule verde
        """
        w, h = self.LARGURA, self.ALTURA
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 0))

        # Caule
        pygame.draw.rect(surf, self.COR_CAULE, (w // 2 - 4, int(h * 0.55), 8, int(h * 0.45)))

        # Corpo da boca (elipse)
        cor_boca = self.COR_BOCA_ON if atacando else self.COR_BOCA_OFF
        boca_rect = pygame.Rect(2, 2, w - 4, int(h * 0.60))
        pygame.draw.ellipse(surf, cor_boca, boca_rect)

        if atacando:
            # Dentes: triângulos simples
            cy = boca_rect.centery
            for tx in range(4, w - 4, 8):
                pygame.draw.polygon(surf, self.COR_DENTE, [
                    (tx, cy - 6), (tx + 4, cy - 6), (tx + 2, cy),
                ])
                pygame.draw.polygon(surf, self.COR_DENTE, [
                    (tx, cy + 6), (tx + 4, cy + 6), (tx + 2, cy),
                ])

        return surf


# ══════════════════════════════════════════════════════════════════════
# TIPO 2 — PEDRA ROLANTE
# ══════════════════════════════════════════════════════════════════════

class _EstadoPedra(Enum):
    PARADA  = auto()   # aguardando; hitbox inativa (não causa dano parada)
    ROLANDO = auto()   # em movimento; hitbox ativa


class PedraRolante(ArmadilhaBase):
    """
    Pedra que começa a rolar quando o player entra na área de ativação.

    FSM
    ────
    PARADA ──(player entra em alcance)──► ROLANDO
    ROLANDO → sempre rola até sair da tela (não reverte)

    Hitbox de dano: ativa apenas em ROLANDO.
    Colisão com parede/limite: a pedra some (kill()) — reaparecer
    seria retrabalho de física fora do escopo desta etapa.
    """

    RAIO:     int = 20   # px — raio visual e de hitbox
    ALCANCE:  int = 200  # px — distância de ativação padrão

    COR_CORPO:  tuple = (130, 100,  70)
    COR_BORDA:  tuple = ( 90,  70,  50)
    COR_PARADA: tuple = ( 80,  80,  90)   # cinza quando parada

    def __init__(self, x: int, y: int, props: dict) -> None:
        super().__init__(x, y)

        self.velocidade: float = float(props.get("velocidade", 180.0))
        # direcao: +1 = direita, -1 = esquerda
        self.direcao:    float = float(props.get("direcao", -1.0))
        self.alcance:    int   = int(props.get("alcance", self.ALCANCE))

        self._estado:   _EstadoPedra = _EstadoPedra.PARADA
        self._fx:       float        = float(x)
        self._rotacao:  float        = 0.0   # graus — visual de rolagem

        self._surf_base = self._gerar_surface()
        self.image = self._surf_parada()
        self.rect  = self.image.get_rect(center=(x, y))

    # ------------------------------------------------------------------

    def update(self, dt: float, player_rect: pygame.Rect) -> None:
        self.just_activated = False

        if self._estado is _EstadoPedra.PARADA:
            dx = abs(player_rect.centerx - self.rect.centerx)
            if dx <= self.alcance:
                self._estado        = _EstadoPedra.ROLANDO
                self.just_activated = True
                self.image          = self._gerar_surface()

        elif self._estado is _EstadoPedra.ROLANDO:
            self._fx      += self.velocidade * self.direcao * dt
            self._rotacao  = (self._rotacao + self.velocidade * dt * 2) % 360

            self.rect.centerx = int(self._fx)
            self.image = pygame.transform.rotate(self._gerar_surface(), -self._rotacao)
            self.rect  = self.image.get_rect(center=self.rect.center)

    def is_dangerous(self) -> bool:
        return self._estado is _EstadoPedra.ROLANDO

    def reset(self) -> None:
        super().reset()
        self._estado    = _EstadoPedra.PARADA
        self._fx        = float(self._spawn_x)
        self._rotacao   = 0.0
        self.image      = self._surf_parada()
        self.rect       = self.image.get_rect(center=(self._spawn_x, self._spawn_y))

    # ------------------------------------------------------------------

    def _gerar_surface(self) -> pygame.Surface:
        """Círculo preenchido com bordas simulando rocha."""
        d = self.RAIO * 2
        surf = pygame.Surface((d, d), pygame.SRCALPHA)
        pygame.draw.circle(surf, self.COR_CORPO,  (self.RAIO, self.RAIO), self.RAIO)
        pygame.draw.circle(surf, self.COR_BORDA,  (self.RAIO, self.RAIO), self.RAIO, 3)
        # Veios de rocha: 3 linhas diagonais
        for ang in (30, 90, 150):
            rad = math.radians(ang)
            x0 = int(self.RAIO + (self.RAIO - 5) * math.cos(rad))
            y0 = int(self.RAIO + (self.RAIO - 5) * math.sin(rad))
            x1 = int(self.RAIO - (self.RAIO - 5) * math.cos(rad))
            y1 = int(self.RAIO - (self.RAIO - 5) * math.sin(rad))
            pygame.draw.line(surf, self.COR_BORDA, (x0, y0), (x1, y1), 1)
        return surf

    def _surf_parada(self) -> pygame.Surface:
        """Visual cinza quando parada — distingue visualmente do estado ativo."""
        d = self.RAIO * 2
        surf = pygame.Surface((d, d), pygame.SRCALPHA)
        pygame.draw.circle(surf, self.COR_PARADA, (self.RAIO, self.RAIO), self.RAIO)
        pygame.draw.circle(surf, self.COR_BORDA,  (self.RAIO, self.RAIO), self.RAIO, 2)
        return surf


# ══════════════════════════════════════════════════════════════════════
# TIPO 3 — GALHO QUE CAI
# ══════════════════════════════════════════════════════════════════════

class _EstadoGalho(Enum):
    SUSPENSO = auto()   # no alto, aguardando
    TREMENDO = auto()   # contagem regressiva (tremor visual)
    CAINDO   = auto()   # em queda; hitbox ativa
    NO_CHAO  = auto()   # pousou; obstáculo visual; hitbox inativa


class GalhoCaindo(ArmadilhaBase):
    """
    Galho suspenso que cai quando o player passa abaixo.

    FSM
    ────
    SUSPENSO ──(player abaixo)──► TREMENDO
    TREMENDO ──(tempo_ativacao s)──► CAINDO
    CAINDO   ──(atinge y_chao)──► NO_CHAO

    Hitbox de dano: ativa apenas em CAINDO.
    Detecção "abaixo": player.rect.top > self.rect.bottom E dentro da
    faixa horizontal do galho (±largura/2).
    """

    LARGURA:        int   = 80
    ESPESSURA:      int   = 14
    VELOCIDADE_QUEDA: float = 600.0   # px/s
    AMPLITUDE_TREMOR: float = 3.0     # px de oscilação horizontal

    COR_CASCA:    tuple = (100,  70,  40)
    COR_MADEIRA:  tuple = (150, 100,  60)
    COR_FOLHA:    tuple = ( 50, 130,  50)

    def __init__(self, x: int, y: int, props: dict) -> None:
        super().__init__(x, y)

        self.tempo_ativacao: float = float(props.get("tempo_ativacao", 0.5))
        self._y_chao:        int   = int(props.get("y_chao", y + 400))

        self._estado:    _EstadoGalho = _EstadoGalho.SUSPENSO
        self._timer:     float        = 0.0
        self._fy:        float        = float(y)
        self._tremor_t:  float        = 0.0   # acumula para oscilação

        self._surf_galho = self._gerar_surface()
        self.image       = self._surf_galho
        self.rect        = self.image.get_rect(topleft=(x, y))

    # ------------------------------------------------------------------

    def update(self, dt: float, player_rect: pygame.Rect) -> None:
        self.just_activated = False

        if self._estado is _EstadoGalho.SUSPENSO:
            # Detecta player abaixo dentro da faixa horizontal
            dentro_x = (player_rect.left < self.rect.right and
                        player_rect.right > self.rect.left)
            abaixo_y = player_rect.top > self.rect.bottom
            if dentro_x and abaixo_y:
                self._estado        = _EstadoGalho.TREMENDO
                self._timer         = self.tempo_ativacao
                self.just_activated = True

        elif self._estado is _EstadoGalho.TREMENDO:
            self._timer    -= dt
            self._tremor_t += dt
            # Oscilação horizontal senoidal
            offset_x = int(self.AMPLITUDE_TREMOR * math.sin(self._tremor_t * 30))
            self.rect.x = self._spawn_x + offset_x

            if self._timer <= 0.0:
                self._estado = _EstadoGalho.CAINDO
                self.rect.x  = self._spawn_x   # centraliza antes de cair

        elif self._estado is _EstadoGalho.CAINDO:
            self._fy     += self.VELOCIDADE_QUEDA * dt
            self.rect.y   = int(self._fy)

            if self.rect.y >= self._y_chao:
                self.rect.y  = self._y_chao
                self._fy     = float(self._y_chao)
                self._estado = _EstadoGalho.NO_CHAO

        # NO_CHAO: sem atualização — galho permanece como obstáculo visual

    def is_dangerous(self) -> bool:
        return self._estado is _EstadoGalho.CAINDO

    def reset(self) -> None:
        super().reset()
        self._estado   = _EstadoGalho.SUSPENSO
        self._timer    = 0.0
        self._fy       = float(self._spawn_y)
        self._tremor_t = 0.0
        self.rect.topleft = (self._spawn_x, self._spawn_y)

    # ------------------------------------------------------------------

    def _gerar_surface(self) -> pygame.Surface:
        """Galho horizontal procedural com textura de casca e folhas."""
        w, h = self.LARGURA, self.ESPESSURA + 8
        surf = pygame.Surface((w, h), pygame.SRCALPHA)

        # Corpo do galho
        pygame.draw.rect(surf, self.COR_MADEIRA, (0, 4, w, self.ESPESSURA))
        pygame.draw.rect(surf, self.COR_CASCA,   (0, 4, w, self.ESPESSURA), 2)

        # Veios horizontais
        for vy in (6, 10):
            pygame.draw.line(surf, self.COR_CASCA, (4, vy), (w - 4, vy), 1)

        # Folhas no topo (pequenos círculos)
        for fx in range(6, w - 6, 12):
            pygame.draw.circle(surf, self.COR_FOLHA, (fx, 4), 5)

        return surf


# ══════════════════════════════════════════════════════════════════════
# REGISTRY — adicionar novos tipos aqui
# ══════════════════════════════════════════════════════════════════════

_REGISTRY: dict[str, type[ArmadilhaBase]] = {
    "planta_carnivora": PlantaCarnivora,
    "pedra_rolante":    PedraRolante,
    "galho_caindo":     GalhoCaindo,

    # Futuras entradas:
    # "espinho_retratil": EspinhoRetratil,
    # "bola_fogo":        BolaFogo,
    # "piso_falso":       PisoFalso,
}
