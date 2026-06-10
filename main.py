"""
main.py
═══════
Ponto de entrada do jogo — Game Loop e Máquina de Estados Finita (FSM).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MÁQUINA DE ESTADOS FINITA (FSM)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    ┌──────────┐ ESPAÇO  ┌──────────────┐  morte   ┌───────────┐
    │   MENU   │────────►│   JOGANDO    │─────────►│ GAME_OVER │
    └──────────┘         └──────────────┘          └─────┬─────┘
         ▲               P│   │saida/        R│       │M
         │                ▼   │moedas=0       ▼       │
         │           ┌───────────────┐  ┌──────────┐  │
         │           │   PAUSADO     │  │reset jogo│  │
         │           │  ⟨futuro⟩    │  └──────────┘  │
         │           └────P──────────┘                │
         │                        │                   │
         │    _avancar_fase        ▼                   │
         │   ┌──────────► TRANSICAO_FASE               │
         │   │             ⟨futuro⟩                   │
         │   │                    │                   │
         │   │                    ▼                   │
         │   │              ┌──────────┐        R     │
         └───┼──────M───────│ VITORIA  │──────────────┘
             │              └──────────┘
             │                   │M
             └──────────►_ir_para_menu()

Cada transição é uma chamada a um método dedicado. handle_events()
nunca altera self.estado diretamente — centraliza efeitos colaterais
(áudio, score, construção de nível) e torna as transições testáveis.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PROGRESSÃO DE CAMPANHA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

O jogo possui TOTAL_FASES fases numeradas de 1 a N. O arquivo de cada
fase é resolvido dinamicamente por _arquivo_fase_atual():

    fase_atual=1  →  "fase1.txt"
    fase_atual=2  →  "fase2.txt"
    fase_atual=3  →  "fase3.txt"

Ao zerar as moedas de uma fase intermediária, _avancar_fase() incrementa
fase_atual, reconstrói o nível (sem resetar o score) e toca o SFX de
transição. Ao zerar a última fase, _ir_para_vitoria() é chamado — encerra
a campanha com a tela de vitória final.

_resetar_jogo(reiniciar_campanha=True) é chamado ao pressionar R no
GAME_OVER/VITORIA ou ao iniciar pelo MENU: reseta fase_atual=1 e score=0.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SEPARAÇÃO DE RESPONSABILIDADES NO GAME LOOP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  handle_events()   lê intenções do jogador e do SO
                    → nunca move objetos, nunca desenha

  update(dt)        avança o mundo em dt segundos
                    → nunca lê input, nunca desenha
                    → guarda antecipada: retorna se estado ≠ "JOGANDO"

  draw()            compõe pixels para o frame atual
                    → nunca lê input, nunca muda estado de jogo

Misturar responsabilidades é a causa mais comum de bugs difíceis de
reproduzir em jogos (ex.: física executada duas vezes por frame).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GERENCIAMENTO DE MEMÓRIA — GRUPOS DE SPRITES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Sprites do Pygame são contados por referência. Um sprite pode pertencer
a múltiplos Groups simultaneamente. Se um Group for substituído sem
esvaziar o anterior, sprites com referências externas (variáveis locais,
outras estruturas) permanecem vivos na memória — memory leak silencioso
que cresce a cada reset.

Solução: _construir_nivel() chama group.empty() em todos os grupos
existentes antes de recriar. empty() chama sprite.kill() em cada membro,
removendo-o de TODOS os grupos e liberando a Surface para o GC.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COLISÃO DE PISÃO (STOMP)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Condições simultâneas para stomp:
  1. player.vel_y > 0              → jogador está caindo
  2. player.rect.bottom ≤ centery  → base do jogador acima da linha
                                     média do inimigo

Usar centery (e não rect.top) concede metade da altura do inimigo como
zona de tolerância — o pisão é detectado mesmo que o jogador ultrapasse
levemente o topo num frame de alta velocidade.

Após stomp: vel_y = PLAYER_STOMP_BOUNCE (negativo), no_chao = False.
A flag no_chao deve ser False para que a gravidade retome imediatamente.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ÁUDIO RESILIENTE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Cada arquivo de som tem seu próprio try/except. Um arquivo ausente não
impede os demais de carregar. self.sons mapeia chave → Sound | None;
_tocar_som() faz o guard em um único ponto, sem ``if som`` espalhado.

pygame.mixer.music é um canal dedicado de streaming (músicas longas,
não carregadas na RAM). pygame.mixer.Sound ocupa canais polyphônicos
(SFX curtos, carregados integralmente para latência mínima).
"""

from __future__ import annotations

import pathlib
import random
import sys
import pygame

import config
from camera          import Camera
from player          import Player
from sprites         import Checkpoint, Inimigo, Moeda, Plataforma, SaidaFase
from enemies         import create_enemy
from plataforma_movel import PlataformaMovel
from traps           import create_trap
from save_manager    import SaveManager
from menu_principal  import MenuPrincipal, OpcaoMenu
from menu_pause      import MenuPause, OpcaoPause
from entities.insects import create_insect
from game_states     import GameState
from hud             import Hud, HudData
from telemetry       import Telemetria
from tilemap_loader  import carregar_mapa, inspecionar_mapa
from particulas      import (
    GerenciadorParticulas,
    emitir_landing_dust,
    emitir_jump_dust,
    emitir_run_dust,
    emitir_rastro_vento,
    emitir_cauda_break,
    RUN_INTERVALO,
    RUN_VEL_THRESHOLD,
)


# ══════════════════════════════════════════════════════════════════════
class Game:
    """
    Orquestra todos os subsistemas do jogo.

    Atributos persistentes entre partidas (criados em __init__)
    ─────────────────────────────────────────────────────────────
    screen, clock, running      infraestrutura do Pygame
    estado                      estado atual da FSM
    high_score                  melhor pontuação da sessão
    sons                        dict[str, Sound | None]
    _musica_atual               faixa em reprodução (guard de idempotência)
    _fonte_*                    fontes pré-carregadas
    _overlay                    Surface semi-transparente pré-renderizada
    _surf_faixa_menu             Surface da faixa de fundo do menu (pré-renderizada)

    Atributos recriados a cada _construir_nivel()
    ──────────────────────────────────────────────
    player, camera, score
    plataformas, moedas, inimigos, checkpoints, saida_sprite   (Groups)
    plataformas_moveis   (lista de PlataformaMovel — participam do grupo plataformas)
    saida_fase  (SaidaFase | None)
    _spawn_x, _spawn_y, _total_moedas
    _checkpoint_respawn_x, _checkpoint_respawn_y (float | None)
    _fase_concluida (bool) — guard contra duplo disparo no mesmo frame
    """

    # Volumes centralizados — ajuste aqui sem abrir os métodos de áudio
    _VOL_MUSICA_MENU: float = 0.40
    _VOL_MUSICA_FASE: float = 0.35
    _VOL_SFX: dict[str, float] = {
        "pulo":    0.35,
        "moeda":   0.45,
        "morte":   0.55,
        "stomp":   0.50,
        "vitoria": 0.60,
    }

    # Mapeamento explícito: chave SFX → constante em config
    # Preferido sobre getattr dinâmico — erros de nome são capturados
    # em tempo de importação, não em tempo de execução.
    _CAMINHOS_SFX: dict[str, str] = {
        "pulo":    config.SFX_PULO,
        "moeda":   config.SFX_MOEDA,
        "morte":   config.SFX_MORTE,
        "stomp":   config.SFX_STOMP,
        "vitoria": config.SFX_VITORIA,
    }

    # ── Landing Impact — constantes de Game Feel ──────────────────────
    #
    # Todas as constantes que controlam o shake de pouso ficam aqui,
    # não espalhadas pelo código — alterar o feel requer mudar apenas
    # este bloco.
    #
    # _LANDING_VY_THRESHOLD
    #   Velocidade de queda mínima (px/s) para disparar o shake.
    #   Quedas menores (ex: pular e pousar na mesma plataforma) não
    #   geram tremor — evita feedback excessivo em ações cotidianas.
    #   Valor padrão: 300 px/s ≈ queda de ~1.5 tile de altura.
    #
    # _LANDING_SHAKE_MIN / _LANDING_SHAKE_MAX
    #   Limites de intensidade do shake em pixels.
    #   O clamp garante que quedas extremas (terminal velocity = 900 px/s)
    #   não gerem tremores excessivos que desorientem o jogador.
    #
    # _LANDING_SHAKE_DURACAO
    #   Duração do tremor em segundos. Quedas de pouso devem ser mais
    #   curtas que o shake de dano (0.30s) — o impacto é momentâneo.
    #
    # _LANDING_SHAKE_FATOR
    #   Multiplicador linear: intensidade = vel_impacto × FATOR.
    #   Ajuste este valor para calibrar a "sensação de peso" sem tocar
    #   em threshold nem nos limites de clamp.
    _LANDING_VY_THRESHOLD:   float = 300.0   # px/s mínimo para shake
    _LANDING_SHAKE_MIN:      int   = 2        # intensidade mínima (px)
    _LANDING_SHAKE_MAX:      int   = 10       # intensidade máxima (px)
    _LANDING_SHAKE_DURACAO:  float = 0.12     # duração do tremor (s)
    _LANDING_SHAKE_FATOR:    float = 0.015    # vel_y → intensidade linear

    # ── Hit Stop — congelamento dramático de simulação ────────────────
    #
    # O Hit Stop congela a SIMULAÇÃO (física, animações, partículas)
    # por uma fração de segundo para dar peso dramático ao impacto.
    # O renderizador (draw) continua rodando normalmente — o frame
    # congelado fica na tela por _HIT_STOP_DANO segundos.
    #
    # Por que NÃO usar time.sleep()?
    # ──────────────────────────────────────────────────────────────────
    # time.sleep() bloqueia o processo Python inteiro — o Pygame para de
    # processar eventos, a janela congela a nível de SO (aparece "sem
    # resposta" no Windows), e o vsync / compositor perdem o controle do
    # frame timing. Em laptops com gerenciamento de energia, isso pode
    # disparar throttling de CPU nos frames seguintes.
    #
    # Com bypass de update: o loop roda normalmente (handle→update→draw),
    # clock.tick() mantém o ritmo de FPS, eventos são processados (ESC
    # funciona), e apenas a LÓGICA é pulada — o frame "congela" visualmente
    # porque draw() redesenha o mesmo estado por N frames.
    #
    # _HIT_STOP_DANO:  duração do congelamento ao jogador tomar dano.
    # _HIT_STOP_STOMP: duração ao pisar em inimigo (mais curto — vitória,
    #                  não punição).
    _HIT_STOP_DANO:   float = 0.12   # segundos de freeze ao tomar dano
    _HIT_STOP_STOMP:  float = 0.06   # segundos de freeze ao pisar inimigo

    # ── Ghost Effect (Afterimages) — rastro de velocidade ────────────
    #
    # _GHOST_VX_THRESHOLD / _GHOST_VY_THRESHOLD
    #   Velocidades mínimas (px/s) para ativar o rastro.
    #   Valores abaixo destas não geram fantasmas — sem ruído visual
    #   em movimentos cotidianos.
    #
    # _GHOST_INTERVALO
    #   Segundos entre cada captura de fantasma. Menor = rastro mais denso.
    #   0.04s ≈ um fantasma a cada 2–3 frames — sutil mas legível.
    #
    # _GHOST_ALPHA_INICIAL / _GHOST_ALPHA_DECAY
    #   Alpha de nascimento (0–255) e decaimento por segundo.
    #   150 / 600 = 0.25s de vida — rastro curto e enérgico.
    #
    # _GHOST_MAX
    #   Limite absoluto de fantasmas simultâneos. Previne memory leak
    #   caso o jogador permaneça em alta velocidade por longo tempo.
    _GHOST_VX_THRESHOLD:   float = 120.0   # px/s horizontal mínima
    _GHOST_VY_THRESHOLD:   float = 350.0   # px/s vertical mínima (queda)
    _GHOST_INTERVALO:      float = 0.04    # segundos entre capturas
    _GHOST_ALPHA_INICIAL:  int   = 140     # alpha de nascimento (0–255)
    _GHOST_ALPHA_DECAY:    float = 560.0   # alpha perdido por segundo
    _GHOST_MAX:            int   = 12      # máximo de fantasmas simultâneos

    # ── Camera Juice Bias — câmera preditiva ──────────────────────────
    #
    # Repassa parâmetros para Camera.update_com_bias().
    # Centralizados aqui para tuning rápido sem abrir camera.py.
    #
    # _CAMERA_BIAS_FATOR
    #   Proporção vel_x → bias em pixels. 0.25 = corrida a 160px/s
    #   gera 40px de antecipação.
    #
    # _CAMERA_BIAS_LERP
    #   Taxa de interpolação do bias por segundo. 5.0 = ~63% do
    #   delta coberto em 0.2s — responsivo mas suave na inversão.
    #
    # _CAMERA_BIAS_MAX
    #   Limite máximo do bias (px). Impede que sprints longos
    #   empurrem o calango para o canto da tela.
    _CAMERA_BIAS_FATOR: float = 0.25
    _CAMERA_BIAS_LERP:  float = 5.0
    _CAMERA_BIAS_MAX:   float = 80.0

    # ── Rastro de vento — Fall Wind Dust ─────────────────────────────
    # Ativa quando vel_y supera este limiar (queda rápida).
    _WIND_VY_THRESHOLD:  float = 400.0   # px/s mínima para wind particles
    _WIND_INTERVALO:     float = 0.04    # segundos entre emissões (2 frames)

    # ──────────────────────────────────────────────────────────────────
    # INICIALIZAÇÃO
    # ──────────────────────────────────────────────────────────────────

    def __init__(self) -> None:
        pygame.init()
        # mixer.init() separado: permite rodar em ambientes headless
        # (servidores CI, containers) sem dispositivo de áudio.
        pygame.mixer.init()

        self.screen: pygame.Surface = pygame.display.set_mode(
            (config.SCREEN_WIDTH, config.SCREEN_HEIGHT)
        )
        pygame.display.set_caption(config.TITLE)

        self.clock:   pygame.time.Clock = pygame.time.Clock()
        self.running: bool              = True

        # ── FSM ───────────────────────────────────────────────────────
        self.estado: GameState = GameState.MENU
        self.high_score:  int = 0

        # ── Progressão de campanha ────────────────────────────────────
        # TOTAL_FASES é uma constante de instância (não de classe) porque
        # pode variar por perfil de dificuldade no futuro sem alterar a
        # lógica de nenhum outro módulo.
        # ── Debug de level design ─────────────────────────────────────
        # DEBUG_MAPA = True → imprime inspecionar_mapa() a cada carga de fase.
        # Mostra inimigos, checkpoints e insetos carregados do TMX/TXT.
        # Desativar antes do build final.
        self.DEBUG_MAPA: bool = False

        self.TOTAL_FASES: int = 3
        self.fase_atual:  int = 1

        # ── Sistema de vidas ──────────────────────────────────────────
        # vidas_max: limite superior; reutilizado em _resetar_jogo()
        #            para restaurar vidas ao valor correto sem magic number.
        # vidas:     contagem atual, decrementada por _checar_colisao_inimigos()
        #            quando tomar_dano() retorna True.
        #            Vidas persistem entre fases (reiniciar_campanha=False);
        #            resetam ao recomeçar a campanha (reiniciar_campanha=True).
        self.vidas_max: int = 3
        self.vidas:     int = self.vidas_max

        # ── Screen Shake ──────────────────────────────────────────────
        # shake_timer:       segundos restantes de tremor. Decrementado por
        #                    dt em update(); zero significa tela estável.
        # shake_intensidade: deslocamento máximo em pixels a cada frame.
        #                    Quanto maior, mais violento o tremor.
        # Ambos são manipulados exclusivamente por disparar_shake() e
        # update() — nenhum outro método deve escrevê-los diretamente.
        self.shake_timer:       float = 0.0
        self.shake_intensidade: int   = 0

        # ── Hit Stop ──────────────────────────────────────────────────
        # hit_stop_timer > 0 → simulação congelada; draw() continua ativo.
        # Decrementado antes do guard JOGANDO em update() — assim o freeze
        # sobrevive à transição de estado (ex: last hit → GAME_OVER).
        self.hit_stop_timer: float = 0.0

        # ── Partículas visuais ────────────────────────────────────────
        # GerenciadorParticulas criado aqui (persistente entre frames) e
        # limpo em _construir_nivel() ao trocar de fase — evita partículas
        # de uma fase aparecendo na próxima.
        self.particulas: GerenciadorParticulas = GerenciadorParticulas()

        # ── Ghost Effect (Afterimages) ────────────────────────────────
        # Cada entrada: {"surf": Surface, "x": float, "y": float, "alpha": float}
        # Gerenciado exclusivamente em update (adicionar/decay/remover)
        # e _draw_jogo (renderizar). Limpado em _construir_nivel().
        self._ghosts:      list[dict]  = []
        self._ghost_timer: float       = 0.0   # cronômetro entre capturas

        # ── Rastro de vento (Fall Wind Dust) ─────────────────────────
        self._wind_timer: float = 0.0   # cronômetro entre emissões de vento

        # ── Áudio ─────────────────────────────────────────────────────
        self._musica_atual: str = ""
        self._inicializar_sons()

        # ── Fontes (SysFont tem custo de I/O — criadas uma única vez) ─
        self._fonte_titulo:    pygame.font.Font = pygame.font.SysFont(None, 90)
        self._fonte_subtitulo: pygame.font.Font = pygame.font.SysFont(None, 42)
        self._fonte_hud:       pygame.font.Font = pygame.font.SysFont(None, 30)
        self._fonte_score:     pygame.font.Font = pygame.font.SysFont(None, 36)

        # ── HUD — instanciada uma única vez, reutilizada a cada frame ──
        self._hud: Hud = Hud()

        # ── Telemetria — observer puro, sem side-effects de jogo ──────
        self._tel: Telemetria = Telemetria()

        # ── Save Manager ──────────────────────────────────────────────
        # Instanciado uma vez; o arquivo é lido/escrito sob demanda.
        # Nenhum estado de jogo é armazenado aqui — apenas I/O.
        self._save: SaveManager = SaveManager()

        # ── Menu Principal ────────────────────────────────────────────
        # Instanciado uma vez; reset() é chamado ao transitar para MENU.
        # Callbacks de áudio injetados aqui quando os SFX estiverem prontos.
        self._menu: MenuPrincipal = MenuPrincipal(
            largura    = config.SCREEN_WIDTH,
            altura     = config.SCREEN_HEIGHT,
            on_move    = None,   # futuro: lambda: self._tocar_som('menu_move')
            on_confirm = None,   # futuro: lambda: self._tocar_som('menu_confirm')
        )

        # ── Menu de Pausa ─────────────────────────────────────────────
        self._pause: MenuPause = MenuPause(
            largura    = config.SCREEN_WIDTH,
            altura     = config.SCREEN_HEIGHT,
            on_move    = None,   # futuro: lambda: self._tocar_som('menu_move')
            on_confirm = None,   # futuro: lambda: self._tocar_som('menu_confirm')
        )

        # Acumulador de tempo jogado (segundos) — incrementado a cada frame.
        # Persiste entre sessões via save.
        self._tempo_jogado: float = 0.0

        # Contador global de moedas coletadas em toda a campanha.
        # Distinto de self.score (que pode ser zerado por fase).
        self._moedas_coletadas_total: int = 0

        # ── Carregamento do save (deve vir após todos os atributos) ──
        self._carregar_save_se_existir()

        # ── Prepara menu inicial ──────────────────────────────────────
        self._menu.reset(tem_save=self._save.exists())

        # ── Surfaces pré-renderizadas (criadas uma vez, blit a cada frame) ─
        # Overlay: preto a ~67% de opacidade para painéis de Game Over / Vitória.
        self._overlay: pygame.Surface = pygame.Surface(
            (config.SCREEN_WIDTH, config.SCREEN_HEIGHT), pygame.SRCALPHA
        )
        self._overlay.fill((0, 0, 0, 170))

        # Faixa azul-marinho para o terço superior do menu.
        # Criar Surface dentro de _draw_menu() custaria uma alocação por frame
        # (60x/s) — movida para cá elimina o custo sem mudar o visual.
        self._surf_faixa_menu: pygame.Surface = pygame.Surface(
            (config.SCREEN_WIDTH, config.SCREEN_HEIGHT // 2)
        )
        self._surf_faixa_menu.fill((15, 15, 45))

        # ── Nível inicial ─────────────────────────────────────────────
        self._construir_nivel()
        self._tocar_musica(config.MUSICA_MENU, self._VOL_MUSICA_MENU)

    # ══════════════════════════════════════════════════════════════════
    # ÁUDIO
    # ══════════════════════════════════════════════════════════════════

    def _inicializar_sons(self) -> None:
        """
        Carrega cada SFX de forma independente com try/except próprio.

        Um arquivo ausente não impede os demais de carregar. O resultado
        é self.sons: dict[str, Sound | None]. O valor None indica "arquivo
        não encontrado" — _tocar_som() faz o guard em um único ponto.

        Por que mapeamento explícito (_CAMINHOS_SFX) e não getattr()?
        ─────────────────────────────────────────────────────────────────
        getattr(config, f"SFX_{chave.upper()}") falha em runtime com
        AttributeError se uma chave não tiver correspondente em config —
        silenciosamente ignorada pelo except. Com o dict explícito, um
        erro de nome é capturado em tempo de importação (NameError), muito
        mais fácil de depurar.
        """
        def _tentar_carregar(caminho: str, volume: float) -> pygame.mixer.Sound | None:
            try:
                som = pygame.mixer.Sound(caminho)
                som.set_volume(volume)
                return som
            except (FileNotFoundError, pygame.error) as exc:
                print(f"[ÁUDIO] Não encontrado: '{caminho}' — {exc}")
                return None

        self.sons: dict[str, pygame.mixer.Sound | None] = {
            chave: _tentar_carregar(caminho, self._VOL_SFX[chave])
            for chave, caminho in self._CAMINHOS_SFX.items()
        }

    def _tocar_som(self, chave: str) -> None:
        """
        Dispara um SFX pelo nome. No-op silencioso se ausente ou None.
        Centralizar o guard aqui evita checagens espalhadas pelo código.
        """
        som = self.sons.get(chave)
        if som is not None:
            som.play()

    def _tocar_musica(self, arquivo: str, volume: float = 0.40) -> None:
        """
        Carrega e toca um arquivo de música em loop infinito.

        Guard de idempotência: não reinicia a faixa se ela já estiver
        tocando — evita o "click" audível ao chamar _resetar_jogo()
        enquanto a música de fase já está em reprodução.

        pygame.mixer.music: streaming do disco, canal dedicado, sem
        interferência com os canais polyfônicos dos SFX.
        """
        if arquivo == self._musica_atual and pygame.mixer.music.get_busy():
            return

        try:
            pygame.mixer.music.load(arquivo)
            pygame.mixer.music.set_volume(volume)
            pygame.mixer.music.play(-1)   # -1 = loop infinito
            self._musica_atual = arquivo
        except (FileNotFoundError, pygame.error) as exc:
            print(f"[ÁUDIO] Música não encontrada: '{arquivo}' — {exc}")
            self._musica_atual = ""

    def _parar_musica(self) -> None:
        """Para a música imediatamente e zera o rastreador de faixa."""
        pygame.mixer.music.stop()
        self._musica_atual = ""

    # ══════════════════════════════════════════════════════════════════
    # CONSTRUÇÃO E CARREGAMENTO DE FASE — via tilemap_loader
    # ══════════════════════════════════════════════════════════════════
    #
    # main.py é responsável por:
    #   1. Chamar carregar_mapa() para obter MapData (dados puros)
    #   2. Instanciar sprites a partir dos dados retornados
    #   3. Atualizar câmera e Player com as dimensões do mapa
    #
    # tilemap_loader.py é responsável por:
    #   1. Detectar o formato (.txt ou .tmx)
    #   2. Parsear o arquivo e retornar MapData
    #   3. Aplicar conversão de escala visual → lógica
    #
    # Sem dependência circular:
    #   main.py  →  tilemap_loader  (main importa loader)
    #   tilemap_loader  ↛  main.py  (loader nunca importa main)
    # ══════════════════════════════════════════════════════════════════

    def _construir_nivel(self, arquivo: str | None = None) -> None:
        """
        Cria (ou reconstrói) todos os objetos do nível a partir do arquivo.

        Fluxo
        ──────
          1. Chama carregar_mapa() → recebe MapData com dados puros
          2. Limpa grupos existentes (anti-leak via empty())
          3. Instancia sprites a partir de MapData
          4. Configura câmera e Player

        Gerenciamento de memória — anti-leak
        ──────────────────────────────────────
        empty() chama kill() em cada sprite, removendo-o de TODOS os
        grupos antes de reatribuir — sem isso sprites com referências
        externas sobrevivem como "fantasmas" (memory leak silencioso).
        """
        arquivo = arquivo or self._arquivo_fase_atual()
        self.score: int = 0

        # Limpa partículas da fase anterior — evita ghosting visual
        if hasattr(self, "particulas"):
            self.particulas.limpar()
        self._ghosts.clear()
        self._ghost_timer = 0.0
        self._wind_timer  = 0.0

        # ── Leitura do mapa via loader desacoplado ────────────────────
        dados = carregar_mapa(arquivo)
        if dados is None:
            # Loader já imprimiu o aviso — continua com grupos vazios
            dados = {
                "largura_px": config.WORLD_WIDTH,
                "altura_px":  config.SCREEN_HEIGHT,
                "tile_size":  config.TILE_SIZE,
                "colisao": [], "spawn": None,
                "moedas": [], "inimigos": [], "objetos": [],
            }

        if self.DEBUG_MAPA:
            print(inspecionar_mapa(dados))

        # ── Anti-leak: esvazia grupos antes de recriar ────────────────
        for nome_attr in ("plataformas", "moedas", "inimigos", "checkpoints", "saida_sprite", "insetos", "plataformas_moveis_group", "armadilhas"):
            grupo = getattr(self, nome_attr, None)
            if isinstance(grupo, pygame.sprite.Group):
                grupo.empty()

        # ── Respawn de checkpoint zerado a cada nova fase ─────────────
        # Ao trocar de fase, o jogador deve respawnar no spawn original
        # do novo nível — nunca herdar checkpoints de fases anteriores.
        self._checkpoint_respawn_x: float | None = None
        self._checkpoint_respawn_y: float | None = None

        # Guard de disparo único — zerado a cada novo nível.
        # Impede que um único frame de colisão dispare _avancar_fase()
        # mais de uma vez (colisão detectada em múltiplos sub-passos).
        self._fase_concluida: bool = False

        # ── Telemetria: inicia coleta da nova fase ────────────────
        self._tel.iniciar_fase(self.fase_atual)

        # ── Câmera dimensionada para o mapa real ──────────────────────
        self.camera = Camera(largura_mundo=dados["largura_px"])

        # ── Grupos de sprites ─────────────────────────────────────────
        self.plataformas:  pygame.sprite.Group = pygame.sprite.Group()
        self.moedas:       pygame.sprite.Group = pygame.sprite.Group()
        self.inimigos:     pygame.sprite.Group = pygame.sprite.Group()
        self.checkpoints:  pygame.sprite.Group = pygame.sprite.Group()
        # Grupo de sprite único (0 ou 1 elemento) — permite usar
        # spritecollide() e camera.aplicar() sem caso especial.
        self.saida_sprite: pygame.sprite.Group = pygame.sprite.Group()

        # Insetos do cenário — presas potenciais da língua.
        # Grupo padrão: pode conter dezenas de sprites simultâneos.
        self.insetos: pygame.sprite.Group = pygame.sprite.Group()

        # Plataformas móveis — grupo dedicado para update() e transporte.
        # Os sprites também são adicionados a self.plataformas para que
        # o AABB existente do Player detecte colisão automaticamente.
        self.plataformas_moveis_group: pygame.sprite.Group = pygame.sprite.Group()

        # Armadilhas ambientais — grupo dedicado para update(), colisão e render.
        self.armadilhas: pygame.sprite.Group = pygame.sprite.Group()

        # ── Instanciação a partir de MapData ──────────────────────────
        # Cada lista de dados puros vira sprites concretos aqui.
        # tilemap_loader não sabe que Plataforma/Moeda/Inimigo existem.

        for x, y, w, h in dados["colisao"]:
            self.plataformas.add(Plataforma(x, y, w, h))

        for cx, cy in dados["moedas"]:
            self.moedas.add(Moeda(int(cx), int(cy)))

        for inf in dados["inimigos"]:
            # create_enemy() consulta o registry pelo campo inf["tipo"].
            # Retorna None para tipos desconhecidos — não trava o jogo.
            inimigo = create_enemy(inf)
            if inimigo is not None:
                self.inimigos.add(inimigo)

        # ── Saída de fase ─────────────────────────────────────────────
        # dados["saida"] é None para fases sem saída configurada.
        # O grupo vazio faz spritecollide() retornar [] sem erro —
        # comportamento legado (moedas como trigger) não é afetado.
        if dados["saida"] is not None:
            sd = dados["saida"]
            self.saida_sprite.add(SaidaFase(sd["x"], sd["y"]))

        # ── Insetos ───────────────────────────────────────────────────
        # create_insect() consulta o registry pelo campo tipo.
        # Retorna None para tipos desconhecidos — não trava o jogo.
        for ins in dados["insetos"]:
            inseto = create_insect(ins)
            if inseto is not None:
                self.insetos.add(inseto)

        # ── Armadilhas Ambientais ─────────────────────────────────────
        # create_trap() consulta o registry pelo campo tipo.
        # Retorna None para tipos desconhecidos — não trava o jogo.
        for arm_dado in dados["armadilhas"]:
            armadilha = create_trap(arm_dado)
            if armadilha is not None:
                self.armadilhas.add(armadilha)

        # ── Plataformas Móveis ────────────────────────────────────────
        # Cada PlataformaMovelDado vira um sprite PlataformaMovel.
        # O sprite é adicionado a DOIS grupos:
        #   1. plataformas_moveis_group → para update() e transporte
        #   2. plataformas               → para AABB do Player (sem alterar player.py)
        for pm_dado in dados["plataformas_moveis"]:
            pm = PlataformaMovel(
                x              = pm_dado["x"],
                y              = pm_dado["y"],
                largura        = pm_dado.get("largura",        120),
                altura         = pm_dado.get("altura",          40),
                tipo_movimento = pm_dado.get("tipo_movimento", "horizontal"),
                velocidade     = float(pm_dado.get("velocidade",    80.0)),
                x_min          = pm_dado.get("x_min",          pm_dado["x"]),
                x_max          = pm_dado.get("x_max",          pm_dado["x"] + 400),
                y_min          = pm_dado.get("y_min",          pm_dado["y"]),
                y_max          = pm_dado.get("y_max",          pm_dado["y"] + 400),
            )
            self.plataformas_moveis_group.add(pm)
            self.plataformas.add(pm)   # AABB do Player detecta colisão sem alterar player.py

        # ── Checkpoints ───────────────────────────────────────────────
        # Cada CheckpointDado vira um sprite Checkpoint.
        # A lista pode ser vazia — fases sem checkpoint continuam
        # funcionando normalmente (respawn no spawn original).
        for cp in dados["checkpoints"]:
            self.checkpoints.add(Checkpoint(cp["x"], cp["y"]))

        # ── Spawn do calango ──────────────────────────────────────────
        if dados["spawn"] is not None:
            self._spawn_x, self._spawn_y = dados["spawn"]
        else:
            # Fallback: canto superior esquerdo do mapa
            self._spawn_x = float(config.TILE_SIZE)
            self._spawn_y = float(config.TILE_SIZE)

        # Player criado APÓS o carregamento para usar o spawn correto
        self.player = Player(self._spawn_x, self._spawn_y)

        # Total de moedas para barra de progresso no HUD
        self._total_moedas: int = len(self.moedas)

    def _limites_patrulha(
        self,
        grid:        list[str],
        lin_inimigo: int,
        col_inimigo: int,
        num_colunas: int,
    ) -> tuple[int, int]:
        """
        Calcula (x_min, x_max) de patrulha para um inimigo em world-space.

        Estratégia: scan de chão
        ─────────────────────────
        Percorre colunas adjacentes enquanto houver tile '#' na linha
        imediatamente abaixo do inimigo (lin_chao = lin_inimigo + 1).
        Para no primeiro buraco ou na borda do mapa.

        Fallback: sem chão detectado → ±3 tiles (inimigo flutuante).

        Retorno: (x_min, x_max) em pixels de mundo.
        x_max = (col_dir + 1) * T usa a borda direita do tile mais à direita.
        """
        T        = config.TILE_SIZE
        lin_chao = lin_inimigo + 1

        def tem_chao(col: int) -> bool:
            """True se (lin_chao, col) for tile sólido '#'."""
            if not (0 <= col < num_colunas):
                return False
            if lin_chao >= len(grid):
                return False
            row = grid[lin_chao]
            return col < len(row) and row[col] == "#"

        col_esq = col_inimigo
        while col_esq > 0 and tem_chao(col_esq - 1):
            col_esq -= 1

        col_dir = col_inimigo
        while col_dir < num_colunas - 1 and tem_chao(col_dir + 1):
            col_dir += 1

        # Fallback: inimigo sem chão detectado
        if col_esq == col_inimigo and col_dir == col_inimigo:
            col_esq = max(0,               col_inimigo - 3)
            col_dir = min(num_colunas - 1, col_inimigo + 3)

        return col_esq * T, (col_dir + 1) * T

    # ══════════════════════════════════════════════════════════════════
    # TRANSIÇÕES DE ESTADO
    # ══════════════════════════════════════════════════════════════════
    # Cada transição é um método dedicado. handle_events() nunca altera
    # self.estado diretamente — sempre delega para cá. Isso centraliza
    # os efeitos colaterais (áudio, score, construção de nível) e torna
    # as transições testáveis de forma independente.

    def _arquivo_fase_atual(self) -> str:
        """
        Resolve dinamicamente o caminho do arquivo de mapa para a fase
        corrente usando uma f-string.

        Exemplos:
            fase_atual=1  →  "<BASE_DIR>/fase1.txt"
            fase_atual=2  →  "<BASE_DIR>/fase2.txt"
            fase_atual=3  →  "<BASE_DIR>/fase3.txt"

        Usar str(config.BASE_DIR / ...) garante portabilidade entre
        sistemas operacionais (/ em vez de \\ no Windows).
        """
        return str(config.BASE_DIR / f"fase{self.fase_atual}.txt")

    def _resetar_jogo(self, reiniciar_campanha: bool = True) -> None:
        """
        Reconstrói o nível e transita para JOGANDO.

        Parâmetro reiniciar_campanha
        ─────────────────────────────
        True  (padrão) — chamado pelo MENU ou R no GAME_OVER/VITORIA:
              reseta fase_atual=1 e vidas=vidas_max para começar a
              campanha do início com vidas completas.

        False — chamado por _avancar_fase():
              mantém fase_atual já incrementado e preserva vidas atuais
              — o jogador carrega o estado de saúde que conquistou nas
              fases anteriores. Score também é preservado.

        Em ambos os casos, _construir_nivel() recria todos os grupos
        (empty() → anti-leak) e recria o Player no spawn da nova fase.
        O high_score nunca é resetado — persiste durante a sessão.
        """
        if reiniciar_campanha:
            self.fase_atual = 1
            self.vidas      = self.vidas_max   # vidas cheias ao recomeçar

        self._construir_nivel()   # usa _arquivo_fase_atual() internamente

        # ── Sincroniza vida do Player com o Game ─────────────────
        # Após reconstrução do nível, garante que player.vida_atual
        # espelha self.vidas (que já foi resetado se reiniciar_campanha).
        self.player.vida_atual     = self.vidas
        self.player.morto          = False
        self.player.tem_cauda      = self.player.PLAYER_START_WITH_TAIL
        self.player.just_lost_tail = False
        self.player.lingua         = self.player.lingua.__class__()   # reset via reinicialização

        # ── Respawn condicional em checkpoint ─────────────────────────
        # _construir_nivel() sempre recria o Player no spawn original.
        # Se havia um checkpoint ativo na fase (reiniciar_campanha=False
        # = morte com checkpoint), move o Player para o checkpoint.
        #
        # Condição: reiniciar_campanha=False garante que estamos
        # DENTRO da mesma fase (morte), não trocando de fase.
        # Trocar de fase (reiniciar_campanha=False via _avancar_fase)
        # também zeraria _checkpoint_respawn em _construir_nivel —
        # portanto a condição abaixo nunca reposiciona erroneamente
        # em fase errada.
        #
        # O Player é reposicionado diretamente nos atributos públicos
        # (self.x, self.y, self.rect) — exatamente como Player.__init__
        # faria com as coordenadas de spawn, sem tocar em física.
        if (not reiniciar_campanha
                and self._checkpoint_respawn_x is not None
                and self._checkpoint_respawn_y is not None):
            self.player.x      = self._checkpoint_respawn_x
            self.player.y      = self._checkpoint_respawn_y
            self.player.rect.x = int(self.player.x)
            self.player.rect.y = int(self.player.y)

        # Preserva score quando avançando de fase (reiniciar_campanha=False)
        # mas zera quando recomeçando do zero (reiniciar_campanha=True).
        # _construir_nivel() sempre zera; re-atribuímos aqui se necessário.
        # Nota: o score já foi zerado em _construir_nivel(); como queremos
        # preservar apenas no avanço de fase, o score acumulado é passado
        # explicitamente por _avancar_fase() após a chamada.
        self.estado = GameState.JOGANDO

    def _avancar_fase(self) -> None:
        """
        Incrementa fase_atual e carrega o próximo nível sem resetar o score.

        Fluxo
        ──────
        1. Guarda o score atual (será zerado por _construir_nivel).
        2. Incrementa fase_atual.
        3. Chama _resetar_jogo(reiniciar_campanha=False) — reconstrói o
           nível já com o novo fase_atual, sem voltar à fase 1.
        4. Restaura o score acumulado para que o jogador carregue a
           pontuação conquistada nas fases anteriores.
        5. Toca o SFX de vitória como feedback de conclusão de fase.
        6. Reinicia a música da fase para dar frescor ao novo nível.

        Por que guardar/restaurar o score?
        ────────────────────────────────────
        _construir_nivel() sempre executa ``self.score = 0`` (inicializa
        limpo para o nível). Guardar antes e restaurar depois é a forma
        mais simples de preservar o score sem alterar a lógica interna
        de _construir_nivel() — mantém o contrato claro: cada nível
        começa do zero internamente; quem decide agregar é a campanha.
        """
        score_acumulado = self.score          # 1. guarda antes do reset

        self.fase_atual += 1                  # 2. avança a fase
        self._resetar_jogo(reiniciar_campanha=False)  # 3. constrói novo nível

        self.score = score_acumulado          # 4. restaura pontuação

        self._tocar_som("vitoria")            # 5. SFX de conclusão de fase
        self._tocar_musica(                   # 6. reinicia trilha da fase
            config.MUSICA_FASE, self._VOL_MUSICA_FASE
        )

    def _ir_para_game_over(self) -> None:
        """Derrota: atualiza high_score, para música, dispara SFX, muda estado."""
        if self.score > self.high_score:
            self.high_score = self.score
        self._parar_musica()
        self._tocar_som("morte")
        self.estado = GameState.GAME_OVER

    def _ir_para_vitoria(self) -> None:
        """Vitória: atualiza high_score, para música, dispara jingle, muda estado."""
        if self.score > self.high_score:
            self.high_score = self.score
        self._parar_musica()
        self._tocar_som("vitoria")
        self.estado = GameState.VITORIA

    def _ir_para_menu(self) -> None:
        """Para a música atual, transita para MENU e toca a trilha do menu."""
        self._parar_musica()
        self.estado = GameState.MENU
        self._tocar_musica(config.MUSICA_MENU, self._VOL_MUSICA_MENU)
        # Prepara menu: seleção volta ao início, Continuar reflete save atual
        self._menu.reset(tem_save=self._save.exists())

    def _ir_para_pausado(self) -> None:
        """
        Pausa o jogo: transita para PAUSADO e prepara o menu de pausa.

        A física congela automaticamente porque update() tem guard
        'if self.estado is not GameState.JOGANDO: return'.
        _draw_jogo() continua sendo chamado como fundo visual.
        """
        self.estado = GameState.PAUSADO
        self._pause.reset()
        # Gancho de áudio futuro:
        # self._tocar_som('pause_open')

    def _retornar_ao_jogo(self) -> None:
        """Retoma o jogo a partir da pausa sem perder nenhum progresso."""
        self.estado = GameState.JOGANDO
        # Gancho de áudio futuro:
        # self._tocar_som('pause_close')

    def _ir_para_transicao_fase(self) -> None:
        """
        ⟨futuro⟩ Efeito visual de transição entre fases.

        Implementação futura
        ─────────────────────
        • _avancar_fase() chama este método antes de _resetar_jogo().
        • Um timer controla a duração do efeito (corte, fade, wipe).
        • Ao expirar, _resetar_jogo() é chamado e estado volta a JOGANDO.

        O método existe agora para que _avancar_fase() possa
        referenciar GameState.TRANSICAO_FASE sem retrabalho futuro.
        """
        # self.estado = GameState.TRANSICAO_FASE   # descomentar quando implementar
        pass   # no-op até implementação — _avancar_fase() vai direto

    # ══════════════════════════════════════════════════════════════════
    # GHOST EFFECT (AFTERIMAGES)
    # ══════════════════════════════════════════════════════════════════

    def _capturar_ghost(self) -> None:
        """
        Captura o frame visual atual do jogador como uma afterimage.

        Por que capturar via draw() num Rect temporário?
        ─────────────────────────────────────────────────
        O player.draw() aplica Squash & Stretch e o Damage Flash —
        o ghost deve refletir o visual FINAL do frame, não o frame
        bruto da spritesheet. Renderizamos num Surface temporário
        do tamanho do collider e pedimos ao player que desenhe nele.

        Por que Surface separada e não referência ao atlas?
        ─────────────────────────────────────────────────────
        Referências ao atlas compartilham o buffer da imagem —
        set_alpha() numa referência afetaria o sprite original.
        Uma cópia (.copy()) é necessária para alpha independente.

        Limite _GHOST_MAX previne vazamento de memória:
        Se o jogador ficar em alta velocidade indefinidamente,
        a lista não crescerá além de _GHOST_MAX entradas.

        A posição é capturada em world-space (player.rect.x/y) —
        a câmera aplicará o offset correto no draw, assim como
        faz com todos os outros sprites.
        """
        if len(self._ghosts) >= self._GHOST_MAX:
            return   # lista cheia — descarta o fantasma mais novo (mais recente)

        # Surface temporária com suporte a SRCALPHA para set_alpha funcionar
        w = self.player.WIDTH
        h = self.player.HEIGHT
        surf_ghost = pygame.Surface((w, h), pygame.SRCALPHA)

        # Rect de destino dentro da Surface temporária (posição local: 0, 0)
        rect_local = pygame.Rect(0, 0, w, h)

        # Renderiza o frame atual (com S&S e flash) na Surface temporária
        self.player.draw(surf_ghost, rect_local)

        self._ghosts.append({
            "surf":  surf_ghost,
            "x":     float(self.player.rect.x),    # world-space
            "y":     float(self.player.rect.y),    # world-space
            "alpha": float(self._GHOST_ALPHA_INICIAL),
        })

    def _atualizar_ghosts(self, dt: float) -> None:
        """
        Decrementa o alpha de cada fantasma e remove os que morreram.

        Decay linear por dt
        ────────────────────
        alpha -= _GHOST_ALPHA_DECAY × dt

        Com _GHOST_ALPHA_INICIAL=140 e _GHOST_ALPHA_DECAY=560:
          t=0.00 → alpha=140  (nasce com ~55% de opacidade)
          t=0.12 → alpha=73   (meia vida)
          t=0.25 → alpha=0    (desaparece após ~0.25 segundos)

        List comprehension remove fantasmas mortos sem loop explícito.
        O custo é O(n) onde n ≤ _GHOST_MAX — sempre limitado.
        """
        for g in self._ghosts:
            g["alpha"] = max(0.0, g["alpha"] - self._GHOST_ALPHA_DECAY * dt)

        # Remove mortos (alpha == 0)
        self._ghosts = [g for g in self._ghosts if g["alpha"] > 0]

    # ══════════════════════════════════════════════════════════════════
    # SCREEN SHAKE
    # ══════════════════════════════════════════════════════════════════

    def disparar_shake(
        self,
        duracao:     float = 0.30,
        intensidade: int   = 8,
    ) -> None:
        """
        Ativa o efeito de tremor de tela (screen shake).

        Screen shake é um dos recursos de game feel mais eficazes:
        um impacto físico no mundo do jogo causa um impacto perceptual
        na câmera — o jogador SENTE o dano, não apenas o vê no HUD.
        Usado em jogos desde os anos 80 (ex.: Earthworm Jim, Mega Man X).

        Implementação: deslocamento aleatório a cada frame
        ──────────────────────────────────────────────────
        Enquanto shake_timer > 0, _draw_jogo() sorteia um offset em X e Y
        dentro de [-intensidade, +intensidade] e desloca todos os blits do
        cenário por esse vetor. O offset é RE-SORTEADO a cada frame (não
        interpolado) — isso produz o tremor irregular característico do
        efeito "câmera de impacto", em vez de uma oscilação suave.

        Por que deslocar os blits e não mover a câmera?
        ─────────────────────────────────────────────────
        Mover self.camera.offset_x afetaria a física (retângulos de
        colisão lidos pela câmera ficariam desalinhados). Aplicar o
        deslocamento apenas nos blits mantém physics e visuals separados:
        a câmera em world-space não muda; só o que é desenhado na tela.

        Parâmetros
        ──────────
        duracao     : segundos de tremor (0.30 s ≈ 18 frames a 60 FPS)
        intensidade : deslocamento máximo em pixels por frame
                      Valores recomendados por tipo de evento:
                        dano leve    → intensidade=5,  duracao=0.20
                        dano grave   → intensidade=8,  duracao=0.30  ← padrão
                        explosão     → intensidade=14, duracao=0.45
                        game over    → intensidade=12, duracao=0.50
        """
        self.shake_timer       = duracao
        self.shake_intensidade = intensidade

    def disparar_hit_stop(self, duracao: float | None = None) -> None:
        """
        Congela a simulação por ``duracao`` segundos.

        O congelamento funciona por bypass de update(): enquanto
        hit_stop_timer > 0, o método update() decrementa o timer e
        retorna antes de executar qualquer física ou lógica de jogo.
        O draw() continua rodando normalmente a cada frame — o estado
        congelado é exibido repetidamente na tela, criando a sensação
        de "pausa dramática" sem bloquear o processo.

        O timer é decrementado ANTES do guard de estado em update()
        para sobreviver a transições (ex.: o freeze de game over continua
        ativo enquanto a tela de derrota surge).

        Parâmetros
        ──────────
        duracao : segundos de congelamento. None usa _HIT_STOP_DANO.
                  Use _HIT_STOP_STOMP para pisões (feedback mais leve).
        """
        self.hit_stop_timer = duracao if duracao is not None else self._HIT_STOP_DANO

    # ══════════════════════════════════════════════════════════════════
    # SAÍDA DE FASE
    # ══════════════════════════════════════════════════════════════════

    def _checar_colisao_saida(self) -> None:
        """
        Detecta se o Player tocou a SaidaFase e, se sim, conclui a fase.

        Proteções
        ─────────
        • fast-path se saida_sprite vazio (fase sem saída)
        • _fase_concluida garante disparo único por nível:
          mesmo que spritecollide() retorne True em múltiplos frames
          consecutivos (jogador parado sobre a saída), _concluir_fase()
          só é chamado uma vez.

        Por que não dokill=True?
        ─────────────────────────
        Se dokill=True removesse o sprite, num frame de alta latência
        o grupo ficaria vazio antes de _concluir_fase() terminar.
        _fase_concluida é a proteção correta — o sprite permanece
        até _construir_nivel() esvaziar o grupo no próximo nível.
        """
        if not self.saida_sprite or self._fase_concluida:
            return

        tocou = pygame.sprite.spritecollide(
            self.player, self.saida_sprite, dokill=False
        )
        if tocou:
            self._fase_concluida = True
            self._concluir_fase()

    def _concluir_fase(self) -> None:
        """
        Ponto único de decisão de fim de fase.

        Chamado por:
          • _checar_colisao_saida()  — quando o player toca a SaidaFase
          • update() inline          — fallback legado (fases sem saída,
                                       trigger por moedas zeradas)

        Lógica
        ───────
        Fase intermediária (fase_atual < TOTAL_FASES):
            → _avancar_fase(): preserva score, reconstrói nível, SFX.
        Última fase (fase_atual == TOTAL_FASES):
            → _ir_para_vitoria(): salva high_score, toca jingle, muda estado.

        Por que centralizar aqui?
        ──────────────────────────
        Antes desta refatoração, a lógica if/else estava inline em update().
        Centralizar elimina duplicação caso surja um terceiro trigger
        (ex: boss derrotado, timer esgotado) — basta chamar _concluir_fase().
        """
        # ── Telemetria: fecha coleta antes de avançar ───────────
        self._tel.finalizar_fase(self.fase_atual)
        # Save automático ao concluir fase (antes de avançar)
        self._salvar_jogo()

        if self.fase_atual < self.TOTAL_FASES:
            self._avancar_fase()
        else:
            self._ir_para_vitoria()
            self._tel.resumo_sessao()

    # ══════════════════════════════════════════════════════════════════
    # COLISÕES DE CHECKPOINT
    # ══════════════════════════════════════════════════════════════════

    def _checar_colisao_checkpoints(self) -> None:
        """
        Verifica colisão do Player com cada Checkpoint e ativa os tocados.

        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        REGRA DE ATIVAÇÃO
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

        1. Apenas checkpoints ainda não ativos geram mudança de estado.
           Checkpoints já ativos são ignorados — sem efeito colateral,
           sem custo de escrita, sem alteração do _checkpoint_respawn.

        2. Ao ativar: salva (respawn_x, respawn_y) do sprite em
           _checkpoint_respawn_x / _checkpoint_respawn_y, sobrescrevendo
           qualquer valor anterior. Isso implementa "o checkpoint mais
           recente vence" sem nenhuma estrutura de dados extra.

        3. Múltiplos checkpoints colididos no mesmo frame: todos são
           ativados, mas apenas o último processado pelo loop salva o
           respawn. Na prática, checkpoints nunca se sobrepõem — essa
           situação só ocorre em mapas mal construídos.

        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        POR QUE NÃO USAR spritecollide() COM dokill=False?
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

        spritecollide() retornaria apenas os checkpoints que colidem
        neste frame — correto para a ativação, mas perderia o checkpoint
        mais recente já ativo nos frames sem colisão. Salvar o respawn
        diretamente em _checkpoint_respawn_x/y (e não num sprite) é
        mais simples: o dado persiste entre frames sem precisar recolidir.

        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        O PLAYER NÃO SABE QUE CHECKPOINTS EXISTEM
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

        Toda lógica de ativação e salvamento de respawn vive aqui.
        player.py não importa Checkpoint, não lê checkpoints e não
        expõe nenhum atributo relacionado a respawn.
        """
        if not self.checkpoints:
            return   # fase sem checkpoints — fast-path sem iteração

        tocados = pygame.sprite.spritecollide(
            self.player, self.checkpoints, dokill=False
        )

        for cp in tocados:
            if cp.ativo:
                continue   # já ativo: ignora sem efeito colateral

            # ── Rebaixa checkpoints anteriores visualmente ─────────────
            # Todos os checkpoints já ativos passam para estado 'anterior'
            # (verde apagado) — apenas o recém-tocado fica amarelo.
            # self.ativo permanece True em todos — o respawn correto é
            # determinado por _checkpoint_respawn_x/y, não pelo visual.
            for outro_cp in self.checkpoints:
                if outro_cp is not cp and outro_cp.ativo:
                    outro_cp.marcar_como_anterior()

            cp.ativar()
            # Salva posição de respawn: o checkpoint mais recente vence.
            self._checkpoint_respawn_x = cp.respawn_x
            self._checkpoint_respawn_y = cp.respawn_y
            self._tel.registrar_checkpoint()
            # Save automático ao ativar checkpoint
            self._salvar_jogo()

    # ══════════════════════════════════════════════════════════════════
    # COLISÕES DE COMBATE
    # ══════════════════════════════════════════════════════════════════

    def _checar_colisao_inimigos(self) -> None:
        """
        Avalia cada colisão jogador ↔ inimigo e aplica o desfecho.

        Pisão (stomp) — condições simultâneas obrigatórias
        ────────────────────────────────────────────────────
          1. player.vel_y > 0            → caindo (nunca subindo)
          2. player.rect.bottom ≤ centery → base do jogador acima da
                                            linha média do inimigo

        O limiar centery (e não rect.top) concede tolerância de metade
        da altura do inimigo — evita falsos negativos em frames de alta
        velocidade onde o jogador "pula" o pixel exato do topo.

        Resultado de pisão confirmado
        ──────────────────────────────
          • inimigo.kill()                 — remove de todos os grupos
          • score += 50
          • vel_y = PLAYER_STOMP_BOUNCE    — impulso para cima (negativo)
          • no_chao = False                — retoma gravidade imediatamente
          • SFX "stomp"

        Resultado de toque lateral/inferior
        ─────────────────────────────────────
          • _ir_para_game_over()

        Nota de segurança de iteração
        ───────────────────────────────
        spritecollide() retorna uma lista (cópia) — inimigo.kill() dentro
        do loop não modifica o iterador. Seguro sem list() extra.
        """
        colididos = pygame.sprite.spritecollide(
            self.player, self.inimigos, dokill=False
        )
        if not colididos:
            return

        p           = self.player
        pisou_algum = False

        for inimigo in colididos:
            caindo          = p.vel_y > 0
            base_acima_meio = p.rect.bottom <= inimigo.rect.centery

            if caindo and base_acima_meio:
                inimigo.kill()
                self.score   += 50
                p.vel_y       = config.PLAYER_STOMP_BOUNCE
                p.no_chao     = False
                pisou_algum   = True
                self._tocar_som("stomp")
                self.disparar_hit_stop(self._HIT_STOP_STOMP)   # pausa de vitória

        if not pisou_algum:
            # ── Toque lateral ou por baixo — tomar_dano() decide ─────────
            # tomar_dano() retorna False se o jogador já está invulnerável
            # (i-frames ativos) — nenhuma vida é decrementada nem SFX tocado.
            # Retorna True apenas se o dano foi efetivamente aplicado.
            inimigo_origem_x = tocados[0].rect.centerx if tocados else None
            if self.player.tomar_dano(inimigo_origem_x):
                # Player.vida_atual é a fonte canônica; sincroniza self.vidas
                # para que HUD e _resetar_jogo continuem funcionando.
                self.vidas = self.player.vida_atual
                self._tocar_som("morte")
                self.disparar_shake()
                self.disparar_hit_stop()   # pausa de dano — usa _HIT_STOP_DANO
                self._tel.registrar_dano()

                if self.player.morto:
                    # Último coração: shake mais intenso antes do game over
                    self.disparar_shake(duracao=0.50, intensidade=12)
                    self._tel.registrar_morte(
                        self.player.rect.centerx,
                        self.player.rect.centery,
                    )
                    self._ir_para_game_over()
                # Com vidas restantes: jogador recebe knockback (aplicado em
                # tomar_dano()) e fica invulnerável por INVULNERAVEL_DURATION —
                # sem transição de estado, o jogo continua.

    # ══════════════════════════════════════════════════════════════════
    # 1. EVENTOS — roteados pelo estado atual da FSM
    # ══════════════════════════════════════════════════════════════════

    def handle_events(self) -> None:
        """
        Lê e roteia todos os eventos do frame atual.

        Regra: nunca modifica variáveis de física, nunca chama draw(),
        nunca avança o tempo. Apenas lê intenções e dispara transições.

        Estrutura do loop
        ──────────────────
        QUIT e K_ESCAPE são processados e encerram o jogo imediatamente
        com break (não return) — o loop de eventos continua para processar
        os demais eventos pendentes do mesmo frame antes de sair.

        Os demais eventos são roteados pelo estado atual. Eventos não
        relevantes para o estado corrente são silenciosamente ignorados.
        """
        for event in pygame.event.get():

            # ── Saída global (qualquer estado) ────────────────────────
            if event.type == pygame.QUIT:
                self.running = False
                break   # encerra o loop; demais eventos são descartados

            # K_ESCAPE is handled per-state below (not globally)

            # ── Roteamento por estado ─────────────────────────────────
            if self.estado == GameState.MENU:
                # ESC no menu fecha o jogo
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.running = False
                    break
                # Delega todos os outros eventos ao MenuPrincipal
                self._menu.processar_evento(event)

            elif self.estado == GameState.JOGANDO:
                # ESC durante gameplay → pausa
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self._ir_para_pausado()
                    break
                # Delega ao Player — ele filtra internamente por KEYDOWN
                self.player.handle_jump(event)
                self.player.handle_lingua(event)

            elif self.estado == GameState.PAUSADO:
                # Delega eventos ao menu de pausa
                self._pause.processar_evento(event)

            elif self.estado in (GameState.GAME_OVER, GameState.VITORIA):
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        self._resetar_jogo()
                        self._tocar_musica(config.MUSICA_FASE, self._VOL_MUSICA_FASE)
                    elif event.key == pygame.K_m:
                        self._ir_para_menu()

    # ══════════════════════════════════════════════════════════════════
    # 2. ATUALIZAÇÃO — física e lógica de jogo
    # ══════════════════════════════════════════════════════════════════

    def update(self, dt: float) -> None:
        """
        Avança o estado do mundo em dt segundos.

        Guarda antecipada: retorna imediatamente se estado ≠ "JOGANDO".
        Isso congela o mundo nos demais estados sem aninhamento.

        Ordem de operações dentro do estado JOGANDO
        ─────────────────────────────────────────────
        1. Timers globais  (shake, hit_stop — fora do guard de estado)
        2. Hit Stop guard  (bypassa simulação se congelado)
        3. Física do jogador   (movimento + colisão com plataformas)
        4. Física dos inimigos (patrulha independente)
        5. SFX de pulo         (One-Frame Event Flag — lida e zerada aqui)
        6. Coleta de moedas    (score + SFX)
        7. Combate com inimigos (stomp ou tomar_dano + shake + hit_stop)
        8. Condição de vitória (verificada após coleta — score atualizado)
        9. Câmera              (sempre depois do jogador — posição final)
        """
        # ── Timers globais — decrementados em TODOS os estados ─────────
        # Shake e Hit Stop são disparados durante JOGANDO mas devem
        # continuar (e expirar corretamente) durante GAME_OVER/VITORIA.
        if self.shake_timer > 0.0:
            self.shake_timer = max(0.0, self.shake_timer - dt)

        if self.hit_stop_timer > 0.0:
            self.hit_stop_timer = max(0.0, self.hit_stop_timer - dt)
            # ── Bypass de simulação: frame congelado na tela ──────────
            # draw() continua rodando → o frame atual permanece visível.
            # handle_events() já processou inputs neste frame → ESC/fechar
            # funcionam normalmente durante o congelamento.
            # Partículas, física e câmera são ignorados até o timer zerar.
            return

        # ── Processamento de ação da pausa ────────────────────────────
        if self.estado is GameState.PAUSADO:
            self._pause.update(dt)
            acao_pause = self._pause.obter_acao()
            if acao_pause is OpcaoPause.RETORNAR:
                self._retornar_ao_jogo()
            elif acao_pause is OpcaoPause.REINICIAR_FASE:
                self._resetar_jogo(reiniciar_campanha=False)
                self._retornar_ao_jogo()
            elif acao_pause is OpcaoPause.MENU_PRINCIPAL:
                self._ir_para_menu()
            elif acao_pause is OpcaoPause.SAIR:
                self._salvar_jogo()
                self.running = False
            return   # pausa não executa física

        # ── Processamento de ação do menu ─────────────────────────────
        # Verificado antes do guard de JOGANDO para que a transição
        # ocorra no mesmo frame em que a tecla foi pressionada.
        if self.estado is GameState.MENU:
            self._menu.update(dt)
            acao = self._menu.obter_acao()
            if acao is OpcaoMenu.NOVO_JOGO:
                self._executar_novo_jogo()
            elif acao is OpcaoMenu.CONTINUAR:
                self._executar_continuar()
            elif acao is OpcaoMenu.SAIR:
                self._salvar_jogo()
                self.running = False
            return   # menu não executa física

        # dt armazenado para acesso em subsistemas chamados por índice
        self._dt_last: float = dt

        # Acumula tempo de sessão (apenas em gameplay ativo)
        if self.estado is GameState.JOGANDO:
            self._tempo_jogado += dt

        if self.estado is not GameState.JOGANDO:
            return

        # ── Física ────────────────────────────────────────────────────
        # Plataformas móveis se movem ANTES do Player — o AABB do Player
        # em player.update() usa a posição atualizada deste frame.
        self.plataformas_moveis_group.update(dt)

        self.player.update(dt, self.plataformas)

        # ── Verificação de morte (rota alternativa) ───────────────────
        # player.morto pode ser setado por qualquer sistema futuro
        # (perda de cauda, queda fora do mapa, veneno, etc.) sem passar
        # por _checar_colisao_inimigos. Verificamos aqui para que TODOS
        # os caminhos para morte convirjam no mesmo ponto.
        #
        # _checar_colisao_inimigos() também chama _ir_para_game_over()
        # diretamente — a verificação abaixo cobre apenas os casos em que
        # morto=True foi setado SEM que _ir_para_game_over() já tenha sido
        # chamado (ex: sistema futuro de cauda seta morto mas não chama a
        # transição). A guarda `estado is JOGANDO` evita dupla transição.
        # ── Transporte por plataforma móvel ───────────────────────────
        # Verifica se o Player está apoiado sobre alguma plataforma móvel.
        # Se sim, aplica o delta deste frame diretamente em x/y do Player
        # sem alterar vel_x / vel_y — o Player é um passageiro.
        #
        # Detecção: player.no_chao=True E rect.bottom toca o rect.top da
        # plataforma (tolerância ±2px para variação de arredondamento float→int).
        if self.player.no_chao:
            for pm in self.plataformas_moveis_group:
                if abs(self.player.rect.bottom - pm.rect.top) <= 2:
                    if (self.player.rect.right > pm.rect.left and
                            self.player.rect.left < pm.rect.right):
                        # Aplica deslocamento: reposiciona sem modificar vel
                        self.player.x      += pm.delta_x
                        self.player.rect.x  = int(self.player.x)
                        self.player.y      += pm.delta_y
                        self.player.rect.y  = int(self.player.y)
                        break   # apenas uma plataforma por frame

        # ── Autotomia — One-Frame Flag ─────────────────────────────────
        if self.player.just_lost_tail:
            self.disparar_shake(
                duracao    = self.player.TAIL_SHAKE_DURATION,
                intensidade= self.player.TAIL_SHAKE_INTENSITY,
            )
            px, py = self.player.rect.midbottom
            self.particulas.adicionar_varias(
                emitir_cauda_break(px, py, self.player.virado_direita)
            )

        if self.player.morto and self.estado is GameState.JOGANDO:
            self._ir_para_game_over()
            return

        self.inimigos.update(dt)
        self.insetos.update(dt)

        # ── Armadilhas — update + colisão com player ─────────────────
        for armadilha in self.armadilhas:
            armadilha.update(dt, self.player.rect)

            # if armadilha.just_activated:
            #     self.disparar_shake(duracao=0.1, intensidade=4)

            if armadilha.is_dangerous() and armadilha.rect.colliderect(self.player.rect):
                origem_x = float(armadilha.rect.centerx)
                if self.player.tomar_dano(origem_x):
                    self.vidas = self.player.vida_atual
                    self._tocar_som("morte")
                    self.disparar_shake()
                    self.disparar_hit_stop()
                    self._tel.registrar_dano()
                    if self.player.morto:
                        self.disparar_shake(duracao=0.50, intensidade=12)
                        self._tel.registrar_morte(
                            self.player.rect.centerx,
                            self.player.rect.centery,
                        )
                        self._ir_para_game_over()

        # ── Captura de insetos pela língua ────────────────────────────
        # Verifica colisão hitbox da língua com rect de cada inseto.
        # ao_tocar_interagivel() inicia retração; ser_capturado() remove.
        lingua_hitbox = self.player.lingua.hitbox
        if lingua_hitbox:
            for inseto in list(self.insetos):
                if inseto.ativo and lingua_hitbox.colliderect(inseto.rect):
                    self.player.lingua.ao_tocar_interagivel(inseto)
                    self.score += inseto.VALOR
                    inseto.ser_capturado()

        # ── Língua — atualização de estado e hitbox ──────────────────
        # Passa a origem atual da boca do calango para que a língua
        # siga o Player durante a extensão sem lag visual.
        if self.player.virado_direita:
            boca_x = float(self.player.rect.right)
        else:
            boca_x = float(self.player.rect.left)
        boca_y = float(self.player.rect.centery)
        self.player.lingua.update(dt, boca_x, boca_y)

        # ⟨futuro: colisão da língua com interagíveis⟩
        # hitbox = self.player.lingua.hitbox
        # if hitbox:
        #     tocados = [s for s in self.insetos if hitbox.colliderect(s.rect)]
        #     for obj in tocados:
        #         self.player.lingua.ao_tocar_interagivel(obj)
        #         obj.ser_capturado()

        # ── Landing Impact — Fase 1 do Game Feel ──────────────────────
        # Lê a flag Edge-Triggered do Player (dura exatamente 1 frame).
        # O Player registra o evento; o Game decide a resposta visual.
        #
        # Pipeline de decisão:
        #   just_landed?          → houve transição ar→chão neste frame
        #   vel_impacto > limiar? → a queda foi significativa
        #   clamp(vel × fator)    → converte física em feel proporcional
        #   disparar_shake()      → feedback tátil
        #
        # Por que clamp e não apenas multiplicação linear?
        # ────────────────────────────────────────────────
        # Uma queda a terminal velocity (900 px/s) × 0.015 = 13.5 px.
        # Sem o clamp superior (10 px), quedas extremas ou bugs de
        # física (vel_y > terminal por 1 frame) gerariam shakes
        # desproporcionais. Com clamp: o feel é previsível e controlado
        # independente de qualquer anomalia na física.
        if self.player.just_landed:
            vel_impacto = self.player.velocidade_impacto   # Read-Only
            if vel_impacto >= self._LANDING_VY_THRESHOLD:
                intensidade_bruta = vel_impacto * self._LANDING_SHAKE_FATOR
                intensidade = int(max(
                    self._LANDING_SHAKE_MIN,
                    min(intensidade_bruta, self._LANDING_SHAKE_MAX),
                ))
                self.disparar_shake(
                    duracao     = self._LANDING_SHAKE_DURACAO,
                    intensidade = intensidade,
                )

            # ── Landing Dust ──────────────────────────────────────────
            # Emitido sempre que pousa — mesmo quedas leves geram poeira.
            # A quantidade escala com vel_impacto via emitir_landing_dust().
            px, py = self.player.rect.midbottom
            self.particulas.adicionar_varias(
                emitir_landing_dust(px, py, vel_impacto)
            )

        # ── SFX de pulo ───────────────────────────────────────────────
        if self.player.pulou:
            self._tocar_som("pulo")
            self.player.pulou = False
            self._tel.registrar_pulo()
            if abs(self.player.vel_x) >= config.PLAYER_WALL_JUMP_FORCE:
                self._tel.registrar_wall_jump()

            # ── Jump Dust ─────────────────────────────────────────────
            # Emitido exatamente no frame do pulo (mesma flag que o SFX).
            # vel_x do player é Read-Only — lufada levemente contrária ao movimento.
            px, py = self.player.rect.midbottom
            self.particulas.adicionar_varias(
                emitir_jump_dust(px, py, self.player.vel_x)
            )

        # ── Telemetria: escalada (edge-detector interno no módulo) ──
        self._tel.registrar_escalada(self.player.escalando)

        # ── Run Dust — emissão contínua ritmada ───────────────────────
        # Lê poeira_corrida_timer (cosmético, decrementado em player.py).
        # Quando zera: emite 1 partícula e reinicia o timer.
        # abs(vel_x) > threshold evita poeira ao andar lentamente.
        if (self.player.no_chao
                and abs(self.player.vel_x) > RUN_VEL_THRESHOLD
                and self.player.poeira_corrida_timer <= 0.0):
            px, py   = self.player.rect.midbottom
            direcao  = 1.0 if self.player.vel_x > 0 else -1.0
            self.particulas.adicionar_varias(
                emitir_run_dust(px, py, direcao)
            )
            # Reinicia timer no player (única escrita externa permitida —
            # é um campo cosmético exposto intencionalmente para este propósito)
            self.player.poeira_corrida_timer = RUN_INTERVALO

        # ── Atualiza partículas ───────────────────────────────────────
        self.particulas.atualizar(dt)

        # ── Coleta de moedas ──────────────────────────────────────────
        coletadas = pygame.sprite.spritecollide(
            self.player, self.moedas, dokill=True
        )
        if coletadas:
            self.score += len(coletadas) * Moeda.VALOR
            for _ in coletadas:
                self._tel.registrar_moeda()
                self._moedas_coletadas_total += 1
            self._tocar_som("moeda")

        # ── Ativação de checkpoints ───────────────────────────────────
        # Verificado antes do combate para que um checkpoint ativado no
        # mesmo frame de um dano ainda salve a posição de respawn.
        self._checar_colisao_checkpoints()

        # ── Combate com inimigos ──────────────────────────────────────
        self._checar_colisao_inimigos()

        # ── Saída de fase ─────────────────────────────────────────────
        # Verificado após combate: um jogador que morre e toca a saída
        # no mesmo frame deve morrer, não concluir a fase.
        self._checar_colisao_saida()

        # ── Condição de fim de fase — legado (moedas) ───────────────────
        # Ativo apenas em fases SEM saída configurada (saida_sprite vazio).
        # Em fases com saída, o trigger é _checar_colisao_saida() acima.
        # Preservado integralmente para compatibilidade com mapas antigos.
        if not self.saida_sprite and not self.moedas:
            self._concluir_fase()
            return   # câmera não precisa atualizar — frame de transição

        # ── Câmera com bias preditivo ─────────────────────────────────
        # update_com_bias() em vez de update() — mesma lógica de clamp,
        # mais bias suave proporcional à velocidade horizontal do calango.
        self.camera.update_com_bias(
            self.player.rect,
            vel_x  = self.player.vel_x,
            dt     = dt,
            fator  = self._CAMERA_BIAS_FATOR,
            lerp   = self._CAMERA_BIAS_LERP,
            max_px = self._CAMERA_BIAS_MAX,
        )

        # ── Ghost Effect — captura de afterimage ──────────────────────
        # Condições: alta velocidade horizontal OU queda rápida.
        # Não captura durante Hit Stop (timer decrementado antes do guard).
        vel_x_abs = abs(self.player.vel_x)
        vel_y_cai = self.player.vel_y

        em_alta_vel = (
            vel_x_abs >= self._GHOST_VX_THRESHOLD
            or vel_y_cai >= self._GHOST_VY_THRESHOLD
        )

        self._ghost_timer = max(0.0, self._ghost_timer - dt)

        if em_alta_vel and self._ghost_timer <= 0.0:
            self._capturar_ghost()
            self._ghost_timer = self._GHOST_INTERVALO

        # Decaimento de alpha e remoção de fantasmas mortos
        self._atualizar_ghosts(dt)

        # ── Fall Wind Dust — rastro de atrito de ar ───────────────────
        self._wind_timer = max(0.0, self._wind_timer - dt)
        if (
            vel_y_cai >= self._WIND_VY_THRESHOLD
            and not self.player.no_chao
            and self._wind_timer <= 0.0
        ):
            px_w, py_w = self.player.rect.midbottom
            self.particulas.adicionar_varias(
                emitir_rastro_vento(
                    float(px_w), float(py_w),
                    largura_corpo=float(self.player.WIDTH),
                )
            )
            self._wind_timer = self._WIND_INTERVALO

    # ══════════════════════════════════════════════════════════════════
    # 3. RENDERIZAÇÃO — roteada pelo estado atual da FSM
    # ══════════════════════════════════════════════════════════════════

    def draw(self) -> None:
        """
        Roteia a renderização para o método correto.

        Regra: nunca lê input, nunca muda estado, nunca avança física.

        GAME_OVER e VITORIA desenham o cenário congelado ao fundo antes
        do overlay e do painel — fornece contexto visual sem distrair.
        """
        if self.estado == GameState.MENU:
            self._draw_menu()

        elif self.estado == GameState.JOGANDO:
            self._draw_jogo()
            self._draw_hud()

        elif self.estado == GameState.GAME_OVER:
            self._draw_jogo()
            self._draw_overlay()
            self._draw_game_over()

        elif self.estado == GameState.VITORIA:
            self._draw_jogo()
            self._draw_overlay()
            self._draw_vitoria()

        elif self.estado == GameState.PAUSADO:
            # Cenário congelado ao fundo + overlay + painel de pausa
            self._draw_jogo()
            self._pause.draw(self.screen)

        elif self.estado == GameState.TRANSICAO_FASE:
            # ⟨futuro⟩ — efeito visual entre fases
            self._draw_jogo()
            # self._draw_transicao_fase()   # descomentar quando implementar

        pygame.display.flip()

    # ------------------------------------------------------------------
    # Rotinas de renderização por estado
    # ------------------------------------------------------------------

    def _draw_menu(self) -> None:
        """Delega a renderização do menu ao módulo menu_principal."""
        self._menu.draw(self.screen)

    def _draw_jogo(self) -> None:
        """
        Renderiza o cenário completo com offset de câmera e screen shake.

        Pipeline de transformação por sprite
        ─────────────────────────────────────
        world-space (rect)
            ↓  Camera.aplicar()     → subtrai offset_x da câmera
        screen-space (rect_tela)
            ↓  .move(ox, oy)        → desloca pelo vetor de shake
        draw-space (rect_final)
            ↓  surface.blit()       → pixel na tela

        Camera.aplicar() retorna um novo Rect sem modificar o original —
        world-space intocado para a física. .move() também retorna um
        novo Rect — screen-space intocado para o HUD (que não tremula).

        Por que o HUD NÃO treme?
        ──────────────────────────
        _draw_hud() é chamado APÓS _draw_jogo() e usa coordenadas fixas
        de screen-space (não passa por esta função). Tremular o HUD seria
        desorientador — o jogador precisa ler as vidas mesmo durante o
        impacto. Separar os dois draws resolve o problema naturalmente.

        Por que random.randint e não seno/cosseno?
        ────────────────────────────────────────────
        Tremor senoidal produz oscilação suave e previsível — parece
        uma câmera em movimento, não um impacto. random.randint gera
        deslocamentos completamente irregulares a cada frame — parece
        um choque físico real. Para screen shake de dano, o ruído
        aleatório é sempre preferível à oscilação periódica.
        """
        self.screen.fill(config.SKY_BLUE)

        # ── Vetor de shake ────────────────────────────────────────────
        # Sorteado uma vez por frame e reutilizado em todos os blits —
        # garante que todos os elementos se movem juntos (coerência visual).
        # Se sorteássemos individualmente por sprite, cada objeto tremeria
        # em direções diferentes — efeito de "tela estilhaçada", não tremor.
        if self.shake_timer > 0.0:
            ox = random.randint(-self.shake_intensidade, self.shake_intensidade)
            oy = random.randint(-self.shake_intensidade, self.shake_intensidade)
        else:
            ox, oy = 0, 0   # sem shake: deslocamento nulo

        # ── Renderização com offset ───────────────────────────────────
        # camera.aplicar(rect)  →  screen-space
        # .move(ox, oy)         →  screen-space + shake  (novo Rect, sem mutação)
        for spr in self.plataformas:
            self.screen.blit(spr.image, self.camera.aplicar(spr.rect).move(ox, oy))

        for spr in self.moedas:
            self.screen.blit(spr.image, self.camera.aplicar(spr.rect).move(ox, oy))

        for spr in self.inimigos:
            self.screen.blit(spr.image, self.camera.aplicar(spr.rect).move(ox, oy))

        # ── Saída de fase — renderizada antes dos checkpoints ───────────
        # Fica na mesma camada de checkpoints (atrás do player e ghosts).
        # O grupo tem 0 ou 1 elemento — loop é inofensivo se vazio.
        for spr in self.saida_sprite:
            self.screen.blit(spr.image, self.camera.aplicar(spr.rect).move(ox, oy))

        # ── Plataformas móveis — antes de checkpoints e player ───────
        for spr in self.plataformas_moveis_group:
            self.screen.blit(spr.image, self.camera.aplicar(spr.rect).move(ox, oy))

        # ── Checkpoints — renderizados entre inimigos e ghost effect ──
        # Ficam atrás do Player e dos ghosts mas na frente das moedas.
        # Como SRCALPHA, pixels transparentes não cobrem nada.
        for spr in self.checkpoints:
            self.screen.blit(spr.image, self.camera.aplicar(spr.rect).move(ox, oy))

        # ── Ghost Effect — renderizado ANTES do player ────────────────
        # Os fantasmas ficam "atrás" do sprite real porque são blitados
        # primeiro — o player real sobrepõe as afterimages.
        #
        # Conversão world → screen para cada ghost:
        #   screen_x = ghost_x - camera.offset_x + ox  (shake)
        #   screen_y = ghost_y + oy
        #
        # set_alpha() modifica o estado da Surface — por isso cada ghost
        # tem sua própria cópia (não referência ao atlas compartilhado).
        #
        # Por que não usar .move() aqui?
        # ────────────────────────────────
        # Os ghosts não têm pygame.Rect — apenas (x, y) floats.
        # Calculamos screen_x/y diretamente em vez de criar Rects
        # temporários — mais simples e sem alocação desnecessária.
        for g in self._ghosts:
            alpha_int = int(g["alpha"])
            if alpha_int <= 0:
                continue
            g["surf"].set_alpha(alpha_int)
            sx = int(g["x"] - self.camera.offset_x) + ox
            sy = int(g["y"]) + oy
            self.screen.blit(g["surf"], (sx, sy))

        # ── Armadilhas — renderizadas antes dos insetos ──────────────
        for spr in self.armadilhas:
            self.screen.blit(spr.image, self.camera.aplicar(spr.rect).move(ox, oy))

        # ── Insetos — entre inimigos e língua ───────────────────────
        for spr in self.insetos:
            self.screen.blit(spr.image, self.camera.aplicar(spr.rect).move(ox, oy))

        # ── Língua — desenhada antes do player (atrás do sprite) ──────
        if self.player.lingua.ativa:
            # Origem em screen-space: lateral do rect + shake
            rect_screen = self.camera.aplicar(self.player.rect).move(ox, oy)
            if self.player.virado_direita:
                origem_screen = rect_screen.midright
            else:
                origem_screen = rect_screen.midleft
            self.player.lingua.draw(
                self.screen,
                origem_screen,
                cam_offset_x = self.camera.offset_x,
                cam_offset_y = 0.0,   # câmera apenas horizontal
                ox           = ox,
                oy           = oy,
            )

        self.player.draw(
            self.screen,
            self.camera.aplicar(self.player.rect).move(ox, oy),
        )

        # ── Partículas — world-space com câmera + shake ───────────────
        # offset_x total = camera.offset_x - ox (shake move tudo, incluindo partículas)
        # offset_y total = -oy (shake vertical; partículas em world-space não têm Y-scroll)
        # As partículas ficam "coladas no cenário", não na tela.
        self.particulas.desenhar(
            self.screen,
            offset_x = self.camera.offset_x - ox,
            offset_y = oy,
        )

    def _draw_hud(self) -> None:
        """
        Monta HudData com o estado atual do Game e delega ao módulo hud.py.
        Nenhuma lógica de desenho vive aqui.
        """
        checkpoint_ativo = (
            self._checkpoint_respawn_x is not None
            and self._checkpoint_respawn_y is not None
        )

        dados = HudData(
            fase_atual        = self.fase_atual,
            total_fases       = self.TOTAL_FASES,
            moedas_total      = self._total_moedas,
            moedas_restantes  = len(self.moedas),
            vidas             = self.vidas,
            vidas_max         = self.vidas_max,
            checkpoint_ativo  = checkpoint_ativo,
            tem_cauda         = self.player.tem_cauda,
            score             = self.score,
            fps               = self.clock.get_fps(),
            player_x          = self.player.x,
            player_y          = self.player.y,
            vel_x             = self.player.vel_x,
            vel_y             = self.player.vel_y,
            estado_jogo       = str(self.estado),
        )

        self._hud.draw(self.screen, dados)
    def _draw_overlay(self) -> None:
        """Aplica o overlay escuro pré-renderizado sobre o cenário congelado."""
        self.screen.blit(self._overlay, (0, 0))

    def _draw_game_over(self) -> None:
        """
        Painel de Game Over — cenário congelado ao fundo + overlay escuro.

        Layout (centro da tela):
          cy - 110  →  GAME OVER  (título vermelho grande)
          cy -  55  →  Fase N / T  (contexto da derrota)
          cy -  15  →  Larvas: N coletadas  (progresso na fase)
          cy +  20  →  Score: N
          cy +  60  →  High Score: N  /  ★ Novo High Score!
          cy + 110  →  [R] Tentar Novamente   [M] Menu

        Dados calculados aqui (não armazenados em atributo) para que
        o painel reflita sempre o estado real do momento da derrota
        sem necessidade de snapshot extra.
        """
        SW, SH = config.SCREEN_WIDTH, config.SCREEN_HEIGHT
        cx     = SW // 2
        cy     = SH // 2

        # ── Título ────────────────────────────────────────────────────
        self._texto(self._fonte_titulo, "GAME OVER",
                    config.RED, cx, cy - 110)

        # ── Contexto da derrota ───────────────────────────────────────
        self._texto(
            self._fonte_hud,
            f"Fase  {self.fase_atual} / {self.TOTAL_FASES}",
            (180, 180, 180), cx, cy - 55,
        )

        larvas_coletadas = self._total_moedas - len(self.moedas)
        if self._total_moedas > 0:
            self._texto(
                self._fonte_hud,
                f"Larvas coletadas: {larvas_coletadas} / {self._total_moedas}",
                (180, 220, 180), cx, cy - 15,
            )

        # ── Score ─────────────────────────────────────────────────────
        self._texto(self._fonte_subtitulo, f"Score: {self.score}",
                    config.WHITE, cx, cy + 20)

        if self.score > 0 and self.score >= self.high_score:
            self._texto(self._fonte_hud, "★  Novo High Score!  ★",
                        config.GOLD, cx, cy + 60)
        else:
            self._texto(self._fonte_subtitulo, f"High Score: {self.high_score}",
                        config.GOLD, cx, cy + 60)

        # ── Instrução ─────────────────────────────────────────────────
        self._texto(self._fonte_hud, "[R] Tentar Novamente      [M] Menu",
                    (200, 200, 200), cx, cy + 110)

    def _draw_vitoria(self) -> None:
        """Painel de vitória: título, score final, high score e instruções."""
        SW, SH = config.SCREEN_WIDTH, config.SCREEN_HEIGHT
        cx     = SW // 2
        cy     = SH // 2

        self._texto(self._fonte_titulo,    "VITÓRIA!",
                    config.YELLOW, cx, cy - 110)
        self._texto(self._fonte_subtitulo, "Todas as moedas coletadas!",
                    config.WHITE,  cx, cy - 25)
        self._texto(self._fonte_subtitulo, f"Score Final: {self.score}",
                    config.WHITE,  cx, cy + 20)

        if self.score >= self.high_score:
            self._texto(self._fonte_hud, "★  Novo High Score!  ★",
                        config.GOLD, cx, cy + 65)

        self._texto(self._fonte_hud, "[R] Jogar Novamente      [M] Menu",
                    (200, 200, 200), cx, cy + 115)

    # ------------------------------------------------------------------
    # Utilitário de texto com sombra
    # ------------------------------------------------------------------

    def _texto(
        self,
        fonte:  pygame.font.Font,
        texto:  str,
        cor:    tuple,
        x:      int,
        y:      int,
        ancora: str = "center",
    ) -> None:
        """
        Renderiza texto com sombra preta deslocada 2px para legibilidade.

        Por que renderizar duas vezes?
        ────────────────────────────────
        Texto colorido sobre fundo variável (céu, plataformas, inimigos)
        perde contraste. A sombra em preto a 2px garante legibilidade em
        qualquer cor de fundo ao custo de dois blits por chamada.

        Parâmetros
        ──────────
        fonte   : fonte pré-carregada (evita SysFont por frame)
        texto   : string a exibir
        cor     : cor principal (R, G, B)
        x, y    : posição de ancoragem em screen-space
        ancora  : atributo de Rect para alinhamento
                  ("center", "topright", "topleft", "midleft" …)
        """
        surf_texto  = fonte.render(texto, True, cor)
        surf_sombra = fonte.render(texto, True, config.BLACK)
        rect        = surf_texto.get_rect(**{ancora: (x, y)})

        self.screen.blit(surf_sombra, rect.move(2, 2))   # sombra levemente deslocada
        self.screen.blit(surf_texto,  rect)               # texto na posição exata

    # ══════════════════════════════════════════════════════════════════
    # GAME LOOP
    # ══════════════════════════════════════════════════════════════════

    # ══════════════════════════════════════════════════════════════════
    # AÇÕES DO MENU
    # ══════════════════════════════════════════════════════════════════

    def _executar_novo_jogo(self) -> None:
        """
        Fluxo de Novo Jogo:
          1. Apaga o save existente (reset total)
          2. Reseta contadores de sessão
          3. Inicia na fase 1 com vidas máximas
          4. Posiciona player no spawn original da fase
        """
        self._save.reset()               # apaga save anterior
        self._tempo_jogado           = 0.0
        self._moedas_coletadas_total = 0
        self._resetar_jogo(reiniciar_campanha=True)
        self._tocar_musica(config.MUSICA_FASE, self._VOL_MUSICA_FASE)

    def _executar_continuar(self) -> None:
        """
        Fluxo de Continuar:
          1. Carrega save (já aplicado em _carregar_save_se_existir no init)
          2. Reconstrói o nível da fase salva
          3. Reposiciona player no checkpoint salvo (se existir)

        Os dados do save já foram aplicados em __init__ via
        _carregar_save_se_existir → _apply_save_data, que definiu
        fase_atual, vidas e _checkpoint_respawn_x/y.
        _resetar_jogo(reiniciar_campanha=False) usa esses valores.
        """
        self._resetar_jogo(reiniciar_campanha=False)
        self._tocar_musica(config.MUSICA_FASE, self._VOL_MUSICA_FASE)

    # ══════════════════════════════════════════════════════════════════
    # SAVE GAME
    # ══════════════════════════════════════════════════════════════════

    def _build_save_data(self) -> dict:
        """
        Coleta o estado atual do Game em um dict de primitivos.

        Único ponto de coleta de dados de save — toda extensão futura
        (habilidades, skins, bestiário) adiciona campos aqui e em
        _apply_save_data(), sem tocar em save_manager.py.
        """
        return {
            "fase_atual":          self.fase_atual,
            "checkpoint_x":        self._checkpoint_respawn_x,
            "checkpoint_y":        self._checkpoint_respawn_y,
            "moedas_coletadas":     self._moedas_coletadas_total,
            "vidas":               self.vidas,
            "tempo_total_jogado":   self._tempo_jogado,
        }

    def _apply_save_data(self, dados: dict) -> None:
        """
        Aplica um dict de save ao estado do Game.

        Chamado após load() retornar dados válidos.
        Não chama _construir_nivel() — isso é feito pelo fluxo normal
        de inicialização que ocorre depois.
        """
        self.fase_atual                = int(dados["fase_atual"])
        self.vidas                     = int(dados["vidas"])
        self._moedas_coletadas_total   = int(dados["moedas_coletadas"])
        self._tempo_jogado             = float(dados["tempo_total_jogado"])

        cp_x = dados.get("checkpoint_x")
        cp_y = dados.get("checkpoint_y")
        # Checkpoint do save será aplicado em _resetar_jogo() quando
        # _checkpoint_respawn_x/y estiver definido.
        # Aqui apenas armazenamos — _construir_nivel() virá depois.
        if cp_x is not None and cp_y is not None:
            self._checkpoint_respawn_x = float(cp_x)
            self._checkpoint_respawn_y = float(cp_y)

    def _salvar_jogo(self) -> None:
        """
        Ponto único de save — coleta dados e delega ao SaveManager.

        Seguro chamar em qualquer estado: se o estado não for JOGANDO
        (ex: MENU, GAME_OVER), os dados ainda são válidos e persistem
        o progresso até o momento.
        """
        dados = self._build_save_data()
        ok = self._save.save(dados)
        if ok and self.DEBUG_MAPA:
            print(f"[Save] Salvo — Fase {dados['fase_atual']}, "
                  f"Vidas {dados['vidas']}, "
                  f"Tempo {dados['tempo_total_jogado']:.0f}s")

    def _carregar_save_se_existir(self) -> None:
        """
        Tenta carregar o save game ao iniciar.

        Se o save existir e for válido: aplica o progresso salvo.
        Se não existir ou for inválido: mantém o estado padrão
        (fase 1, vidas máximas, sem checkpoint).

        Chamado uma única vez em __init__(), depois de todos os
        atributos estarem inicializados.
        """
        dados = self._save.load()
        if dados is not None:
            self._apply_save_data(dados)
            print(f"[Save] Progresso restaurado — Fase {self.fase_atual}")
        else:
            print("[Save] Nenhum save encontrado. Iniciando novo jogo.")

    def run(self) -> None:
        """
        Loop principal — executa até self.running = False.

        clock.tick(FPS) dorme o tempo necessário para manter o FPS alvo
        e retorna os milissegundos reais desde o último frame.
        dt = ms / 1000 converte para segundos — unidade usada pela física.

        A sequência handle → update → draw é mantida estritamente em
        toda iteração: cada etapa tem exatamente uma responsabilidade.
        """
        while self.running:
            dt = self.clock.tick(config.FPS) / 1000.0

            self.handle_events()
            self.update(dt)
            self.draw()

        # Save automático ao fechar o jogo normalmente
        self._salvar_jogo()
        pygame.quit()
        sys.exit()


# ══════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    Game().run()
