"""
menu_principal.py
═════════════════
Menu Principal — módulo autônomo e desacoplado.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RESPONSABILIDADE ÚNICA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Este módulo desenha o menu, processa navegação e retorna a ação
escolhida. Ele NUNCA:
  • modifica estado do Game
  • carrega fases
  • acessa player, câmera ou qualquer sistema de gameplay
  • salva ou carrega arquivos (delega ao SaveManager via flag)

O canal de saída é obter_acao() → OpcaoMenu | None.
O Game lê essa ação e executa a transição adequada.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FLUXO DE AÇÕES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  OpcaoMenu.NOVO_JOGO  → Game: reset save + fase 1 + spawn inicial
  OpcaoMenu.CONTINUAR  → Game: carrega save + fase salva + checkpoint
  OpcaoMenu.SAIR       → Game: salva e encerra

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PONTOS DE EXTENSÃO FUTURA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Para adicionar "Configurações", "Créditos", "Bestiário":
  1. Adicionar membro ao Enum OpcaoMenu
  2. Adicionar à lista _OPCOES_DISPONIVEIS (condicionalmente)
  3. Adicionar ao handler no Game

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INTEGRAÇÃO DE ÁUDIO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Dois callbacks opcionais injetados no __init__:
  on_move    : callable — chamado ao mover seleção (ex: tocar SFX)
  on_confirm : callable — chamado ao confirmar opção

O módulo não importa o sistema de áudio diretamente — zero acoplamento.
Para ativar: MenuPrincipal(on_move=lambda: game._tocar_som("menu_move"))

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DEPENDÊNCIAS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  pygame  — Surface, draw, font
  enum    — OpcaoMenu

NÃO importa: config, main, player, sprites, hud, save_manager, enemies.
Constantes de layout e cor são atributos de classe.
"""

from __future__ import annotations

import math
from enum     import Enum, auto
from typing   import Callable

import pygame


# ══════════════════════════════════════════════════════════════════════
# AÇÕES DO MENU
# ══════════════════════════════════════════════════════════════════════

class OpcaoMenu(Enum):
    """
    Ações que o Menu pode retornar ao Game.

    Por que Enum e não strings?
    ───────────────────────────
    • Typos são detectados pelo type-checker
    • Adicionar nova opção = uma linha
    • repr() legível em debug: <OpcaoMenu.NOVO_JOGO>
    """
    NOVO_JOGO = auto()
    CONTINUAR = auto()
    SAIR      = auto()
    # Futuras opções:
    # CONFIGURACOES = auto()
    # CREDITOS      = auto()
    # BESTIARIO     = auto()


# ══════════════════════════════════════════════════════════════════════
# MENU PRINCIPAL
# ══════════════════════════════════════════════════════════════════════

class MenuPrincipal:
    """
    Menu principal navegável com teclado.

    Instanciar uma vez em Game.__init__() e reutilizar — o estado
    (seleção, ação pendente) é resetado por reset() quando o menu
    é exibido novamente.

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    INTERFACE PÚBLICA
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

      reset(tem_save)           — prepara o menu para exibição
      processar_evento(event)   — alimenta um pygame.Event
      update(dt)                — atualiza efeitos visuais
      draw(surface)             — renderiza na Surface fornecida
      obter_acao()              — retorna OpcaoMenu | None e limpa
    """

    # ── Título ────────────────────────────────────────────────────────
    TITULO:       str = "CALANGO FILHOTE"
    SUBTITULO:    str = "um jogo de plataforma"

    # ── Tamanhos de fonte ─────────────────────────────────────────────
    TAM_TITULO:   int = 72
    TAM_SUBTITULO:int = 22
    TAM_OPCAO:    int = 32
    TAM_DICA:     int = 18
    TAM_DESABILI: int = 26

    # ── Espaçamentos ─────────────────────────────────────────────────
    # Y base das opções (fração da altura da tela)
    FRAC_Y_OPCOES:  float = 0.54
    ESPACO_OPCOES:  int   = 52    # px entre opções

    # ── Cores ────────────────────────────────────────────────────────
    COR_FUNDO:      tuple = ( 12,  14,  28)   # azul-noite profundo
    COR_FUNDO2:     tuple = ( 20,  35,  60)   # gradiente inferior
    COR_TITULO:     tuple = (255, 200,  50)   # amarelo dourado
    COR_TITULO_SOMBRA: tuple = (120, 80, 0)
    COR_SUBTITULO:  tuple = (140, 160, 200)
    COR_OPCAO:      tuple = (220, 220, 220)   # branco-suave
    COR_SELECIONADA:tuple = (255, 255, 100)   # amarelo brilhante
    COR_SETA:       tuple = (255, 200,  50)
    COR_DESABILI:   tuple = ( 80,  80,  90)   # cinza escuro
    COR_DICA:       tuple = (100, 120, 150)
    COR_ESTRELA:    tuple = (200, 200, 255)

    # ── Animação da seta ─────────────────────────────────────────────
    SETA_ANIM_FREQ: float = 3.0   # Hz de oscilação da seta

    def __init__(
        self,
        largura:    int,
        altura:     int,
        on_move:    Callable | None = None,
        on_confirm: Callable | None = None,
    ) -> None:
        """
        Parâmetros
        ──────────
        largura, altura : resolução da tela em pixels
        on_move         : callback chamado ao mover seleção (SFX hook)
        on_confirm      : callback chamado ao confirmar opção (SFX hook)
        """
        self._larg:       int  = largura
        self._alt:        int  = altura
        self._on_move:    Callable | None = on_move
        self._on_confirm: Callable | None = on_confirm

        # ── Fontes pré-carregadas ─────────────────────────────────────
        self._f_titulo   = pygame.font.SysFont(None, self.TAM_TITULO)
        self._f_sub      = pygame.font.SysFont(None, self.TAM_SUBTITULO)
        self._f_opcao    = pygame.font.SysFont(None, self.TAM_OPCAO)
        self._f_desabili = pygame.font.SysFont(None, self.TAM_DESABILI)
        self._f_dica     = pygame.font.SysFont(None, self.TAM_DICA)

        # ── Estado de navegação ───────────────────────────────────────
        self._opcoes:     list[tuple[OpcaoMenu, str]] = []   # (enum, label)
        self._idx:        int            = 0
        self._acao:       OpcaoMenu | None = None
        self._tem_save:   bool           = False

        # ── Efeito visual: seta pulsante ──────────────────────────────
        self._tempo:      float = 0.0   # acumulado em update()

        # ── Background pré-renderizado ────────────────────────────────
        self._surf_bg: pygame.Surface = self._construir_fundo()

    # ------------------------------------------------------------------
    # INTERFACE PÚBLICA
    # ------------------------------------------------------------------

    def reset(self, tem_save: bool = False) -> None:
        """
        Prepara o menu para exibição.

        Deve ser chamado pelo Game toda vez que o estado transitar
        para GameState.MENU, para que a seleção comece em NOVO JOGO
        e o estado "Continuar" reflita a existência de save atual.

        Parâmetros
        ──────────
        tem_save : True se save_manager.exists() for True.
                   Determina se "Continuar" aparece habilitado.
        """
        self._tem_save = tem_save
        self._idx      = 0
        self._acao     = None
        self._tempo    = 0.0

        # Monta lista de opções disponíveis (com labels)
        self._opcoes = [
            (OpcaoMenu.NOVO_JOGO, "Novo Jogo"),
            (OpcaoMenu.CONTINUAR, "Continuar"),
            (OpcaoMenu.SAIR,      "Sair"),
        ]

    def processar_evento(self, event: pygame.event.Event) -> None:
        """
        Processa um pygame.Event e atualiza seleção ou ação.

        Teclas aceitas
        ──────────────
        ↑ / W       — mover seleção para cima
        ↓ / S       — mover seleção para baixo
        ENTER / KP_ENTER — confirmar opção selecionada
        ESC         — fechado pelo Game (não tratado aqui)

        Opções desabilitadas são puladas automaticamente na navegação.
        """
        if event.type != pygame.KEYDOWN:
            return

        if event.key in (pygame.K_UP, pygame.K_w):
            self._mover_selecao(-1)

        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self._mover_selecao(+1)

        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self._confirmar()

    def update(self, dt: float) -> None:
        """Acumula tempo para animação da seta pulsante."""
        self._tempo += dt

    def draw(self, surface: pygame.Surface) -> None:
        """
        Renderiza o menu completo na Surface fornecida.

        Ordem de renderização
        ─────────────────────
        1. Fundo gradiente pré-renderizado
        2. Estrelas decorativas (procedurais, posição fixa)
        3. Título + subtítulo
        4. Separador decorativo
        5. Opções (com indicador ► na selecionada)
        6. Dica de teclado na base
        """
        surface.blit(self._surf_bg, (0, 0))
        self._desenhar_estrelas(surface)
        self._desenhar_titulo(surface)
        self._desenhar_opcoes(surface)
        self._desenhar_dica(surface)

    def obter_acao(self) -> OpcaoMenu | None:
        """
        Retorna a ação pendente e a limpa (consumo único).

        Retorno
        ───────
        OpcaoMenu se o jogador confirmou uma opção neste frame.
        None se nenhuma ação foi tomada.

        O Game deve chamar isto a cada frame enquanto o menu estiver ativo.
        """
        acao, self._acao = self._acao, None
        return acao

    # ------------------------------------------------------------------
    # NAVEGAÇÃO INTERNA
    # ------------------------------------------------------------------

    def _mover_selecao(self, direcao: int) -> None:
        """
        Move a seleção ignorando opções desabilitadas.

        Itera até encontrar uma opção habilitada na direção solicitada,
        com wrap-around. Máximo de len(opcoes) iterações para evitar
        loop infinito se todas estiverem desabilitadas.
        """
        n = len(self._opcoes)
        for _ in range(n):
            self._idx = (self._idx + direcao) % n
            if self._esta_habilitada(self._idx):
                break

        if self._on_move:
            try:
                self._on_move()
            except Exception:
                pass   # callback falhou → ignora silenciosamente

    def _confirmar(self) -> None:
        """Registra a ação da opção selecionada se estiver habilitada."""
        if not self._opcoes:
            return
        opcao_enum, _ = self._opcoes[self._idx]
        if not self._esta_habilitada(self._idx):
            return

        self._acao = opcao_enum

        if self._on_confirm:
            try:
                self._on_confirm()
            except Exception:
                pass

    def _esta_habilitada(self, idx: int) -> bool:
        """
        True se a opção no índice dado pode ser selecionada.

        Regra atual:
          • CONTINUAR: desabilitada se não há save (self._tem_save=False)
          • demais: sempre habilitadas
        """
        if not self._opcoes:
            return False
        opcao_enum, _ = self._opcoes[idx]
        if opcao_enum is OpcaoMenu.CONTINUAR and not self._tem_save:
            return False
        return True

    # ------------------------------------------------------------------
    # RENDERIZAÇÃO
    # ------------------------------------------------------------------

    def _construir_fundo(self) -> pygame.Surface:
        """
        Gera o fundo do menu proceduralmente.

        Gradiente vertical de COR_FUNDO → COR_FUNDO2.
        Pré-renderizado no __init__ — zero custo por frame.
        """
        surf = pygame.Surface((self._larg, self._alt))
        r1, g1, b1 = self.COR_FUNDO
        r2, g2, b2 = self.COR_FUNDO2
        for y in range(self._alt):
            t   = y / self._alt
            cor = (
                int(r1 + (r2 - r1) * t),
                int(g1 + (g2 - g1) * t),
                int(b1 + (b2 - b1) * t),
            )
            pygame.draw.line(surf, cor, (0, y), (self._larg, y))
        return surf

    def _desenhar_estrelas(self, surface: pygame.Surface) -> None:
        """
        Pontos de luz decorativos — pseudo-aleatórios mas determinísticos.

        Posições calculadas com seed fixa (hash do índice) para que o
        menu seja sempre idêntico sem guardar estado extra.
        """
        for i in range(40):
            x = (i * 137 + 73)  % self._larg
            y = (i * 97  + 41)  % (self._alt // 2)
            r = 1 if i % 3 else 2
            # Pisca lentamente com fase diferente por estrela
            alpha = int(120 + 100 * math.sin(self._tempo * 1.2 + i * 0.7))
            alpha = max(60, min(220, alpha))
            cor   = (
                min(255, self.COR_ESTRELA[0]),
                min(255, self.COR_ESTRELA[1]),
                min(255, self.COR_ESTRELA[2] + i % 30),
            )
            # Estrelas pequenas: apenas ponto (sem Surface SRCALPHA por frame)
            pygame.draw.circle(surface, cor, (x, y), r)

    def _desenhar_titulo(self, surface: pygame.Surface) -> None:
        """Título principal + subtítulo + linha separadora."""
        cx = self._larg // 2
        cy_titulo = int(self._alt * 0.28)

        # Sombra do título
        sombra = self._f_titulo.render(self.TITULO, True, self.COR_TITULO_SOMBRA)
        r = sombra.get_rect(center=(cx + 3, cy_titulo + 3))
        surface.blit(sombra, r)

        # Título principal
        surf_t = self._f_titulo.render(self.TITULO, True, self.COR_TITULO)
        rt = surf_t.get_rect(center=(cx, cy_titulo))
        surface.blit(surf_t, rt)

        # Subtítulo
        surf_s = self._f_sub.render(self.SUBTITULO, True, self.COR_SUBTITULO)
        rs = surf_s.get_rect(center=(cx, cy_titulo + 50))
        surface.blit(surf_s, rs)

        # Separador decorativo
        linha_y = cy_titulo + 75
        pygame.draw.line(surface, self.COR_SETA,
                         (cx - 100, linha_y), (cx + 100, linha_y), 1)

    def _desenhar_opcoes(self, surface: pygame.Surface) -> None:
        """
        Renderiza cada opção com indicador ► na selecionada.

        Layout por opção:
          ►  [LABEL]     ← selecionada: cor brilhante + seta pulsante
             [LABEL]     ← normal: cor padrão
             [LABEL]     ← desabilitada: cinza + "(sem save)"
        """
        cx    = self._larg // 2
        y_ini = int(self._alt * self.FRAC_Y_OPCOES)

        # Offset da seta: senoidal para pulsar
        seta_off = int(5 * math.sin(self._tempo * self.SETA_ANIM_FREQ * math.tau))

        for i, (opcao_enum, label) in enumerate(self._opcoes):
            y = y_ini + i * self.ESPACO_OPCOES
            selecionada  = (i == self._idx)
            habilitada   = self._esta_habilitada(i)

            # ── Cor e fonte da opção ──────────────────────────────────
            if not habilitada:
                cor   = self.COR_DESABILI
                fonte = self._f_desabili
                texto = label + "  (sem save)"
            elif selecionada:
                cor   = self.COR_SELECIONADA
                fonte = self._f_opcao
                texto = label
            else:
                cor   = self.COR_OPCAO
                fonte = self._f_opcao
                texto = label

            surf_l = fonte.render(texto, True, cor)
            rl     = surf_l.get_rect(center=(cx, y))
            surface.blit(surf_l, rl)

            # ── Seta indicadora ───────────────────────────────────────
            if selecionada and habilitada:
                surf_seta = self._f_opcao.render("►", True, self.COR_SETA)
                x_seta    = rl.left - surf_seta.get_width() - 12 + seta_off
                surface.blit(surf_seta, (x_seta, rl.y))

    def _desenhar_dica(self, surface: pygame.Surface) -> None:
        """Dica de teclado na base da tela."""
        dica  = "↑ ↓  Navegar       ENTER  Selecionar       ESC  Sair"
        surf  = self._f_dica.render(dica, True, self.COR_DICA)
        rect  = surf.get_rect(center=(self._larg // 2, self._alt - 24))
        surface.blit(surf, rect)
