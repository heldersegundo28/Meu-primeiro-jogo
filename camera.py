"""
camera.py
═════════
Câmera de scroll horizontal para o jogo Plataforma 2D — Pygame.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONCEITO CENTRAL: WORLD-SPACE vs. SCREEN-SPACE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Todo objeto do jogo existe em dois sistemas de coordenadas simultâneos:

  • World-space  (espaço de mundo)
    Coordenadas absolutas do nível — onde o objeto realmente está.
    Usadas por física, colisões e lógica de jogo.
    Nunca sofrem mutação pela câmera.
    Exemplo: plataforma em x=1 200, jogador em x=820.

  • Screen-space  (espaço de tela)
    Coordenadas relativas à janela — onde o objeto será desenhado.
    Calculadas apenas na fase de renderização (draw).
    Exemplo: com offset_x=600, a plataforma acima é desenhada em x=600.

A transformação entre os dois espaços é uma subtração simples:

    screen_x = world_x − camera.offset_x          (equação fundamental)

Esse modelo é idêntico ao usado em engines profissionais como Unity
(Camera.WorldToScreenPoint) e Godot (CanvasLayer / Camera2D).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ESTRATÉGIA: SNAP-TO-CENTER COM CLAMP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

A câmera tenta manter o alvo (normalmente o jogador) exatamente no
centro horizontal da janela. Quando o alvo se aproxima das bordas do
mundo, o offset é travado para não exibir área fora do nível.

Diagrama de estados do offset:
  ┌─────────────────────────────────────────────────────────┐
  │  mundo: 0 ─────[offset_min]────────────[offset_max]──── WORLD_WIDTH │
  │  tela:  0 ──────── âncora_x ────── SCREEN_WIDTH                    │
  │                                                                     │
  │  Zona A: alvo perto da borda esquerda → offset travado em 0        │
  │  Zona B: alvo no centro do mundo      → câmera segue livremente    │
  │  Zona C: alvo perto da borda direita  → offset travado em max      │
  └─────────────────────────────────────────────────────────┘

Variação futura — câmera com inércia (lerp):
    self.offset_x += (offset_desejado - self.offset_x) * VELOCIDADE * dt
  Produz uma câmera que "atrasa" levemente o alvo, dando sensação
  cinematográfica. A troca é um frame de lag proporcional a VELOCIDADE.
"""

from __future__ import annotations

import pygame
import config


class Camera:
    """
    Câmera 2D de scroll horizontal com centralização snap-to-center.

    Responsabilidades
    ─────────────────
    1. Manter o jogador centralizado na tela durante o gameplay.
    2. Travar o scroll nas bordas do mundo (clamp).
    3. Converter qualquer Rect de world-space para screen-space via
       o método ``aplicar``, sem modificar o Rect original.
    4. (Opcional) Bias preditivo via ``update_com_bias`` — a câmera
       "olha à frente" na direção do movimento.

    Atributo público
    ────────────────
    offset_x : float
        Deslocamento horizontal atual em pixels.
        Lido por ``Game._draw_jogo`` para ajustar cada ``blit``.
        Escrito apenas por ``update``/``update_com_bias`` e ``redimensionar``.

    Imutabilidade dos Rects de mundo
    ─────────────────────────────────
    ``aplicar`` retorna *sempre* um novo ``pygame.Rect`` — nunca
    modifica o rect passado como argumento. Isso é fundamental: os
    Rects de mundo são a fonte-da-verdade da física; corrompê-los
    durante o draw introduziria bugs de colisão intermitentes e
    difíceis de rastrear.
    """

    def __init__(self, largura_mundo: int = config.WORLD_WIDTH) -> None:
        """
        Inicializa a câmera para um nível de largura ``largura_mundo``.

        Parâmetro
        ─────────
        largura_mundo : int
            Largura total do nível em pixels. Passado explicitamente
            (em vez de ler ``config.WORLD_WIDTH`` dentro da classe)
            para que câmeras com mundos de tamanhos variados possam
            coexistir sem alterar o módulo de configuração — útil
            ao carregar fases com dimensões distintas do arquivo .txt.

        Pré-computação dos limites de clamp
        ────────────────────────────────────
        Os limites são calculados uma única vez no construtor e
        reutilizados em todos os frames. Isso evita subtrações
        redundantes a 60 FPS.

            offset_min = 0
                → câmera nunca recua além da borda esquerda do mundo.

            offset_max = largura_mundo − SCREEN_WIDTH
                → câmera nunca avança além da borda direita.
                → ``max(0, ...)`` protege o caso edge de mundos menores
                   que a tela (offset_max nunca fica negativo).
        """
        self.offset_x: float = 0.0

        # Coluna de tela onde o alvo será ancorado.
        # SCREEN_WIDTH / 2 = centro exato da janela.
        # Pode ser ajustado para "câmera assimétrica" (ex.: 1/3 da tela)
        # sem nenhuma outra mudança no código.
        self._ancora_x: float = config.SCREEN_WIDTH / 2.0

        # Limites de clamp pré-computados (imutáveis durante a fase).
        self._offset_min: float = 0.0
        self._offset_max: float = max(
            0.0, float(largura_mundo - config.SCREEN_WIDTH)
        )

        # Bias preditivo atual (acumulado via lerp em update_com_bias).
        # Separado de offset_x para que update() (snap) nunca herde
        # um bias residual de update_com_bias().
        self._bias_atual: float = 0.0

    # ------------------------------------------------------------------
    def update(self, alvo: pygame.Rect) -> None:
        """
        Recalcula ``offset_x`` para centralizar o alvo na tela.

        Chamada uma vez por frame, *após* toda a lógica de movimento
        do alvo ter sido processada, para ler a posição final do frame.

        Matemática passo a passo
        ────────────────────────
        Queremos que, após a transformação, o centro do alvo apareça
        na coluna ``_ancora_x`` da tela:

            screen_x_do_alvo  ==  _ancora_x
            world_x_do_alvo − offset_x  ==  _ancora_x
            offset_x  ==  world_x_do_alvo − _ancora_x      ← offset desejado

        Depois aplicamos o clamp para manter o offset dentro dos
        limites válidos do mundo:

            offset_x = clamp(offset_desejado, offset_min, offset_max)

        Parâmetro
        ─────────
        alvo : pygame.Rect
            Rect do objeto a seguir em world-space.
            Normalmente ``player.rect``.
        """
        offset_desejado: float = float(alvo.centerx) - self._ancora_x
        self.offset_x = max(
            self._offset_min,
            min(offset_desejado, self._offset_max),
        )

    # ------------------------------------------------------------------
    def update_com_bias(
        self,
        alvo:    pygame.Rect,
        vel_x:   float,
        dt:      float,
        fator:   float = 0.25,
        lerp:    float = 5.0,
        max_px:  float = 80.0,
    ) -> None:
        """
        Câmera Juice com bias preditivo baseado na velocidade horizontal.

        Conceito: Lead / Predictive Camera
        ────────────────────────────────────
        Em vez de manter o jogador exatamente no centro, a câmera
        "olha um pouco à frente" na direção do movimento — revelando
        mais terreno à frente e menos atrás.

        Diagrama de bias:
            vel_x = +160 (correndo →)
            bias_alvo = +160 × 0.25 = +40px
            câmera avança 40px à frente do jogador

            ┌──────────────────────────────────────────┐
            │   ← 40px →   [calango]                  │
            │  (revelado    (não mais   (mais visível) │
            │   a mais)      no centro)                │
            └──────────────────────────────────────────┘

        Interpolação suave (lerp × dt)
        ────────────────────────────────
        O bias não salta para o alvo imediatamente — interpola via:
            bias_atual += (bias_alvo - bias_atual) × lerp × dt

        Isso evita trancos ao mudar de direção: o bias desliza
        suavemente de +40 → 0 → -40 ao inverter o movimento.

        Separação bias / offset_x
        ───────────────────────────
        O bias é acumulado em ``self._bias_atual`` (não em offset_x
        diretamente). O offset final é calculado como:
            offset_x = clamp(centro_alvo - ancora_x + bias_atual, min, max)

        Isso garante que o clamp de bordas leve o bias em conta —
        a câmera não ultrapassará as bordas do mundo mesmo com bias alto.

        Parâmetros
        ──────────
        alvo     : Rect do jogador (world-space)
        vel_x    : velocidade horizontal do jogador (telemetria)
        dt       : delta time em segundos
        fator    : proporção vel_x → bias em pixels (default 0.25)
                   vel_x=160 → bias_alvo=40px
        lerp     : taxa de interpolação do bias por segundo (default 5.0)
                   Maior = câmera mais responsiva; menor = mais suave
        max_px   : limite absoluto do bias em pixels (default 80px)
                   Impede que corrida a alta velocidade empurre demais a câmera
        """
        # ── Calcula o bias alvo proporcional à velocidade ─────────────
        bias_alvo: float = max(-max_px, min(vel_x * fator, max_px))

        # ── Lerp suave do bias atual → alvo ────────────────────────────
        # lerp(a, b, t) = a + (b - a) × t   com   t = lerp × dt
        self._bias_atual += (bias_alvo - self._bias_atual) * lerp * dt

        # ── Offset final: centro + bias, depois clamp ──────────────────
        offset_desejado = (float(alvo.centerx) - self._ancora_x
                           + self._bias_atual)
        self.offset_x = max(
            self._offset_min,
            min(offset_desejado, self._offset_max),
        )

    # ------------------------------------------------------------------
    def aplicar(self, rect: pygame.Rect) -> pygame.Rect:
        """
        Converte um Rect de world-space para screen-space.

        Aplica a equação fundamental da câmera:

            screen_x = world_x − camera.offset_x

        Garantias de imutabilidade
        ───────────────────────────
        • Retorna um *novo* ``pygame.Rect`` a cada chamada.
        • O ``rect`` original nunca é modificado (sem side effects).
        • A coordenada Y é copiada sem alteração — scroll é só horizontal.

        Uso típico em ``draw()``:
            surface.blit(sprite.image, camera.aplicar(sprite.rect))

        Parâmetro
        ─────────
        rect : pygame.Rect
            Rect em world-space. Não será modificado.

        Retorno
        ───────
        pygame.Rect
            Novo Rect em screen-space, pronto para ``blit`` ou
            ``pygame.draw``. Dimensões (width, height) preservadas.
        """
        return pygame.Rect(
            int(rect.x - self.offset_x),  # única coordenada afetada
            rect.y,                        # Y inalterado (sem scroll vertical)
            rect.width,
            rect.height,
        )

    # ------------------------------------------------------------------
    def redimensionar(self, largura_mundo: int) -> None:
        """
        Atualiza os limites de clamp para um novo tamanho de mundo.

        Chamada por ``Game._construir_nivel`` ao carregar uma fase
        cujas dimensões diferem do valor padrão de ``config.WORLD_WIDTH``.

        Após o redimensionamento, ``offset_x`` é re-clampado para
        garantir que a posição atual da câmera permaneça válida — evita
        que a câmera fique apontando para além das bordas do novo nível.

        Parâmetro
        ─────────
        largura_mundo : int
            Nova largura do mundo em pixels.
        """
        self._offset_max = max(
            0.0, float(largura_mundo - config.SCREEN_WIDTH)
        )
        # Re-clamp do estado atual: evita offset inválido após a troca de fase
        self.offset_x = max(
            self._offset_min,
            min(self.offset_x, self._offset_max),
        )

    # ------------------------------------------------------------------
    def __repr__(self) -> str:
        """Representação de depuração legível no terminal e no debugger."""
        return (
            f"Camera("
            f"offset_x={self.offset_x:.1f}, "
            f"ancora_x={self._ancora_x:.1f}, "
            f"range=[{self._offset_min:.0f}, {self._offset_max:.0f}]"
            f")"
        )
