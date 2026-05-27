"""
main.py
═══════
Ponto de entrada do jogo — Game Loop e Máquina de Estados Finita (FSM).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MÁQUINA DE ESTADOS FINITA (FSM)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    ┌─────────┐ ESPAÇO  ┌──────────┐  morte   ┌───────────┐
    │  MENU   │────────►│ JOGANDO  │─────────►│ GAME_OVER │
    └─────────┘         └──────────┘          └───────────┘
         ▲               │        │             R│    │M
         │    moedas=0   │        │              ▼    │
         │  fase<TOTAL   │        │           ┌──────┐│
         │    ┌──────────┘        │           │reset ││
         │    ▼ _avancar_fase()   │ moedas=0  │jogo  ││
         │  JOGANDO(próx.fase) ◄──┘ fase=TOTAL└──────┘│
         │                        │                   │
         │                        ▼                   │
         │                   ┌─────────┐        R     │
         └────────M───────── │ VITORIA │──────────────┘
                             └─────────┘
                                  │M
                                  └──► _ir_para_menu()

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

import sys
import pygame

import config
from camera  import Camera
from player  import Player
from sprites import Inimigo, Moeda, Plataforma


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
    plataformas, moedas, inimigos   (Groups)
    _spawn_x, _spawn_y, _total_moedas
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
        self.estado:      str = "MENU"
        self.high_score:  int = 0

        # ── Progressão de campanha ────────────────────────────────────
        # TOTAL_FASES é uma constante de instância (não de classe) porque
        # pode variar por perfil de dificuldade no futuro sem alterar a
        # lógica de nenhum outro módulo.
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

        # ── Áudio ─────────────────────────────────────────────────────
        self._musica_atual: str = ""
        self._inicializar_sons()

        # ── Fontes (SysFont tem custo de I/O — criadas uma única vez) ─
        self._fonte_titulo:    pygame.font.Font = pygame.font.SysFont(None, 90)
        self._fonte_subtitulo: pygame.font.Font = pygame.font.SysFont(None, 42)
        self._fonte_hud:       pygame.font.Font = pygame.font.SysFont(None, 30)
        self._fonte_score:     pygame.font.Font = pygame.font.SysFont(None, 36)

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
    # CONSTRUÇÃO E CARREGAMENTO DE FASE
    # ══════════════════════════════════════════════════════════════════

    def _construir_nivel(self, arquivo: str | None = None) -> None:
        """
        Cria (ou reconstrói) todos os objetos do nível a partir do arquivo.

        Separado de __init__ para que _resetar_jogo() possa reconstruir
        o mundo sem recriar a janela (evita flash de display.set_mode).

        Parâmetro arquivo
        ──────────────────
        Quando None (padrão), usa _arquivo_fase_atual() — que resolve
        dinamicamente "fase{self.fase_atual}.txt". Aceitar o caminho
        explícito permite testes unitários sem alterar self.fase_atual.

        Gerenciamento de memória — anti-leak
        ──────────────────────────────────────
        Na primeira chamada os grupos ainda não existem; getattr retorna
        None e o empty() é pulado.

        Nas chamadas seguintes (reset): empty() é chamado em cada grupo
        antes de reatribuir. empty() invoca kill() em cada sprite,
        removendo-o de TODOS os grupos e permitindo que o GC libere as
        Surfaces. Sem empty(), sprites com referências externas sobrevivem
        como "fantasmas" na memória — leak silencioso que cresce a cada
        partida.

        Ordem obrigatória: empty() ANTES de reatribuir os grupos.
        """
        arquivo = arquivo or self._arquivo_fase_atual()
        self.score: int = 0

        # Limpa grupos existentes antes de recriar (anti-leak)
        for nome_attr in ("plataformas", "moedas", "inimigos"):
            grupo = getattr(self, nome_attr, None)
            if isinstance(grupo, pygame.sprite.Group):
                grupo.empty()

        self.camera:      Camera              = Camera()
        self.plataformas: pygame.sprite.Group = pygame.sprite.Group()
        self.moedas:      pygame.sprite.Group = pygame.sprite.Group()
        self.inimigos:    pygame.sprite.Group = pygame.sprite.Group()

        # Spawn padrão — sobrescrito pelo tile 'P' no mapa
        self._spawn_x: float = float(config.TILE_SIZE)
        self._spawn_y: float = float(config.TILE_SIZE)

        self._carregar_fase(arquivo)

        # Player criado APÓS o carregamento para usar o spawn lido do mapa.
        # Se criado antes, usaria o spawn padrão e ignoraria o 'P'.
        self.player: Player = Player(self._spawn_x, self._spawn_y)

        # Total capturado aqui para que a barra de progresso use a contagem
        # completa, incluindo moedas que serão coletadas depois.
        self._total_moedas: int = len(self.moedas)

    def _carregar_fase(self, nome_arquivo: str) -> None:
        """
        Lê o arquivo de texto e popula os grupos de sprites.

        Formato do grid
        ────────────────
        Cada caractere = tile de TILE_SIZE × TILE_SIZE px.
        Posição de mundo: (col * TILE_SIZE,  lin * TILE_SIZE).

        Legenda de tiles
        ─────────────────
          '.'  espaço vazio (céu) — ignorado
          '#'  plataforma sólida
          'M'  moeda — centralizada no tile
          'E'  inimigo — limites de patrulha calculados automaticamente
          'P'  spawn do jogador — salva posição, não cria sprite

        Tratamento de erro
        ───────────────────
        FileNotFoundError → aviso no terminal + retorno silencioso.
        O jogo continua com grupos vazios, permitindo rodar durante
        desenvolvimento mesmo sem o arquivo de fase.
        """
        T = config.TILE_SIZE

        try:
            with open(nome_arquivo, encoding="utf-8") as f:
                grid = [linha.rstrip("\n") for linha in f]
        except FileNotFoundError:
            print(f"[FASE] Arquivo não encontrado: '{nome_arquivo}'")
            return

        num_colunas = max((len(l) for l in grid), default=0)

        for lin, linha in enumerate(grid):
            for col, tile in enumerate(linha):
                mx = col * T   # coordenada X de mundo
                my = lin * T   # coordenada Y de mundo

                if tile == "#":
                    self.plataformas.add(Plataforma(mx, my, T, T))

                elif tile == "M":
                    self.moedas.add(Moeda(mx + T // 2, my + T // 2))

                elif tile == "E":
                    x_min, x_max = self._limites_patrulha(
                        grid, lin, col, num_colunas
                    )
                    self.inimigos.add(
                        Inimigo(mx, my, x_min, x_max, velocidade=110.0)
                    )

                elif tile == "P":
                    self._spawn_x = float(mx)
                    self._spawn_y = float(my)

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

        # Preserva score quando avançando de fase (reiniciar_campanha=False)
        # mas zera quando recomeçando do zero (reiniciar_campanha=True).
        # _construir_nivel() sempre zera; re-atribuímos aqui se necessário.
        # Nota: o score já foi zerado em _construir_nivel(); como queremos
        # preservar apenas no avanço de fase, o score acumulado é passado
        # explicitamente por _avancar_fase() após a chamada.
        self.estado = "JOGANDO"

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
        self.estado = "GAME_OVER"

    def _ir_para_vitoria(self) -> None:
        """Vitória: atualiza high_score, para música, dispara jingle, muda estado."""
        if self.score > self.high_score:
            self.high_score = self.score
        self._parar_musica()
        self._tocar_som("vitoria")
        self.estado = "VITORIA"

    def _ir_para_menu(self) -> None:
        """Para a música atual, transita para MENU e toca a trilha do menu."""
        self._parar_musica()
        self.estado = "MENU"
        self._tocar_musica(config.MUSICA_MENU, self._VOL_MUSICA_MENU)

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

        if not pisou_algum:
            # ── Toque lateral ou por baixo — tomar_dano() decide ─────────
            # tomar_dano() retorna False se o jogador já está invulnerável
            # (i-frames ativos) — nenhuma vida é decrementada nem SFX tocado.
            # Retorna True apenas se o dano foi efetivamente aplicado.
            if self.player.tomar_dano():
                self.vidas -= 1
                self._tocar_som("morte")

                if self.vidas <= 0:
                    # Sem vidas: encerra a partida
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

            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.running = False
                break

            # ── Roteamento por estado ─────────────────────────────────
            if self.estado == "MENU":
                if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                    self._resetar_jogo()
                    self._tocar_musica(config.MUSICA_FASE, self._VOL_MUSICA_FASE)

            elif self.estado == "JOGANDO":
                # Delega ao Player — ele filtra internamente por KEYDOWN
                self.player.handle_jump(event)

            elif self.estado in ("GAME_OVER", "VITORIA"):
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
        1. Física do jogador   (movimento + colisão com plataformas)
        2. Física dos inimigos (patrulha independente)
        3. SFX de pulo         (One-Frame Event Flag — lida e zerada aqui)
        4. Coleta de moedas    (score + SFX)
        5. Combate com inimigos (stomp ou game over)
        6. Condição de vitória (verificada após coleta — score atualizado)
        7. Câmera              (sempre depois do jogador — posição final)
        """
        if self.estado != "JOGANDO":
            return

        # ── Física ────────────────────────────────────────────────────
        self.player.update(dt, self.plataformas)
        self.inimigos.update(dt)

        # ── SFX de pulo ───────────────────────────────────────────────
        if self.player.pulou:
            self._tocar_som("pulo")
            self.player.pulou = False

        # ── Coleta de moedas ──────────────────────────────────────────
        coletadas = pygame.sprite.spritecollide(
            self.player, self.moedas, dokill=True
        )
        if coletadas:
            self.score += len(coletadas) * Moeda.VALOR
            self._tocar_som("moeda")

        # ── Combate com inimigos ──────────────────────────────────────
        self._checar_colisao_inimigos()

        # ── Condição de fim de fase ───────────────────────────────────
        # `not self.moedas` é idiomático para len == 0 e evita chamada
        # de função. A verificação acontece APÓS a coleta — garante que
        # o score da última moeda está contabilizado antes da transição.
        if not self.moedas:
            if self.fase_atual < self.TOTAL_FASES:
                # ── Fase intermediária: avança para a próxima ─────────
                # _avancar_fase() preserva o score, incrementa fase_atual,
                # reconstrói o nível e toca o SFX de conclusão.
                # O estado permanece "JOGANDO" — sem tela de transição,
                # a câmera corta imediatamente para o novo mapa.
                self._avancar_fase()
            else:
                # ── Última fase: encerra a campanha ───────────────────
                self._ir_para_vitoria()
            return   # câmera não precisa atualizar — frame de transição

        # ── Câmera ────────────────────────────────────────────────────
        self.camera.update(self.player.rect)

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
        if self.estado == "MENU":
            self._draw_menu()

        elif self.estado == "JOGANDO":
            self._draw_jogo()
            self._draw_hud()

        elif self.estado == "GAME_OVER":
            self._draw_jogo()
            self._draw_overlay()
            self._draw_game_over()

        elif self.estado == "VITORIA":
            self._draw_jogo()
            self._draw_overlay()
            self._draw_vitoria()

        pygame.display.flip()

    # ------------------------------------------------------------------
    # Rotinas de renderização por estado
    # ------------------------------------------------------------------

    def _draw_menu(self) -> None:
        """Tela de menu: fundo escuro, título, controles e high score."""
        SW, SH   = config.SCREEN_WIDTH, config.SCREEN_HEIGHT
        mid_x    = SW // 2
        mid_y    = SH // 2

        self.screen.fill(config.BLACK)

        # Faixa pré-renderizada — sem alocação de Surface por frame
        self.screen.blit(self._surf_faixa_menu, (0, 0))

        self._texto(
            self._fonte_titulo, config.TITLE,
            config.YELLOW, mid_x, mid_y - 100,
        )
        self._texto(
            self._fonte_subtitulo, "Pressione ESPAÇO para Iniciar",
            config.WHITE, mid_x, mid_y + 10,
        )
        self._texto(
            self._fonte_hud, "← → / A D  Mover    ESPAÇO / ↑ / W  Pular",
            (180, 180, 180), mid_x, mid_y + 65,
        )

        if self.high_score > 0:
            self._texto(
                self._fonte_subtitulo, f"High Score: {self.high_score}",
                config.GOLD, mid_x, mid_y + 120,
            )

    def _draw_jogo(self) -> None:
        """
        Renderiza o cenário completo com offset de câmera.

        Por que não usar Group.draw()?
        ───────────────────────────────
        Group.draw() usa sprite.rect diretamente (world-space). A câmera
        precisa de um Rect ajustado (screen-space) via Camera.aplicar(),
        que retorna um novo Rect sem modificar o original — preservando
        a física. Loop manual é necessário para interpor o offset.
        """
        self.screen.fill(config.SKY_BLUE)

        for spr in self.plataformas:
            self.screen.blit(spr.image, self.camera.aplicar(spr.rect))

        for spr in self.moedas:
            self.screen.blit(spr.image, self.camera.aplicar(spr.rect))

        for spr in self.inimigos:
            self.screen.blit(spr.image, self.camera.aplicar(spr.rect))

        self.player.draw(self.screen, self.camera.aplicar(self.player.rect))

    def _draw_hud(self) -> None:
        """HUD em gameplay: vidas (esquerda), fase (centro), score (direita), barra de moedas."""
        SW = config.SCREEN_WIDTH

        # ── Vidas — canto superior esquerdo ───────────────────────────
        # Coração Unicode (♥) repetido N vezes: legível, sem assets.
        # Corações cinzas representam vidas perdidas — dá contexto visual
        # imediato do estado de saúde sem precisar de números.
        coracoes_cheios  = "♥" * self.vidas
        coracoes_vazios  = "♡" * (self.vidas_max - self.vidas)
        texto_vidas      = coracoes_cheios + coracoes_vazios

        self._texto(
            self._fonte_score, texto_vidas,
            config.RED, 10, 10, ancora="topleft",
        )

        # ── Indicador de fase — centro superior ───────────────────────
        # Renderizado depois das vidas para garantir que a sombra das
        # vidas não sobreponha o texto de fase em resoluções estreitas.
        self._texto(
            self._fonte_hud,
            f"FASE  {self.fase_atual} / {self.TOTAL_FASES}",
            config.WHITE, SW // 2, 10, ancora="midtop",
        )

        # ── Score — canto superior direito ────────────────────────────
        self._texto(
            self._fonte_score, f"Score: {self.score}",
            config.YELLOW, SW - 10, 10, ancora="topright",
        )

        # ── Barra de progresso de moedas ──────────────────────────────
        coletadas  = self._total_moedas - len(self.moedas)
        barra_w    = 160
        barra_h    = 10
        barra_x    = 10
        barra_y    = 52   # deslocado para baixo das vidas (era 38)

        # Fundo cinza da barra
        pygame.draw.rect(
            self.screen, (80, 80, 80),
            (barra_x, barra_y, barra_w, barra_h),
            border_radius=4,
        )
        # Preenchimento proporcional
        if self._total_moedas > 0:
            preenchido = int(barra_w * coletadas / self._total_moedas)
            if preenchido > 0:
                pygame.draw.rect(
                    self.screen, config.YELLOW,
                    (barra_x, barra_y, preenchido, barra_h),
                    border_radius=4,
                )

        # Legenda da barra — renderizada separadamente para clareza
        surf_moedas = self._fonte_hud.render(
            f"Moedas: {coletadas}/{self._total_moedas}",
            True, config.WHITE,
        )
        self.screen.blit(surf_moedas, (barra_x, barra_y + 14))

        # ── Linha de debug — logo abaixo da legenda de moedas ─────────
        texto_debug = (
            f"X: {int(self.player.x)}  "
            f"anim: {self.player.estado_animacao}[{self.player.frame_atual}]  "
            f"inimigos: {len(self.inimigos)}"
        )
        surf_debug = self._fonte_hud.render(texto_debug, True, config.BLACK)
        self.screen.blit(surf_debug, (barra_x, barra_y + 30))

    def _draw_overlay(self) -> None:
        """Aplica o overlay escuro pré-renderizado sobre o cenário congelado."""
        self.screen.blit(self._overlay, (0, 0))

    def _draw_game_over(self) -> None:
        """Painel de Game Over: título, score, high score e instruções."""
        SW, SH = config.SCREEN_WIDTH, config.SCREEN_HEIGHT
        cx     = SW // 2
        cy     = SH // 2

        self._texto(self._fonte_titulo,    "GAME OVER",
                    config.RED,   cx, cy - 110)
        self._texto(self._fonte_subtitulo, f"Score: {self.score}",
                    config.WHITE, cx, cy - 20)

        if self.score > 0 and self.score >= self.high_score:
            self._texto(self._fonte_hud, "★  Novo High Score!  ★",
                        config.GOLD, cx, cy + 25)

        self._texto(self._fonte_subtitulo, f"High Score: {self.high_score}",
                    config.GOLD,        cx, cy + 60)
        self._texto(self._fonte_hud,       "[R] Tentar Novamente      [M] Menu",
                    (200, 200, 200),     cx, cy + 115)

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

        pygame.quit()
        sys.exit()


# ══════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    Game().run()
