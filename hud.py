"""
hud.py
══════
HUD (Heads-Up Display) — camada de interface do jogador.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RESPONSABILIDADE ÚNICA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Este módulo renderiza informações de jogo em screen-space (coordenadas
fixas, sem câmera). Ele NUNCA:
  • lê estado do Game, Player, Câmera ou qualquer outro objeto do projeto
  • modifica qualquer variável fora do módulo
  • chama métodos de transição de estado
  • aloca Surfaces por frame (fontes e surfs estáticos são pré-criados)

O único canal de entrada é HudData — um dataclass puro de dados.
O único canal de saída é pygame.Surface (via draw()).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LAYOUT DA HUD (800×600 padrão)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ┌───────────────────────────────────────────────────────────────┐
  │ ♥ ♥ ♥           FASE  2 / 5              Score: 350          │  ← linha 1
  │ ▓▓▓▓▓▓▓░░░░      Larvas: 5/8                                 │  ← linha 2
  │                 [✔ Checkpoint]                               │  ← linha 3 (só se ativo)
  ├ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┤
  │ DEBUG: FPS:59  X:1240 Y:320  Vx:160 Vy:0  Estado:JOGANDO     │  ← debug (DEBUG_HUD=True)
  └───────────────────────────────────────────────────────────────┘

  Coluna esquerda  (x=PAD):             vidas, barra de moedas, contagem
  Coluna centro    (x=SW//2):           fase atual / total
  Coluna direita   (x=SW-PAD):         score
  Linha checkpoint (y=LINHA_CP_Y):      indicador discreto, centralizado
  Linha debug      (y=LINHA_DEBUG_Y):   apenas se DEBUG_HUD=True

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ESTRUTURA PARA FUTURAS EXPANSÕES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Para adicionar uma barra de energia:
    1. Adicionar campo `energia: float` e `energia_max: float` em HudData
    2. Chamar _barra() com as cores desejadas na posição reservada
    3. Zero mudança em main.py além de preencher o novo campo

Para adicionar ícone de habilidade:
    1. Adicionar campo `habilidade_ativa: bool` em HudData
    2. Renderizar indicador na posição LINHA_HAB_Y (constante reservada)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DEPENDÊNCIAS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  pygame   — renderização
  config   — constantes de cor e resolução (leitura apenas)
  dataclasses — HudData sem boilerplate

NÃO importa: main, player, camera, sprites, tilemap_loader, game_states.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pygame

import config


# ══════════════════════════════════════════════════════════════════════
# CONTROLE DE DEBUG
# ══════════════════════════════════════════════════════════════════════

# Quando True, exibe painel de debug abaixo da HUD normal.
# Mudar para True durante desenvolvimento; False para build final.
# Alternativa: ler de variável de ambiente: os.getenv("HUD_DEBUG", "0") == "1"
DEBUG_HUD: bool = False


# ══════════════════════════════════════════════════════════════════════
# CONSTANTES DE LAYOUT
# ══════════════════════════════════════════════════════════════════════
# Centralizadas aqui para que reposicionamento seja uma alteração
# de uma linha, não uma caçada por números espalhados.

# ── Margens e espaçamentos ────────────────────────────────────────────
PAD:      int = 10    # margem das bordas da tela (px)
ESPACO_V: int = 4     # espaçamento vertical entre sub-elementos (px)

# ── Posições Y dos grupos de elementos ───────────────────────────────
LINHA_1_Y: int = PAD                           # vidas / fase / score
LINHA_2_Y: int = LINHA_1_Y + 32               # barra de moedas + contagem
LINHA_3_Y: int = LINHA_2_Y + 26               # reservada: energia futura
LINHA_CP_Y:   int = LINHA_3_Y + ESPACO_V       # indicador de checkpoint
LINHA_CAUDA_Y: int = LINHA_CP_Y + 22           # indicador de autotomia
LINHA_HAB_Y:  int = LINHA_CAUDA_Y + 22         # reservada: habilidades futuras
LINHA_DEBUG_Y: int = LINHA_HAB_Y + 26         # painel de debug

# ── Barra de moedas ───────────────────────────────────────────────────
BARRA_W:  int = 160   # largura total da barra (px)
BARRA_H:  int = 10    # altura da barra (px)
BARRA_RAIO: int = 4   # border-radius para visual suave

# ── Tamanhos de fonte (SysFont None = fonte padrão do sistema) ────────
TAMANHO_FONTE_VIDAS:  int = 30   # corações Unicode
TAMANHO_FONTE_FASE:   int = 28   # "FASE N/T"
TAMANHO_FONTE_SCORE:  int = 28   # "Score: NNN"
TAMANHO_FONTE_LARVAS: int = 22   # "Larvas: N/T"
TAMANHO_FONTE_CP:     int = 20   # "✔ Checkpoint Ativo"
TAMANHO_FONTE_DEBUG:  int = 18   # linha de debug

# ── Cores da HUD ──────────────────────────────────────────────────────
# Derivadas de config.* para manter consistência de paleta.
# Cores próprias da HUD ficam aqui — sem dispersar em config.py.
COR_VIDAS_CHEIAS:  tuple = config.RED              # ♥
COR_VIDAS_VAZIAS:  tuple = (100, 40, 40)           # ♡ (vermelho escuro)
COR_FASE:          tuple = config.WHITE
COR_SCORE:         tuple = config.YELLOW
COR_BARRA_FUNDO:   tuple = (70, 70, 70)            # trilho da barra
COR_BARRA_LARVAS:  tuple = config.YELLOW           # preenchimento
COR_LARVAS_TEXTO:  tuple = config.WHITE
COR_CHECKPOINT:    tuple = (120, 220, 120)         # verde suave
COR_CAUDA_OK:      tuple = ( 80, 200, 120)         # verde: cauda disponível
COR_CAUDA_PERDIDA: tuple = (220,  80,  80)         # vermelho: cauda perdida
COR_DEBUG_FUNDO:   tuple = (0, 0, 0, 180)          # painel semi-opaco
COR_DEBUG_TEXTO:   tuple = (200, 255, 200)         # verde terminal
COR_SOMBRA:        tuple = config.BLACK            # sombra de texto


# ══════════════════════════════════════════════════════════════════════
# DADO DE ENTRADA
# ══════════════════════════════════════════════════════════════════════

@dataclass
class HudData:
    """
    Snapshot imutável dos dados de jogo que a HUD precisa para desenhar.

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    CONTRATO DE DESACOPLAMENTO
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    HudData contém APENAS tipos primitivos (int, float, bool, str).
    Nenhum objeto do projeto (Player, Game, Checkpoint …) é passado —
    isso garante que a HUD nunca possa modificar estado de jogo por acidente.

    O main.py monta um HudData por frame antes de chamar hud.draw().
    O custo de criação de um dataclass pequeno por frame é negligível
    comparado a um blit de Surface.

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    CAMPOS
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    Etapa 1 — Fase atual
        fase_atual    : fase que está sendo jogada (ex: 2)
        total_fases   : número total de fases da campanha (ex: 5)

    Etapa 2 — Moedas / Larvas
        moedas_total  : total de larvas no nível carregado
        moedas_restantes: larvas ainda não coletadas (usado para calcular coletas)

    Etapa 3 — Vidas
        vidas         : vidas atuais do jogador
        vidas_max     : máximo de vidas possíveis

    Etapa 4 — Checkpoint
        checkpoint_ativo: True se há checkpoint registrado nesta fase

    Etapa 5 — Debug (usado apenas se DEBUG_HUD=True)
        fps           : FPS medido no frame atual
        player_x      : posição world-space X do player (px)
        player_y      : posição world-space Y do player (px)
        vel_x         : velocidade horizontal do player (px/s)
        vel_y         : velocidade vertical do player (px/s)
        estado_jogo   : repr do GameState atual (string)

    Campos futuros (reservados, não usados ainda)
        score         : pontuação atual (ex: 350)
    """
    # ── Etapa 1: fase ────────────────────────────────────────────────
    fase_atual:    int = 1
    total_fases:   int = 1

    # ── Etapa 2: larvas / moedas ──────────────────────────────────────
    moedas_total:     int = 0
    moedas_restantes: int = 0

    # ── Etapa 3: vidas ────────────────────────────────────────────────
    vidas:     int = 3
    vidas_max: int = 3

    # ── Etapa 4: checkpoint ───────────────────────────────────────────
    checkpoint_ativo: bool = False

    # ── Autotomia ─────────────────────────────────────────────────────
    # tem_cauda: True = cauda disponível (exibe indicador cheio).
    #            False = cauda perdida (exibe indicador vazio/alerta).
    tem_cauda: bool = True

    # ── Score ─────────────────────────────────────────────────────────
    score: int = 0

    # ── Etapa 5: debug ────────────────────────────────────────────────
    fps:         float = 0.0
    player_x:    float = 0.0
    player_y:    float = 0.0
    vel_x:       float = 0.0
    vel_y:       float = 0.0
    estado_jogo: str   = ""


# ══════════════════════════════════════════════════════════════════════
# HUD
# ══════════════════════════════════════════════════════════════════════

class Hud:
    """
    Renderizador da HUD — recebe dados, produz pixels.

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    CICLO DE VIDA
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

      1. Instanciar uma vez: hud = Hud()
         → fontes criadas aqui (SysFont tem custo de I/O)

      2. A cada frame de gameplay:
         dados = HudData(fase_atual=..., vidas=..., ...)
         hud.draw(screen, dados)

    Nenhuma referência ao Game, Player ou qualquer outro objeto
    do projeto é armazenada internamente.

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    ESTADO INTERNO (somente para performance)
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

      _fontes    : dict de pygame.font.Font pré-carregadas
      _surf_debug: Surface semi-opaca do painel de debug (recriada
                   apenas quando DEBUG_HUD muda, não a cada frame)

    Toda Surface de texto é criada no momento do draw() — o custo
    por frame de font.render() é desprezível para textos curtos e
    evita cache stale sem invalidação explícita.
    """

    def __init__(self) -> None:
        # ── Fontes pré-carregadas ─────────────────────────────────────
        # SysFont(None, size) usa a fonte padrão do sistema — zero assets,
        # zero I/O após __init__. None = fonte padrão do pygame/OS.
        self._fontes: dict[str, pygame.font.Font] = {
            "vidas":  pygame.font.SysFont(None, TAMANHO_FONTE_VIDAS),
            "fase":   pygame.font.SysFont(None, TAMANHO_FONTE_FASE),
            "score":  pygame.font.SysFont(None, TAMANHO_FONTE_SCORE),
            "larvas": pygame.font.SysFont(None, TAMANHO_FONTE_LARVAS),
            "cp":     pygame.font.SysFont(None, TAMANHO_FONTE_CP),
            "debug":  pygame.font.SysFont(None, TAMANHO_FONTE_DEBUG),
        }

        # ── Surface do painel de debug (SRCALPHA para semi-transparência)
        # Recriada se a resolução mudar — para o Vertical Slice, tamanho
        # fixo é suficiente.
        self._surf_debug: pygame.Surface = pygame.Surface(
            (config.SCREEN_WIDTH, 22), pygame.SRCALPHA
        )
        self._surf_debug.fill(COR_DEBUG_FUNDO)

    # ------------------------------------------------------------------
    # PONTO DE ENTRADA PÚBLICO
    # ------------------------------------------------------------------

    def draw(self, screen: pygame.Surface, dados: HudData) -> None:
        """
        Renderiza a HUD completa na Surface fornecida.

        Parâmetros
        ──────────
        screen : Surface de destino (normalmente a tela principal).
                 A HUD desenha em screen-space — nenhuma transformação
                 de câmera é aplicada.
        dados  : snapshot de dados do frame atual (HudData).

        Ordem de desenho (back-to-front dentro da HUD):
          1. Vidas          (canto superior esquerdo)
          2. Fase           (centro superior)
          3. Score          (canto superior direito)
          4. Barra larvas   (esquerda, linha 2)
          5. Contagem larvas(esquerda, linha 2 + offset)
          6. Checkpoint     (centro, linha 3 — somente se ativo)
          7. Debug          (fundo semi-opaco + texto — somente se DEBUG_HUD)
        """
        self._desenhar_vidas(screen, dados)
        self._desenhar_fase(screen, dados)
        self._desenhar_score(screen, dados)
        self._desenhar_larvas(screen, dados)
        self._desenhar_checkpoint(screen, dados)
        self._desenhar_cauda(screen, dados)

        if DEBUG_HUD:
            self._desenhar_debug(screen, dados)

    # ------------------------------------------------------------------
    # ETAPA 1 — Fase atual
    # ------------------------------------------------------------------

    def _desenhar_fase(
        self, screen: pygame.Surface, dados: HudData
    ) -> None:
        """
        Exibe "FASE  N / T" centralizado no topo da tela.

        Por que dois espaços entre "FASE" e o número?
        ───────────────────────────────────────────────
        Fonte monospace: dois espaços criam respiro visual entre o label
        e o valor sem precisar de dois render() separados.
        """
        texto = f"FASE  {dados.fase_atual} / {dados.total_fases}"
        self._texto(
            screen,
            "fase", texto, COR_FASE,
            x=config.SCREEN_WIDTH // 2,
            y=LINHA_1_Y,
            ancora="midtop",
        )

    # ------------------------------------------------------------------
    # ETAPA 2 — Moedas / Larvas
    # ------------------------------------------------------------------

    def _desenhar_larvas(
        self, screen: pygame.Surface, dados: HudData
    ) -> None:
        """
        Exibe barra de progresso e contagem de larvas coletadas.

        Layout (abaixo das vidas, canto esquerdo):
            [▓▓▓▓░░░░]  Larvas: 5/8

        A barra é um retângulo de fundo (trilho) com um retângulo de
        preenchimento proporcional sobre ele. border_radius suaviza
        as extremidades sem custo significativo.

        Casos especiais
        ───────────────
        • moedas_total == 0 → não renderiza (evita divisão por zero e
          a barra vazia aparecendo em fases sem larvas).
        """
        coletadas = dados.moedas_total - dados.moedas_restantes
        bx = PAD
        by = LINHA_2_Y

        # Trilho (fundo cinza)
        pygame.draw.rect(
            screen, COR_BARRA_FUNDO,
            (bx, by, BARRA_W, BARRA_H),
            border_radius=BARRA_RAIO,
        )

        # Preenchimento proporcional
        if dados.moedas_total > 0 and coletadas > 0:
            largura_cheia = int(BARRA_W * coletadas / dados.moedas_total)
            pygame.draw.rect(
                screen, COR_BARRA_LARVAS,
                (bx, by, largura_cheia, BARRA_H),
                border_radius=BARRA_RAIO,
            )

        # Texto de contagem logo abaixo da barra
        if dados.moedas_total > 0:
            self._texto(
                screen,
                "larvas", f"Larvas: {coletadas}/{dados.moedas_total}",
                COR_LARVAS_TEXTO,
                x=bx, y=by + BARRA_H + ESPACO_V,
                ancora="topleft",
            )

    # ------------------------------------------------------------------
    # ETAPA 3 — Vidas
    # ------------------------------------------------------------------

    def _desenhar_vidas(
        self, screen: pygame.Surface, dados: HudData
    ) -> None:
        """
        Exibe corações cheios (♥) e vazios (♡) no canto superior esquerdo.

        Dois render() separados permitem cores diferentes para cheios e
        vazios sem concatenar strings de cores misturadas.

        Corações cheios primeiro, vazios na mesma linha imediatamente
        à direita — o jogador lê o estado de saúde da esquerda para a
        direita, na ordem decrescente de urgência.
        """
        fonte = self._fontes["vidas"]
        x = PAD
        y = LINHA_1_Y

        # ── Corações cheios ───────────────────────────────────────────
        if dados.vidas > 0:
            surf_cheios = fonte.render(
                "♥ " * dados.vidas, True, COR_VIDAS_CHEIAS
            )
            sombra = fonte.render(
                "♥ " * dados.vidas, True, COR_SOMBRA
            )
            screen.blit(sombra, (x + 2, y + 2))
            screen.blit(surf_cheios, (x, y))
            largura_cheios = surf_cheios.get_width()
        else:
            largura_cheios = 0

        # ── Corações vazios ───────────────────────────────────────────
        vazios = dados.vidas_max - dados.vidas
        if vazios > 0:
            surf_vazios = fonte.render(
                "♡ " * vazios, True, COR_VIDAS_VAZIAS
            )
            screen.blit(surf_vazios, (x + largura_cheios, y))

    # ------------------------------------------------------------------
    # ETAPA 4 — Checkpoint
    # ------------------------------------------------------------------

    def _desenhar_checkpoint(
        self, screen: pygame.Surface, dados: HudData
    ) -> None:
        """
        Exibe "✔ Checkpoint Ativo" centralizado abaixo das larvas.

        Renderizado APENAS quando checkpoint_ativo=True — discreto por
        design. O jogador vê a confirmação sem ruído visual constante.

        Posicionado no centro da tela para que não sobreponha nem as
        vidas (esquerda) nem o score (direita).
        """
        if not dados.checkpoint_ativo:
            return

        self._texto(
            screen,
            "cp", "✔  Checkpoint Ativo",
            COR_CHECKPOINT,
            x=config.SCREEN_WIDTH // 2,
            y=LINHA_CP_Y,
            ancora="midtop",
        )

    # ------------------------------------------------------------------
    # ETAPA 3 (continuação) — Score
    # ------------------------------------------------------------------

    def _desenhar_cauda(
        self, screen: pygame.Surface, dados: HudData
    ) -> None:
        """
        Indicador de autotomia — sempre visível, muda de cor ao perder a cauda.

        Layout: canto inferior esquerdo da faixa de status, abaixo do checkpoint.

        Com cauda   →  🦎 Cauda: ✓   (verde)
        Sem cauda   →  🦎 Cauda: ✗   (vermelho)

        Por que sempre visível (ao contrário do checkpoint)?
        ──────────────────────────────────────────────────────
        A cauda é a mecânica de identidade do personagem — o jogador
        deve ver o status a todo momento para calibrar o risco.
        O checkpoint é informação contextual; a cauda é estado vital.
        """
        cor   = COR_CAUDA_OK if dados.tem_cauda else COR_CAUDA_PERDIDA
        icone = "✓" if dados.tem_cauda else "✗"
        self._texto(
            screen,
            "cp",   # reutiliza a fonte de checkpoint — mesmo tamanho
            f"Cauda: {icone}",
            cor,
            x=PAD, y=LINHA_CAUDA_Y,
            ancora="topleft",
        )

    def _desenhar_score(
        self, screen: pygame.Surface, dados: HudData
    ) -> None:
        """Score no canto superior direito, alinhado com vidas e fase."""
        self._texto(
            screen,
            "score", f"Score: {dados.score}",
            COR_SCORE,
            x=config.SCREEN_WIDTH - PAD,
            y=LINHA_1_Y,
            ancora="topright",
        )

    # ------------------------------------------------------------------
    # ETAPA 5 — Painel de Debug
    # ------------------------------------------------------------------

    def _desenhar_debug(
        self, screen: pygame.Surface, dados: HudData
    ) -> None:
        """
        Painel de debug — visível apenas quando DEBUG_HUD = True.

        Exibe em uma única linha compacta:
            FPS | X | Y | Vx | Vy | Estado

        Layout
        ───────
        Fundo semi-opaco (SRCALPHA 180/255) sobre toda a largura da tela
        na linha LINHA_DEBUG_Y. Texto verde terminal sobre fundo escuro
        garante legibilidade sem cobrir o gameplay.

        Por que uma linha só e não múltiplas?
        ──────────────────────────────────────
        Durante gameplay rápido (plataformas, pulos), o dev precisa de
        leitura instantânea — uma linha permite varredura sem mover os
        olhos. Valores críticos (posição, velocidade) ficam juntos.

        Campos exibidos
        ────────────────
        FPS      : frames por segundo reais (medido pelo clock do Game)
        X / Y    : posição world-space do player em pixels inteiros
        Vx / Vy  : velocidade em px/s (inteiros para leitura rápida)
        Estado   : nome do GameState atual (ex: "GameState.JOGANDO")
        """
        # Fundo semi-opaco
        screen.blit(self._surf_debug, (0, LINHA_DEBUG_Y))

        linha = (
            f"FPS:{dados.fps:04.1f}"
            f"  X:{int(dados.player_x):>5}"
            f"  Y:{int(dados.player_y):>4}"
            f"  Vx:{int(dados.vel_x):>5}"
            f"  Vy:{int(dados.vel_y):>5}"
            f"  {dados.estado_jogo}"
        )
        self._texto(
            screen,
            "debug", linha, COR_DEBUG_TEXTO,
            x=PAD, y=LINHA_DEBUG_Y + 3,
            ancora="topleft",
            sombra=False,   # sombra desativa: fundo já é escuro
        )

    # ------------------------------------------------------------------
    # UTILITÁRIO INTERNO
    # ------------------------------------------------------------------

    def _texto(
        self,
        screen:  pygame.Surface,
        chave:   str,
        texto:   str,
        cor:     tuple,
        x:       int,
        y:       int,
        ancora:  str   = "topleft",
        sombra:  bool  = True,
    ) -> None:
        """
        Renderiza texto com sombra opcional usando a fonte da chave.

        Parâmetros
        ──────────
        screen : Surface de destino
        chave  : chave em self._fontes (ex: "vidas", "fase")
        texto  : string a renderizar
        cor    : cor principal (R, G, B)
        x, y   : coordenadas de ancoragem em screen-space
        ancora : atributo de pygame.Rect para alinhamento
                 ("topleft", "midtop", "topright", "midleft" …)
        sombra : se True, renderiza uma cópia preta deslocada 2px antes
                 do texto principal — garante legibilidade em qualquer fundo

        Por que font.render() a cada chamada e não cache de Surface?
        ─────────────────────────────────────────────────────────────
        Os textos da HUD mudam frequentemente (score, vidas, FPS) e a
        maioria muda pelo menos uma vez por segundo. Manter um cache com
        invalidação por valor seria mais código que o ganho de performance
        — font.render() de string curta leva < 0.1ms em hardware moderno.
        """
        fonte = self._fontes[chave]
        surf  = fonte.render(texto, True, cor)
        rect  = surf.get_rect(**{ancora: (x, y)})

        if sombra:
            surf_sombra = fonte.render(texto, True, COR_SOMBRA)
            screen.blit(surf_sombra, rect.move(2, 2))

        screen.blit(surf, rect)
