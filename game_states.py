"""
game_states.py
══════════════
Enum canônico dos estados globais da FSM do jogo.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RESPONSABILIDADE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Este módulo define APENAS os estados possíveis da máquina de estados
do jogo. Ele não contém lógica de transição, não importa pygame,
não importa config e não depende de nenhum outro módulo do projeto.

Isso garante:
  • zero risco de importação circular
  • testável isoladamente (unittest sem pygame)
  • um único lugar canônico para adicionar novos estados

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COMO USAR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    from game_states import GameState

    # Comparação
    if self.estado == GameState.JOGANDO:
        ...

    # Atribuição
    self.estado = GameState.MENU

    # Guard de update
    if self.estado is not GameState.JOGANDO:
        return

    # Switch-style (Python 3.10+, mas match/case não é obrigatório)
    if self.estado == GameState.MENU:    ...
    elif self.estado == GameState.PAUSADO: ...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DIAGRAMA DA FSM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

                        ┌──────────────────────────────────────┐
                        │              PAUSADO                 │
                        │   (futuro — congela física, exibe   │
                        │    painel, permite retomar ou sair) │
                        └─────────────┬────────────────────────┘
                          P (pausa)   │  P (retoma)
                                      │
    ┌──────────┐  ESPAÇO  ┌───────────▼──┐  morte    ┌───────────┐
    │   MENU   │─────────►│   JOGANDO    │──────────►│ GAME_OVER │
    └──────────┘          └──────────────┘           └─────┬─────┘
         ▲                  │           │               R   │  M
         │    _avancar_fase │           │saida          ▼   │
         │   ┌──────────────┘           │         ┌──────┐  │
         │   │ TRANSICAO_FASE           │         │reset │  │
         │   │ (futuro — efeito visual  │         │jogo  │  │
         │   │  entre fases, corte ou  │         └──────┘  │
         │   │  fade, depois JOGANDO)  │                   │
         │   └──────────────►          │                   │
         │                             ▼                   │
         │                       ┌──────────┐              │
         └──────────M────────────│  VITORIA │◄─────────────┘
                                 └──────────┘

Legenda:
  ESPAÇO       = tecla Space no MENU inicia o jogo
  R            = tecla R em GAME_OVER/VITORIA reinicia
  M            = tecla M em GAME_OVER/VITORIA vai ao menu
  P            = tecla P (futuro) pausa/retoma em JOGANDO
  _avancar_fase= conclusão de fase intermediária
  morte        = vidas = 0
  saida        = jogador toca SaidaFase na última fase

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ESTADOS E SUAS RESPONSABILIDADES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  MENU
    Sistema(s) ativos:  nenhum (física congelada)
    Renderização:       _draw_menu()
    Input:              SPACE → JOGANDO

  JOGANDO
    Sistema(s) ativos:  player, inimigos, câmera, partículas,
                        checkpoints, saída de fase
    Renderização:       _draw_jogo() + _draw_hud()
    Input:              delegado ao Player (pulo, movimento)
                        P → PAUSADO (futuro)

  PAUSADO  ⟨futuro⟩
    Sistema(s) ativos:  nenhum (congela update() inteiro)
    Renderização:       _draw_jogo() congelado + painel de pausa
    Input:              P → retoma JOGANDO
                        M → MENU
    Nota: estado criado agora para que _ir_para_pausado() possa
    ser adicionado sem alterar handle_events() novamente.

  TRANSICAO_FASE  ⟨futuro⟩
    Sistema(s) ativos:  nenhum durante o efeito visual
    Renderização:       efeito de corte/fade entre fases
    Input:              bloqueado durante a transição
    Nota: _avancar_fase() poderá transitar para este estado
    antes de construir o novo nível — zero retrabalho no site
    de chamada quando o efeito for implementado.

  GAME_OVER
    Sistema(s) ativos:  nenhum (física congelada)
    Renderização:       _draw_jogo() congelado + overlay + painel
    Input:              R → reinicia / M → menu

  VITORIA
    Sistema(s) ativos:  nenhum (física congelada)
    Renderização:       _draw_jogo() congelado + overlay + painel
    Input:              R → reinicia / M → menu
"""

from __future__ import annotations
from enum import Enum, auto


class GameState(Enum):
    """
    Estados possíveis da máquina de estados finita do jogo.

    Por que Enum e não constantes de string ou int?
    ────────────────────────────────────────────────
    • Enum.auto() garante unicidade: dois estados nunca têm o mesmo valor
      por acidente humano (ao contrário de "MENU" vs "menu").
    • Comparação com `is` (identidade de objeto) em vez de `==` (valor
      de string) — mais rápido e impossível de errar por typo.
    • repr() legível em tracebacks: <GameState.JOGANDO> em vez de 2.
    • O type-checker infere o tipo correto em anotações: `GameState`,
      não `str` ou `int`.
    • Adicionar um estado novo é uma linha — sem risco de colisão.

    Convenção de nomeação
    ─────────────────────
    SNAKE_UPPER_CASE por convenção de Enum em Python (PEP 8).
    Nomes em português para consistência com o restante do projeto.
    """

    MENU            = auto()   # tela inicial — física congelada
    JOGANDO         = auto()   # gameplay ativo — todos os sistemas ligados
    PAUSADO         = auto()   # ⟨futuro⟩ pausa — física congelada, retomável
    TRANSICAO_FASE  = auto()   # ⟨futuro⟩ efeito visual entre fases
    GAME_OVER       = auto()   # derrota — física congelada, overlay exibido
    VITORIA         = auto()   # vitória — física congelada, jingle, overlay
