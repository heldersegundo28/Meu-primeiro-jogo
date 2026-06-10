"""
telemetry.py
════════════
Sistema de telemetria para playtest — coleta de dados em memória.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RESPONSABILIDADE ÚNICA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Este módulo APENAS observa eventos e acumula contadores.
Ele NUNCA:
  • modifica variáveis de jogo
  • chama métodos de transição de estado
  • lê estado de Player, Game, Câmera ou sprites diretamente
  • salva arquivos ou faz I/O (nesta etapa)
  • lança exceções que interrompam o loop principal

O canal de entrada são chamadas explícitas a métodos de evento
(registrar_pulo(), registrar_morte(), …). O canal de saída é
resumo_fase() — uma string de texto para o terminal.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ARQUITETURA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  EstatisticasFase   — contadores por nível (zerado a cada nova fase)
  EventoMorte        — posição e fase de cada morte (lista histórica)
  Telemetria         — singleton-por-instância; mantém histórico entre fases

  main.py instancia Telemetria uma vez em __init__() e chama os métodos
  de evento nos pontos já existentes do loop — sem alterar lógica.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DEPENDÊNCIAS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  time      — temporizador de fase (stdlib, zero pygame)
  dataclasses — estrutura de dados sem boilerplate
  typing    — anotações

NÃO importa: pygame, config, main, player, sprites, hud, game_states.
Zero risco de importação circular.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing      import List


# ══════════════════════════════════════════════════════════════════════
# CONTROLE DE DEBUG
# ══════════════════════════════════════════════════════════════════════

# True  → imprime eventos e resumos no terminal durante o playtest.
# False → opera em silêncio total (sem print, sem custo de I/O).
DEBUG_TELEMETRY: bool = False


# ══════════════════════════════════════════════════════════════════════
# ESTRUTURAS DE DADOS
# ══════════════════════════════════════════════════════════════════════

@dataclass
class EventoMorte:
    """
    Registro imutável de uma morte do jogador.

    Etapa 3 — Mapa de Mortes.

    Campos
    ──────
    fase  : número da fase em que a morte ocorreu (ex: 2)
    x     : posição world-space X do player no frame da morte (px)
    y     : posição world-space Y do player no frame da morte (px)
    tempo : segundos desde o início desta fase (float)

    Por que guardar o tempo além da posição?
    ─────────────────────────────────────────
    Mortes precoces (tempo < 10s) indicam dificuldade no início da fase.
    Mortes tardias (tempo > 60s) podem indicar fadiga ou obstáculo final.
    Esse dado não tem custo extra — já calculamos o tempo de fase.
    """
    fase:  int
    x:     float
    y:     float
    tempo: float   # segundos desde início da fase


@dataclass
class EstatisticasFase:
    """
    Contadores acumulados para uma única fase.

    Etapas 1 e 2.
    Zerado automaticamente por Telemetria.iniciar_fase().

    ── Etapa 1: Fase ─────────────────────────────────────────────────
    tempo_total_fase      : duração em segundos (calculada em finalizar_fase)
    mortes                : quantas vezes o jogador morreu nesta fase
    moedas_coletadas      : larvas pegadas nesta fase
    checkpoints_ativados  : checkpoints tocados pela primeira vez

    ── Etapa 2: Jogador ──────────────────────────────────────────────
    total_pulos           : pulos normais (inclui coyote, exclui wall jump)
    total_wall_jumps      : pulos executados a partir de parede
    total_escaladas       : vezes que o player aderiu a uma parede (edge)
    total_dano_recebido   : hits que decrementaram vidas (i-frames ignorados)

    Nota sobre total_escaladas
    ──────────────────────────
    Conta o número de vezes que o player *começou* a escalar (borda de
    escalando False→True). Não conta frames enquanto escala — o que
    importa para balanceamento é "quantas vezes usou a mecânica", não
    "por quantos frames ficou grudado".
    """
    # ── Etapa 1 ────────────────────────────────────────────────────────
    tempo_total_fase:     float = 0.0
    mortes:               int   = 0
    moedas_coletadas:     int   = 0
    checkpoints_ativados: int   = 0

    # ── Etapa 2 ────────────────────────────────────────────────────────
    total_pulos:          int   = 0
    total_wall_jumps:     int   = 0
    total_escaladas:      int   = 0
    total_dano_recebido:  int   = 0


# ══════════════════════════════════════════════════════════════════════
# TELEMETRIA
# ══════════════════════════════════════════════════════════════════════

class Telemetria:
    """
    Coletor de dados de playtest — observer puro, sem side-effects de jogo.

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    CICLO DE VIDA
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

      telemetria = Telemetria()          # uma vez em Game.__init__()

      telemetria.iniciar_fase(1)         # em _construir_nivel()
        ...
      telemetria.registrar_pulo()        # no frame que detecta pulou=True
      telemetria.registrar_morte(x, y)   # em _checar_colisao_inimigos()
      telemetria.registrar_checkpoint()  # em _checar_colisao_checkpoints()
      telemetria.registrar_moeda()       # na coleta de cada moeda
        ...
      telemetria.finalizar_fase(1)       # em _concluir_fase() ou _avancar_fase()

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    ESTADO INTERNO
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

      _fase_atual     : número da fase em progresso
      _stats          : EstatisticasFase da fase em andamento
      _t_inicio_fase  : timestamp (time.monotonic) do início da fase
      _escalando_prev : estado anterior de escalada (edge detector)
      historico       : lista de EstatisticasFase finalizadas (todas as fases)
      mortes          : lista de EventoMorte (toda a sessão)

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    SEGURANÇA DE CHAMADA
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    Todos os métodos de registro são protegidos por try/except genérico.
    Se um bug de integração passar um tipo errado ou chamar fora de ordem,
    a telemetria silencia o erro — o jogo nunca trava por causa de coleta
    de dados. Em DEBUG_TELEMETRY=True o erro é impresso para diagnóstico.
    """

    def __init__(self) -> None:
        self._fase_atual:    int               = 0
        self._stats:         EstatisticasFase  = EstatisticasFase()
        self._t_inicio_fase: float             = 0.0
        self._escalando_prev: bool             = False   # edge-detector de escalada

        # Histórico imutável — uma entrada por fase finalizada
        self.historico: List[EstatisticasFase] = []
        # Mapa de mortes — toda a sessão
        self.mortes:    List[EventoMorte]      = []

    # ------------------------------------------------------------------
    # CONTROLE DE FASE
    # ------------------------------------------------------------------

    def iniciar_fase(self, numero_fase: int) -> None:
        """
        Inicia a coleta de uma nova fase.

        Chamado em: Game._construir_nivel()

        Reseta os contadores da fase atual e registra o timestamp de início.
        O histórico e o mapa de mortes NÃO são zerados — acumulam toda a sessão.

        Parâmetros
        ──────────
        numero_fase : número da fase que está começando (ex: 1, 2, 3)
        """
        try:
            self._fase_atual    = numero_fase
            self._stats         = EstatisticasFase()
            self._t_inicio_fase = time.monotonic()
            self._escalando_prev = False

            if DEBUG_TELEMETRY:
                print(f"[TELEMETRIA] ── Fase {numero_fase} iniciada ──────────")
        except Exception as e:
            if DEBUG_TELEMETRY:
                print(f"[TELEMETRIA][ERRO] iniciar_fase: {e}")

    def finalizar_fase(self, numero_fase: int) -> None:
        """
        Fecha a coleta da fase e imprime o resumo (Etapa 4).

        Chamado em: Game._concluir_fase() — antes de _avancar_fase() ou
        _ir_para_vitoria().

        Calcula tempo_total_fase, arquiva EstatisticasFase no histórico
        e exibe o resumo se DEBUG_TELEMETRY=True.

        Parâmetros
        ──────────
        numero_fase : número da fase sendo finalizada (sanity check)
        """
        try:
            self._stats.tempo_total_fase = time.monotonic() - self._t_inicio_fase

            # Arquiva uma cópia — _stats será zerado em iniciar_fase()
            from copy import copy
            self.historico.append(copy(self._stats))

            if DEBUG_TELEMETRY:
                self._imprimir_resumo(numero_fase, self._stats)
        except Exception as e:
            if DEBUG_TELEMETRY:
                print(f"[TELEMETRIA][ERRO] finalizar_fase: {e}")

    # ------------------------------------------------------------------
    # ETAPA 1 — Estatísticas da Fase
    # ------------------------------------------------------------------

    def registrar_moeda(self) -> None:
        """
        Incrementa moedas_coletadas.

        Chamado em: Game.update() — no bloco de coleta de moedas,
        uma vez por moeda coletada no frame.

        Por que não passar a quantidade total?
        ───────────────────────────────────────
        O loop de coleta já itera moeda por moeda — chamar registrar_moeda()
        dentro do loop é mais seguro que passar `len(coletadas)` depois,
        pois garante contagem mesmo se o loop for refatorado.
        """
        try:
            self._stats.moedas_coletadas += 1
        except Exception as e:
            if DEBUG_TELEMETRY:
                print(f"[TELEMETRIA][ERRO] registrar_moeda: {e}")

    def registrar_checkpoint(self) -> None:
        """
        Incrementa checkpoints_ativados.

        Chamado em: Game._checar_colisao_checkpoints() — apenas quando
        um checkpoint muda de ativo=False para ativo=True (não em
        recolisões com checkpoints já ativos).
        """
        try:
            self._stats.checkpoints_ativados += 1
            if DEBUG_TELEMETRY:
                print(
                    f"[TELEMETRIA] Checkpoint #{self._stats.checkpoints_ativados} "
                    f"ativado (fase {self._fase_atual})"
                )
        except Exception as e:
            if DEBUG_TELEMETRY:
                print(f"[TELEMETRIA][ERRO] registrar_checkpoint: {e}")

    # ------------------------------------------------------------------
    # ETAPA 2 — Estatísticas do Jogador
    # ------------------------------------------------------------------

    def registrar_pulo(self) -> None:
        """
        Incrementa total_pulos (pulo normal OU wall jump).

        Chamado em: Game.update() — no bloco `if self.player.pulou:`,
        que já é a One-Frame Flag canônica de pulo no projeto.

        Distinção pulo normal vs wall jump
        ────────────────────────────────────
        O main.py deve chamar registrar_wall_jump() separadamente quando
        detectar que foi um wall jump (via flag player.wall_jumped, se
        adicionada) — ou podemos checar player._parede_dir no frame do pulo.

        Nesta implementação, registrar_pulo() conta TODOS os pulos
        (normais + wall jumps). registrar_wall_jump() é chamado
        ADICIONALMENTE para os wall jumps — assim total_pulos inclui
        tudo e total_wall_jumps é o subconjunto de parede.
        """
        try:
            self._stats.total_pulos += 1
        except Exception as e:
            if DEBUG_TELEMETRY:
                print(f"[TELEMETRIA][ERRO] registrar_pulo: {e}")

    def registrar_wall_jump(self) -> None:
        """
        Incrementa total_wall_jumps.

        Chamado em: Game.update() — no bloco `if self.player.pulou:`,
        quando player.vel_x tem magnitude de wall jump E player.no_chao=False
        antes do pulo (distinção de pulo de parede vs. pulo normal).

        Implementação alternativa: adicionar flag `wall_jumped: bool = False`
        ao Player (zerando junto com `pulou`) — zero-custo e sem lógica
        de inferência no main.py. Por ora, main.py infere pelo contexto.
        """
        try:
            self._stats.total_wall_jumps += 1
            if DEBUG_TELEMETRY:
                print(
                    f"[TELEMETRIA] Wall jump #{self._stats.total_wall_jumps} "
                    f"(fase {self._fase_atual})"
                )
        except Exception as e:
            if DEBUG_TELEMETRY:
                print(f"[TELEMETRIA][ERRO] registrar_wall_jump: {e}")

    def registrar_escalada(self, escalando_atual: bool) -> None:
        """
        Detecta a borda False→True de player.escalando e incrementa total_escaladas.

        Chamado em: Game.update() a cada frame com o valor atual de
        player.escalando. A detecção de borda é feita aqui (não no main.py)
        para manter a lógica de telemetria isolada.

        Por que borda e não contagem de frames?
        ─────────────────────────────────────────
        "Escalou 12 vezes" é mais útil para balanceamento do que
        "ficou escalando por 840 frames" — o segundo depende do FPS e
        da duração de cada escalada, o primeiro conta usos da mecânica.

        Parâmetros
        ──────────
        escalando_atual : player.escalando do frame corrente
        """
        try:
            if escalando_atual and not self._escalando_prev:
                self._stats.total_escaladas += 1
                if DEBUG_TELEMETRY:
                    print(
                        f"[TELEMETRIA] Escalada #{self._stats.total_escaladas} "
                        f"(fase {self._fase_atual})"
                    )
            self._escalando_prev = escalando_atual
        except Exception as e:
            if DEBUG_TELEMETRY:
                print(f"[TELEMETRIA][ERRO] registrar_escalada: {e}")

    def registrar_dano(self) -> None:
        """
        Incrementa total_dano_recebido.

        Chamado em: Game._checar_colisao_inimigos() — apenas quando
        player.tomar_dano() retornar True (dano efetivo, não bloqueado
        por i-frames). Garante que só dano real é contado.
        """
        try:
            self._stats.total_dano_recebido += 1
            if DEBUG_TELEMETRY:
                print(
                    f"[TELEMETRIA] Dano #{self._stats.total_dano_recebido} "
                    f"(fase {self._fase_atual})"
                )
        except Exception as e:
            if DEBUG_TELEMETRY:
                print(f"[TELEMETRIA][ERRO] registrar_dano: {e}")

    # ------------------------------------------------------------------
    # ETAPA 3 — Mapa de Mortes
    # ------------------------------------------------------------------

    def registrar_morte(self, x: float, y: float) -> None:
        """
        Registra a posição da morte no mapa e incrementa mortes da fase.

        Chamado em: Game._checar_colisao_inimigos() — após vidas <= 0,
        antes de _ir_para_game_over(), com player.x e player.y.

        A lista self.mortes acumula toda a sessão — nunca é zerada.
        self._stats.mortes acumula apenas para a fase atual.

        Parâmetros
        ──────────
        x : posição world-space X do player (player.x ou player.rect.centerx)
        y : posição world-space Y do player (player.y ou player.rect.centery)
        """
        try:
            tempo_na_fase = time.monotonic() - self._t_inicio_fase
            evento = EventoMorte(
                fase  = self._fase_atual,
                x     = x,
                y     = y,
                tempo = tempo_na_fase,
            )
            self.mortes.append(evento)
            self._stats.mortes += 1

            if DEBUG_TELEMETRY:
                print(
                    f"[TELEMETRIA] Morte #{self._stats.mortes} "
                    f"| Fase {self._fase_atual} "
                    f"| X={int(x)} Y={int(y)} "
                    f"| t={tempo_na_fase:.1f}s"
                )
        except Exception as e:
            if DEBUG_TELEMETRY:
                print(f"[TELEMETRIA][ERRO] registrar_morte: {e}")

    # ------------------------------------------------------------------
    # ETAPA 4 — Resumo de Fase
    # ------------------------------------------------------------------

    def _imprimir_resumo(self, numero_fase: int, stats: EstatisticasFase) -> None:
        """
        Imprime o resumo de fim de fase no terminal (Etapa 4).

        Formato
        ───────
        ╔══════════════════════════════════════════╗
        ║  RESUMO — FASE 2                        ║
        ╠══════════════════════════════════════════╣
        ║  Tempo         :   47.3s                ║
        ║  Mortes        :   3                    ║
        ║  Moedas        :   5 / 8                ║
        ║  Checkpoints   :   1                    ║
        ║  Pulos         :   42                   ║
        ║  Wall Jumps    :   7                    ║
        ║  Escaladas     :   9                    ║
        ║  Dano recebido :   2                    ║
        ╚══════════════════════════════════════════╝

        Por que não retornar uma string?
        ──────────────────────────────────
        O consumidor atual é o terminal de playtest. Quando a exportação
        para JSON for implementada, os dados já estão em EstatisticasFase
        — o print aqui é apenas conveniência de debug. Uma versão futura
        pode retornar a string para exibição na HUD ou em arquivo.
        """
        t = stats.tempo_total_fase
        linhas = [
            f"╔══════════════════════════════════════════╗",
            f"║  RESUMO — FASE {numero_fase:<26}║",
            f"╠══════════════════════════════════════════╣",
            f"║  Tempo         : {t:>6.1f}s                ║",
            f"║  Mortes        : {stats.mortes:>6}                  ║",
            f"║  Moedas        : {stats.moedas_coletadas:>6}                  ║",
            f"║  Checkpoints   : {stats.checkpoints_ativados:>6}                  ║",
            f"║  Pulos         : {stats.total_pulos:>6}                  ║",
            f"║  Wall Jumps    : {stats.total_wall_jumps:>6}                  ║",
            f"║  Escaladas     : {stats.total_escaladas:>6}                  ║",
            f"║  Dano recebido : {stats.total_dano_recebido:>6}                  ║",
            f"╚══════════════════════════════════════════╝",
        ]
        print("\n".join(linhas))

    def resumo_sessao(self) -> None:
        """
        Imprime o resumo agregado de todas as fases da sessão.

        Chamado opcionalmente em: Game._ir_para_vitoria() ou ao fechar.
        Útil para ter uma visão da sessão completa de playtest.
        """
        if not self.historico:
            if DEBUG_TELEMETRY:
                print("[TELEMETRIA] Nenhuma fase finalizada nesta sessão.")
            return

        if not DEBUG_TELEMETRY:
            return

        print("\n[TELEMETRIA] ══ RESUMO DA SESSÃO ══════════════════════")
        tempo_total = sum(s.tempo_total_fase for s in self.historico)
        mortes_total = sum(s.mortes for s in self.historico)
        moedas_total = sum(s.moedas_coletadas for s in self.historico)
        pulos_total  = sum(s.total_pulos for s in self.historico)

        for i, stats in enumerate(self.historico, start=1):
            t = stats.tempo_total_fase
            print(
                f"  Fase {i}: {t:5.1f}s | "
                f"Mortes:{stats.mortes:2} | "
                f"Moedas:{stats.moedas_coletadas:2} | "
                f"Pulos:{stats.total_pulos:3} | "
                f"WallJ:{stats.total_wall_jumps:2} | "
                f"Escal:{stats.total_escaladas:2}"
            )

        print(f"  ─────────────────────────────────────────────────────")
        print(f"  TOTAL: {tempo_total:.1f}s | Mortes:{mortes_total} | "
              f"Moedas:{moedas_total} | Pulos:{pulos_total}")

        if self.mortes:
            print(f"\n  Mapa de mortes ({len(self.mortes)} total):")
            for m in self.mortes:
                print(f"    Fase {m.fase} | X={int(m.x):>5} Y={int(m.y):>4} | t={m.tempo:.1f}s")
        print("[TELEMETRIA] ════════════════════════════════════════════\n")
