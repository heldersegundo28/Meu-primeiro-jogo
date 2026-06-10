"""
menu_pause.py
═════════════
Menu de Pausa — módulo autônomo e desacoplado.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RESPONSABILIDADE ÚNICA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Este módulo desenha o overlay de pausa, processa navegação e retorna
a ação escolhida. Ele NUNCA:
  • modifica estado do Game, Player ou câmera
  • recarrega fases ou salva arquivos
  • importa main, player, config, camera, save_manager

O canal de saída é obter_acao() → OpcaoPause | None.
O Game lê a ação e executa a transição.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FLUXO DE AÇÕES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  OpcaoPause.RETORNAR       → Game: GameState.JOGANDO
  OpcaoPause.REINICIAR_FASE → Game: _resetar_jogo(reiniciar_campanha=False)
  OpcaoPause.MENU_PRINCIPAL → Game: _ir_para_menu()
  OpcaoPause.SAIR           → Game: _salvar_jogo() + running=False

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RENDERIZAÇÃO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

O Game chama _draw_jogo() para desenhar o mundo congelado e depois
menu_pause.draw(surface) para sobrepor o overlay.

O overlay é uma Surface SRCALPHA semi-opaca pré-renderizada — zero
alocação por frame.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DEPENDÊNCIAS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  pygame  — Surface, draw, font, SRCALPHA
  enum    — OpcaoPause

NÃO importa: config, main, player, sprites, hud, save_manager, camera.
"""

from __future__ import annotations

import math
from enum    import Enum, auto
from typing  import Callable

import pygame


# ══════════════════════════════════════════════════════════════════════
# AÇÕES DO MENU DE PAUSA
# ══════════════════════════════════════════════════════════════════════

class OpcaoPause(Enum):
    """
    Ações que o MenuPause pode retornar ao Game.

    Extensível sem if/elif:
      Adicionar membro aqui + handler no Game.
    """
    RETORNAR        = auto()   # volta ao jogo sem perder progresso
    REINICIAR_FASE  = auto()   # recarrega a fase do início (ou checkpoint)
    MENU_PRINCIPAL  = auto()   # vai ao menu sem fechar o jogo
    SAIR            = auto()   # salva e encerra
    # Futuras opções:
    # CONFIGURACOES = auto()
    # ACESSIBILIDADE = auto()


# ══════════════════════════════════════════════════════════════════════
# MENU DE PAUSA
# ══════════════════════════════════════════════════════════════════════

class MenuPause:
    """
    Menu de pausa sobreposto ao jogo congelado.

    Instanciar uma vez em Game.__init__(). reset() é chamado ao entrar
    em PAUSADO para que a seleção comece em RETORNAR.

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    INTERFACE PÚBLICA
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

      reset()                — seleção volta para RETORNAR
      processar_evento(event)— alimenta um pygame.Event
      update(dt)             — anima seta pulsante
      draw(surface)          — renderiza overlay + painel
      obter_acao()           — retorna OpcaoPause | None e limpa
    """

    # ── Layout ───────────────────────────────────────────────────────
    TAM_TITULO:   int   = 44
    TAM_OPCAO:    int   = 30
    TAM_DICA:     int   = 17

    FRAC_Y_TITULO: float = 0.34   # Y do "PAUSADO" como fração da tela
    FRAC_Y_OPCOES: float = 0.48
    ESPACO_OPCOES: int   = 46     # px entre opções

    # Painel (caixa ao redor das opções)
    PAINEL_PADDING_X: int = 60
    PAINEL_PADDING_Y: int = 28

    # ── Cores ────────────────────────────────────────────────────────
    COR_OVERLAY:    tuple = (0, 0, 0, 155)        # preto semi-opaco
    COR_PAINEL_BG:  tuple = (18, 24, 48, 230)     # azul-noite (RGBA)
    COR_PAINEL_BRD: tuple = (80, 120, 200, 255)   # borda azul
    COR_TITULO:     tuple = (180, 210, 255)
    COR_OPCAO:      tuple = (210, 210, 210)
    COR_SELECIONADA:tuple = (255, 255, 100)
    COR_SETA:       tuple = (255, 200,  50)
    COR_DICA:       tuple = (100, 120, 150)

    # ── Animação ─────────────────────────────────────────────────────
    SETA_ANIM_FREQ: float = 3.0   # Hz da seta pulsante

    def __init__(
        self,
        largura:    int,
        altura:     int,
        on_move:    Callable | None = None,
        on_confirm: Callable | None = None,
    ) -> None:
        self._larg       = largura
        self._alt        = altura
        self._on_move    = on_move
        self._on_confirm = on_confirm

        # Fontes
        self._f_titulo = pygame.font.SysFont(None, self.TAM_TITULO)
        self._f_opcao  = pygame.font.SysFont(None, self.TAM_OPCAO)
        self._f_dica   = pygame.font.SysFont(None, self.TAM_DICA)

        # Estado interno
        self._opcoes: list[tuple[OpcaoPause, str]] = [
            (OpcaoPause.RETORNAR,       "Retornar ao Jogo"),
            (OpcaoPause.REINICIAR_FASE, "Reiniciar Fase"),
            (OpcaoPause.MENU_PRINCIPAL, "Menu Principal"),
            (OpcaoPause.SAIR,           "Sair do Jogo"),
        ]
        self._idx:   int             = 0
        self._acao:  OpcaoPause | None = None
        self._tempo: float           = 0.0

        # Overlay pré-renderizado (SRCALPHA) — zero alocação por frame
        self._surf_overlay: pygame.Surface = pygame.Surface(
            (largura, altura), pygame.SRCALPHA
        )
        self._surf_overlay.fill(self.COR_OVERLAY)

        # Painel pré-renderizado — recalculado em reset() se necessário
        self._surf_painel: pygame.Surface | None = None
        self._painel_rect: pygame.Rect | None    = None
        self._construir_painel()

    # ------------------------------------------------------------------
    # INTERFACE PÚBLICA
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Volta seleção para RETORNAR. Chamado ao entrar em PAUSADO."""
        self._idx   = 0
        self._acao  = None
        self._tempo = 0.0

    def processar_evento(self, event: pygame.event.Event) -> None:
        """
        Processa um pygame.Event de navegação.

        ESC → RETORNAR (atalho para fechar pausa rapidamente)
        ↑/W  → mover para cima
        ↓/S  → mover para baixo
        ENTER → confirmar
        """
        if event.type != pygame.KEYDOWN:
            return

        if event.key == pygame.K_ESCAPE:
            # ESC no pause = retornar ao jogo
            self._acao = OpcaoPause.RETORNAR
            if self._on_confirm:
                try: self._on_confirm()
                except Exception: pass

        elif event.key in (pygame.K_UP, pygame.K_w):
            self._mover(-1)

        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self._mover(+1)

        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self._confirmar()

    def update(self, dt: float) -> None:
        """Acumula tempo para a animação da seta pulsante."""
        self._tempo += dt

    def draw(self, surface: pygame.Surface) -> None:
        """
        Renderiza o overlay + painel de pausa sobre a Surface.

        Deve ser chamado APÓS _draw_jogo() — o jogo congelado é
        o fundo visual do overlay.

        Ordem:
          1. Overlay semi-opaco (escurece o jogo)
          2. Painel (caixa com borda)
          3. Título "PAUSADO"
          4. Opções com seta indicadora
          5. Dica de teclado
        """
        # 1. Overlay
        surface.blit(self._surf_overlay, (0, 0))

        # 2. Painel
        if self._surf_painel and self._painel_rect:
            surface.blit(self._surf_painel, self._painel_rect)

        cx = self._larg // 2

        # 3. Título
        cy_titulo = int(self._alt * self.FRAC_Y_TITULO)
        surf_t = self._f_titulo.render("PAUSADO", True, self.COR_TITULO)
        rt = surf_t.get_rect(center=(cx, cy_titulo))
        surface.blit(surf_t, rt)

        # Separador fino abaixo do título
        linha_y = cy_titulo + 30
        pygame.draw.line(surface, self.COR_PAINEL_BRD,
                         (cx - 80, linha_y), (cx + 80, linha_y), 1)

        # 4. Opções
        seta_off = int(5 * math.sin(self._tempo * self.SETA_ANIM_FREQ * math.tau))
        y_ini    = int(self._alt * self.FRAC_Y_OPCOES)

        for i, (_, label) in enumerate(self._opcoes):
            y          = y_ini + i * self.ESPACO_OPCOES
            selecionada = (i == self._idx)
            cor        = self.COR_SELECIONADA if selecionada else self.COR_OPCAO

            surf_l = self._f_opcao.render(label, True, cor)
            rl     = surf_l.get_rect(center=(cx, y))
            surface.blit(surf_l, rl)

            if selecionada:
                surf_seta = self._f_opcao.render("►", True, self.COR_SETA)
                x_seta    = rl.left - surf_seta.get_width() - 10 + seta_off
                surface.blit(surf_seta, (x_seta, rl.y))

        # 5. Dica
        dica  = "↑ ↓  Navegar       ENTER  Selecionar       ESC  Retornar"
        surf_d = self._f_dica.render(dica, True, self.COR_DICA)
        rd     = surf_d.get_rect(center=(cx, self._alt - 24))
        surface.blit(surf_d, rd)

    def obter_acao(self) -> OpcaoPause | None:
        """Retorna e limpa a ação pendente (consumo único)."""
        acao, self._acao = self._acao, None
        return acao

    # ------------------------------------------------------------------
    # INTERNOS
    # ------------------------------------------------------------------

    def _mover(self, direcao: int) -> None:
        n         = len(self._opcoes)
        self._idx = (self._idx + direcao) % n
        if self._on_move:
            try: self._on_move()
            except Exception: pass

    def _confirmar(self) -> None:
        if not self._opcoes:
            return
        self._acao = self._opcoes[self._idx][0]
        if self._on_confirm:
            try: self._on_confirm()
            except Exception: pass

    def _construir_painel(self) -> None:
        """
        Pré-renderiza a caixa de fundo do painel (SRCALPHA).

        Dimensões calculadas para cobrir o bloco de opções com padding.
        Borda azul de 2px sobre fundo azul-noite semi-opaco.
        """
        cx    = self._larg // 2
        y_ini = int(self._alt * self.FRAC_Y_TITULO) - self.PAINEL_PADDING_Y
        y_fim = (int(self._alt * self.FRAC_Y_OPCOES)
                 + len(self._opcoes) * self.ESPACO_OPCOES
                 + self.PAINEL_PADDING_Y)

        # Largura estimada pela opção mais longa
        fonte_tmp = pygame.font.SysFont(None, self.TAM_OPCAO)
        max_w     = max(
            fonte_tmp.size(label)[0] for _, label in self._opcoes
        )
        pw  = max_w + self.PAINEL_PADDING_X * 2 + 40  # +40 para a seta
        ph  = y_fim - y_ini

        surf = pygame.Surface((pw, ph), pygame.SRCALPHA)
        surf.fill(self.COR_PAINEL_BG)
        pygame.draw.rect(surf, self.COR_PAINEL_BRD, surf.get_rect(), 2)

        self._surf_painel = surf
        self._painel_rect = surf.get_rect(center=(cx, (y_ini + y_fim) // 2))
