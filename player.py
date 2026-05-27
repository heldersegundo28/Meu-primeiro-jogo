"""
player.py
═════════
Entidade principal do jogo — física, input, colisão, animação e game feel.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FÍSICA COM DELTA TIME (dt-physics)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Toda grandeza de movimento usa a Integração de Euler semi-implícita:

    vel  +=  aceleração × dt          →  velocidade em px/s
    pos  +=  vel        × dt          →  posição   em px

Multiplicar por dt garante que o personagem percorre a mesma distância
por segundo a 30, 60 ou 120 FPS. Sem dt, a velocidade seria proporcional
ao frame rate — o jogo ficaria mais rápido em máquinas mais potentes.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COLISÃO AABB POR EIXO SEPARADO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

AABB = Axis-Aligned Bounding Box. A solução por eixo separado evita o
bug de "wall-sticking" (personagem gruda na parede ao pular rente a ela):

    1. Move só X → detecta colisão → corrige X   (lateral)
    2. Move só Y → detecta colisão → corrige Y   (pouso/teto)

Após cada correção: re-sincroniza o float ← rect corrigido (anti-jitter).
Ver _resolve_collisions() para a implementação completa.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GAME FEEL — COYOTE TIME E INPUT BUFFERING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Dois problemas de "feel" afetam jogos de plataforma com física dt-based:

  PROBLEMA 1: pulo perdido na borda
  ─────────────────────────────────
  O jogador chega à borda de uma plataforma e pressiona Espaço um
  frame após no_chao virar False. A física está correta — ele já está
  no ar — mas o pulo parece ter "falhado" ao jogador. Resultado:
  frustração, sensação de controles imprecisos.

  SOLUÇÃO: Coyote Time
  ─────────────────────
  Mantemos um timer que inicia em COYOTE_DURATION ao sair do chão
  (sem pular). Enquanto o timer > 0, o jogador AINDA pode pular mesmo
  sem estar em no_chao. Assim que o pulo é executado via coyote, o
  timer é zerado para impedir pulos duplos.

  Linha do tempo:
    t=0.00  toca o chão        → coyote_timer = COYOTE_DURATION (0.15)
    t=0.10  sai da borda       → coyote_timer começa a decrescer
    t=0.18  jogador pressiona  → coyote_timer=0.07 > 0 → PULO VÁLIDO ✓
    t=0.27  coyote expirou     → sem pulo (no ar há 170ms)

  PROBLEMA 2: pulo prematuro antes do pouso
  ──────────────────────────────────────────
  O jogador pressiona Espaço 80ms antes de pousar numa plataforma.
  Quando pousa, a intenção já "expirou" — o pulo não executa. O
  jogador precisa pressionar de novo, gerando input reativo em vez
  de preditivo.

  SOLUÇÃO: Input Buffering (Jump Buffer)
  ───────────────────────────────────────
  Ao pressionar Espaço, apenas registramos a intenção:
      jump_buffer_timer = JUMP_BUFFER_DURATION

  A cada frame, se jump_buffer_timer > 0 E o jogador pode pular
  (no_chao OU coyote), executamos o pulo automaticamente.

  Linha do tempo:
    t=0.00  jogador pressiona  → jump_buffer_timer = 0.12
    t=0.00  está no ar         → sem pulo (buffer registrado)
    t=0.05  pousa na plataforma→ jump_buffer_timer=0.07 > 0 → PULO ✓
    t=0.12  buffer expirou     → sem pulo automático

  SINERGIA DOS DOIS SISTEMAS
  ───────────────────────────
  Coyote Time:    amplia a janela de pulo APÓS sair do chão
  Input Buffer:   amplia a janela de pulo ANTES de tocar o chão

  Juntos, cobrem os dois lados da interação — o resultado é controles
  que "sentem" instantâneos mesmo com física discreta a 60 FPS.
  Valores típicos usados em jogos profissionais: 0.10–0.20 segundos.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ANIMAÇÃO POR SPRITESHEET — ARQUITETURA DE TRÊS CAMADAS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Camada 1 — QUAL sequência?   _atualizar_estado_animacao()
  Camada 2 — QUAL frame?       _atualizar_frames(dt)
  Camada 3 — COMO renderizar?  draw() → blit direto do atlas

Layout esperado da spritesheet (configurável via config.py):
  ┌─────────┬─────────┬─────────┬─────────┐
  │ idle  0 │ idle  1 │ idle  2 │ idle  3 │  row 0  (parado)
  ├─────────┼─────────┼─────────┼─────────┤
  │  run  0 │  run  1 │  run  2 │  run  3 │  row 1  (correndo)
  ├─────────┼─────────┼─────────┼─────────┤
  │ jump  0 │ jump  1 │ jump  2 │ jump  3 │  row 2  (pulando)
  └─────────┴─────────┴─────────┴─────────┘
  Cada célula: FRAME_WIDTH × FRAME_HEIGHT px (default 32×32)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FLAG DE EVENTO DE UM FRAME (pulou)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Player não conhece o sistema de áudio. Quando o pulo é EXECUTADO
(independente se via no_chao, coyote ou buffer), self.pulou = True
sinaliza ao Game para tocar o SFX. O Game lê e zera a flag.
Padrão: "One-Frame Event Flag" (Unity: Input.GetButtonDown).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
I-FRAMES (INVULNERABILIDADE TEMPORÁRIA) E EFEITO DE PISCAR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Problema: sem proteção pós-dano, um inimigo parado sobre o jogador
aplicaria dano em todos os 60 frames do segundo — vida zerada em 1s.

Solução: invulnerabilidade temporária (i-frames, "invincibility frames")

  tomar_dano() → ativa invulneravel_timer = INVULNERAVEL_DURATION
  update()     → decrementa invulneravel_timer com dt
  tomar_dano() → se invulneravel_timer > 0: retorna False (bloqueado)

O retorno bool de tomar_dano() segue o padrão Command Query Separation:
  True  → dano aplicado — Game decrementa lives e toca SFX de dano
  False → jogador invulnerável — Game ignora completamente

Knockback
──────────
Ao tomar dano, o jogador recebe um impulso para afastá-lo do perigo:
  vel_y = KNOCKBACK_VY   (negativo → sobe, confirmação visual do dano)
  vel_x = ±KNOCKBACK_VX  (sinal invertido de virado_direita → empurra
                          para trás, nunca em direção ao inimigo)

Efeito visual de piscar (NES/SNES i-frames)
──────────────────────────────────────────────
Clássico em jogos como Mega Man, Castlevania, Kirby. O sprite alterna
entre visível e invisível em intervalos curtos (PISCA_FREQUENCIA).

Matemática do piscar baseado em tempo contínuo (dt-based):
  pisca_timer acumula dt enquanto invulnerável.
  Fase = int(pisca_timer / PISCA_FREQUENCIA)
  Se fase % 2 == 0 → desenha; se fase % 2 == 1 → pula o blit.

  Com PISCA_FREQUENCIA = 0.07s: troca a cada 4 frames (60 FPS).
  Resultado: 7 ciclos visível/invisível por segundo — frequência
  que o olho humano processa como "piscando" sem causar fadiga.

Por que usar divisão inteira e módulo em vez de toggle booleano?
  Um toggle bool dependeria de ser executado exatamente uma vez por
  intervalo — sensível a lag spikes. A divisão inteira do tempo
  acumulado é determinística: dado o mesmo pisca_timer, o resultado
  é sempre o mesmo, independente de quantos frames aconteceram.
"""

from __future__ import annotations

import pygame

import config
from spritesheet import Spritesheet


class Player:
    """
    Entidade controlada pelo jogador.

    Responsabilidades
    ─────────────────
    • Física:       gravidade, aceleração, integração dt-based
    • Game feel:    Coyote Time + Input Buffering para pulos responsivos
    • Input:        teclado (movimento horizontal, buffer de pulo)
    • Colisão:      AABB por eixo separado com grupo de plataformas
    • Animação:     FSM de estados + cronômetro de frames
    • Renderização: blit de spritesheet com direção e câmera

    Invariante central
    ───────────────────
    self.x / self.y  →  floats autoritativos da posição (world-space)
    self.rect        →  derivado (int truncado); sincronizado após colisões
    """

    # ── Hitbox de colisão ─────────────────────────────────────────────
    WIDTH:  int = 40
    HEIGHT: int = 60

    # ── Física ────────────────────────────────────────────────────────
    SPEED:      float = config.PLAYER_SPEED
    GRAVITY:    float = config.PLAYER_GRAVITY
    FORCA_PULO: float = config.PLAYER_JUMP_FORCE

    # ── Game Feel — janelas de tolerância de pulo ─────────────────────
    #
    # COYOTE_DURATION: segundos após sair do chão em que o pulo ainda
    # é válido. 0.15 s = 9 frames a 60 FPS — imperceptível ao jogador
    # mas transforma uma borda "escorregadia" em superfície sólida.
    #
    # JUMP_BUFFER_DURATION: segundos que a intenção de pulo fica
    # "guardada" antes de pousar. 0.12 s = 7 frames a 60 FPS — cobre
    # o tempo de reação humana de antecipar o pouso.
    COYOTE_DURATION:      float = 0.15
    JUMP_BUFFER_DURATION: float = 0.12

    # ── Animação ──────────────────────────────────────────────────────
    TOTAL_FRAMES: int   = 4
    _INTERVALO:   float = config.VELOCIDADE_ANIMACAO

    _LINHA_SHEET: dict[str, int] = {
        "parado":   0,
        "correndo": 1,
        "pulando":  2,
    }

    # ── I-frames — invulnerabilidade temporária pós-dano ──────────────
    #
    # INVULNERAVEL_DURATION: janela de proteção em segundos.
    #   1.5 s = 90 frames a 60 FPS. Valor padrão de jogos como Mega Man
    #   e Castlevania — longo o suficiente para o jogador escapar do
    #   perigo, curto o suficiente para manter o desafio.
    #
    # PISCA_FREQUENCIA: segundos entre cada alternância visível/invisível.
    #   0.07 s ≈ 4 frames a 60 FPS — frequência que o olho humano
    #   percebe como "piscando" sem causar fadiga visual.
    INVULNERAVEL_DURATION: float = 1.5
    PISCA_FREQUENCIA:      float = 0.07

    # ── Knockback — impulso ao tomar dano ─────────────────────────────
    #
    # KNOCKBACK_VY: velocidade vertical do knockback (negativa = para cima).
    #   -350 px/s ≈ 60% da força de pulo — sobe visivelmente mas não
    #   tanto quanto um pulo voluntário. O jogador sente o impacto.
    #
    # KNOCKBACK_VX: magnitude do empurrão horizontal.
    #   Sinal determinado em tomar_dano() pelo virado_direita:
    #   se olha para →, é empurrado para ← (sinal negativo) e vice-versa.
    KNOCKBACK_VY: float = -350.0
    KNOCKBACK_VX: float =  300.0

    # ──────────────────────────────────────────────────────────────────
    def __init__(self, x: float, y: float) -> None:
        """
        Inicializa física, timers de game feel, animação e spritesheet.

        Parâmetros
        ──────────
        x, y : topleft inicial em coordenadas de mundo (pixels).
        """
        # ── Posição (floats autoritativos) ────────────────────────────
        self.x: float = float(x)
        self.y: float = float(y)

        # ── Velocidade (px/s) ─────────────────────────────────────────
        self.vel_x: float = 0.0
        self.vel_y: float = 0.0

        # ── Estado de chão ────────────────────────────────────────────
        # Levantado em _resolve_collisions quando o jogador pousa.
        # Zerado no início da resolução do eixo Y de cada frame.
        self.no_chao: bool = False

        # ── Timers de game feel ───────────────────────────────────────
        #
        # coyote_timer
        #   Inicia em COYOTE_DURATION ao tocar o chão.
        #   Decrementa com dt enquanto o jogador está no ar.
        #   Enquanto > 0: o jogador pode pular mesmo sem no_chao.
        #   Zerado imediatamente ao executar um pulo via coyote
        #   para impedir pulos duplos.
        self.coyote_timer: float = 0.0

        #
        # jump_buffer_timer
        #   Levantado para JUMP_BUFFER_DURATION ao pressionar Espaço.
        #   Decrementa com dt a cada frame.
        #   Enquanto > 0: update() tentará executar o pulo se as
        #   condições (no_chao OU coyote) forem satisfeitas.
        #   Zerado ao executar o pulo para evitar pulos duplos.
        self.jump_buffer_timer: float = 0.0

        # ── Rect de colisão (world-space) ─────────────────────────────
        self.rect: pygame.Rect = pygame.Rect(
            int(self.x), int(self.y), self.WIDTH, self.HEIGHT
        )

        # ── Direção do olhar ──────────────────────────────────────────
        self.virado_direita: bool = True

        # ── Máquina de estados de animação ────────────────────────────
        self.estado_animacao: str   = "parado"
        self.frame_atual:     int   = 0
        self.tempo_animacao:  float = 0.0

        # ── Flag de evento de um frame ────────────────────────────────
        # True quando um pulo é EXECUTADO neste frame (qualquer caminho:
        # no_chao, coyote ou buffer). Game lê, toca SFX e zera a flag.
        self.pulou: bool = False

        # ── I-frames — timers de invulnerabilidade e piscar ───────────
        #
        # invulneravel_timer
        #   > 0  →  jogador está invulnerável: tomar_dano() retorna False
        #   = 0  →  jogador pode tomar dano normalmente
        #   Decrementado por dt em update(); ativado por tomar_dano().
        self.invulneravel_timer: float = 0.0

        # pisca_timer
        #   Acumula dt enquanto invulneravel_timer > 0.
        #   Zerado ao entrar no estado invulnerável para iniciar o
        #   ciclo de piscar do zero (evita flash de meio-ciclo).
        #   Usado em draw() para calcular a fase visível/invisível.
        self.pisca_timer: float = 0.0

        # ── Spritesheet ───────────────────────────────────────────────
        self._carregar_animacoes()

    # ══════════════════════════════════════════════════════════════════
    # CARREGAMENTO DE ANIMAÇÕES
    # ══════════════════════════════════════════════════════════════════

    def _carregar_animacoes(self) -> None:
        """
        Carrega a spritesheet e monta os dicionários de animação.

        Estrutura produzida
        ────────────────────
          self.animacoes_dir : dict[str, list[Surface]]  — olha para →
          self.animacoes_esq : dict[str, list[Surface]]  — olha para ←

        O flip é calculado UMA vez aqui. draw() é uma indexação O(1).
        Frames são escalados de FRAME_WIDTH×FRAME_HEIGHT para WIDTH×HEIGHT,
        desacoplando resolução da arte de hitbox de física.
        """
        sheet  = Spritesheet(config.SPRITE_PLAYER)
        escala = (self.WIDTH, self.HEIGHT)
        fw, fh, n = config.FRAME_WIDTH, config.FRAME_HEIGHT, self.TOTAL_FRAMES

        self.animacoes_dir: dict[str, list[pygame.Surface]] = {}
        self.animacoes_esq: dict[str, list[pygame.Surface]] = {}

        for estado, linha in self._LINHA_SHEET.items():
            self.animacoes_dir[estado] = sheet.get_sequencia(
                linha, n, fw, fh, escala=escala,
            )
            self.animacoes_esq[estado] = sheet.get_sequencia(
                linha, n, fw, fh, escala=escala, espelhar_x=True,
            )

    # ══════════════════════════════════════════════════════════════════
    # INPUT  (métodos públicos chamados pelo Game)
    # ══════════════════════════════════════════════════════════════════

    def handle_jump(self, event: pygame.event.Event) -> None:
        """
        Registra a intenção de pulo no jump_buffer_timer.

        Por que registrar no buffer em vez de pular imediatamente?
        ─────────────────────────────────────────────────────────────
        A execução real do pulo (aplicar FORCA_PULO, levantar no_chao,
        levantar self.pulou) acontece em _processar_pulo(), chamado
        dentro de update(). Isso garante que o buffer e o coyote time
        são consultados no mesmo ponto — o estado de física mais
        recente do frame, após _resolve_collisions().

        Por que KEYDOWN e não get_pressed()?
        ──────────────────────────────────────
        get_pressed() retornaria True durante TODOS os frames em que
        Espaço está pressionado, reativando o buffer a cada frame e
        tornando o sistema ineficaz. KEYDOWN dispara UMA VEZ.
        """
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
                # Registra intenção — não executa o pulo aqui.
                # update() executará o pulo na próxima oportunidade válida.
                self.jump_buffer_timer = self.JUMP_BUFFER_DURATION

    # ══════════════════════════════════════════════════════════════════
    # FÍSICA  (métodos privados)
    # ══════════════════════════════════════════════════════════════════

    def tomar_dano(self) -> bool:
        """
        Aplica dano ao jogador se ele não estiver invulnerável.

        Padrão Command Query Separation (CQS)
        ──────────────────────────────────────
        Este método é um Command com retorno de status — modifica estado
        (ativa i-frames, aplica knockback) E informa se o fez:

          True  → dano aplicado com sucesso.
                  Game deve: decrementar lives, tocar SFX de dano,
                  verificar game over.

          False → jogador invulnerável — dano bloqueado.
                  Game ignora completamente (sem SFX, sem decremento).

        Efeitos quando dano é aplicado (retorno True)
        ───────────────────────────────────────────────
          invulneravel_timer ← INVULNERAVEL_DURATION  (ativa proteção)
          pisca_timer        ← 0.0     (reinicia ciclo visual do zero)
          vel_y              ← KNOCKBACK_VY  (impulso para cima)
          vel_x              ← ±KNOCKBACK_VX (empurrão para trás)

        Knockback direcional
        ─────────────────────
        O sinal de vel_x é OPOSTO à direção do olhar:
          virado_direita=True  → vel_x = -KNOCKBACK_VX  (empurra para ←)
          virado_direita=False → vel_x = +KNOCKBACK_VX  (empurra para →)

        Isso garante que o jogador é sempre empurrado PARA LONGE do
        inimigo — a direção de "retrocesso" intuitiva para o jogador.

        Por que não decrementar lives aqui?
        ─────────────────────────────────────
        Lives são responsabilidade do Game (estado global da campanha),
        não do Player (estado de uma entidade). O Player reporta o evento;
        o Game decide o que fazer com ele — desacoplamento correto.
        """
        if self.invulneravel_timer > 0.0:
            return False   # invulnerável — dano bloqueado

        # ── Ativa i-frames ────────────────────────────────────────────
        self.invulneravel_timer = self.INVULNERAVEL_DURATION
        self.pisca_timer        = 0.0   # ciclo visual começa do zero

        # ── Knockback físico ──────────────────────────────────────────
        self.vel_y = self.KNOCKBACK_VY
        self.vel_x = (
            -self.KNOCKBACK_VX if self.virado_direita   # olha →, empurra ←
            else +self.KNOCKBACK_VX                     # olha ←, empurra →
        )

        # Knockback lança o jogador no ar — coyote e buffer perdem
        # sentido neste contexto; zerá-los evita pulo acidental
        # imediatamente após o impacto.
        self.no_chao           = False
        self.coyote_timer      = 0.0
        self.jump_buffer_timer = 0.0

        return True   # dano aplicado — Game deve decrementar lives

    def _handle_input(self) -> None:
        """
        Lê o estado contínuo do teclado e define vel_x.
        Zerar vel_x antes das checagens garante parada imediata ao soltar.
        """
        keys       = pygame.key.get_pressed()
        self.vel_x = 0.0

        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.vel_x          = -self.SPEED
            self.virado_direita = False

        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.vel_x          = +self.SPEED
            self.virado_direita = True

    def _apply_gravity(self, dt: float) -> None:
        """Acumula gravidade em vel_y (positivo = para baixo)."""
        self.vel_y += self.GRAVITY * dt

    def _pode_pular(self) -> bool:
        """
        Retorna True se o jogador está apto a executar um pulo agora.

        A condição combina dois critérios com OR:
            no_chao        →  toque físico direto com uma plataforma
            coyote_timer>0 →  ainda na janela de tolerância pós-borda

        Extraído como método para evitar duplicação: a mesma lógica
        é usada em _processar_pulo() e pode ser consultada externamente
        (ex.: inimigos com IA de salto futura).
        """
        return self.no_chao or self.coyote_timer > 0.0

    def _executar_pulo(self) -> None:
        """
        Aplica a força de pulo e reseta os dois timers.

        Chamado apenas quando _pode_pular() == True e jump_buffer_timer > 0.
        Centralizar aqui garante que o reset dos timers é sempre atômico —
        não há risco de esquecer um dos dois em algum branch de if/else.

        Efeitos:
          vel_y             ← FORCA_PULO (negativo = para cima)
          no_chao           ← False  (deixou o chão)
          coyote_timer      ← 0.0    (janela consumida — sem pulo duplo)
          jump_buffer_timer ← 0.0    (intenção consumida — sem pulo duplo)
          pulou             ← True   (One-Frame Flag para SFX no Game)
        """
        self.vel_y             = self.FORCA_PULO
        self.no_chao           = False
        self.coyote_timer      = 0.0   # impede segundo pulo via coyote
        self.jump_buffer_timer = 0.0   # consome a intenção registrada
        self.pulou             = True  # Game lê esta flag e toca o SFX

    def _atualizar_timers_game_feel(self, dt: float) -> None:
        """
        Decrementa os timers de Coyote Time e Input Buffer a cada frame.

        Deve ser chamado APÓS _resolve_collisions() para ler no_chao
        no estado correto do frame atual (pós-colisão).

        Coyote Time
        ────────────
        Se o jogador ESTÁ no chão: recarrega o timer para o valor máximo.
        Isso garante que a janela está sempre disponível ao sair de uma
        superfície — independente de quantos frames o jogador permaneceu parado.

        Se o jogador NÃO está no chão: decrementa. Quando atinge 0,
        a janela de coyote expirou e o pulo não é mais permitido por
        este caminho (apenas no_chao pode liberar o próximo pulo).

        Input Buffer
        ─────────────
        Decrementa independentemente de no_chao ou coyote — representa
        o tempo que a intenção do jogador fica "na fila" aguardando
        uma oportunidade de execução. Sempre >= 0.0.
        """
        if self.no_chao:
            # No chão: recarrega janela de coyote para a próxima borda
            self.coyote_timer = self.COYOTE_DURATION
        else:
            # No ar: consome a janela de coyote linearmente com o tempo
            self.coyote_timer = max(0.0, self.coyote_timer - dt)

        # Buffer de pulo decrementa sempre — independente do estado de chão
        self.jump_buffer_timer = max(0.0, self.jump_buffer_timer - dt)

    def _processar_pulo(self) -> None:
        """
        Tenta executar um pulo se buffer e condições estiverem alinhados.

        Lógica de decisão:
            jump_buffer_timer > 0   →  existe intenção registrada?
            _pode_pular()           →  no_chao OU coyote_timer > 0?
            ↳ ambos True            →  executa _executar_pulo()

        Por que chamar APÓS _atualizar_timers_game_feel()?
        ─────────────────────────────────────────────────────
        Os timers devem refletir o estado físico do frame atual antes
        da decisão de pulo. Se processarmos antes de decrementar o coyote,
        a janela terminaria no frame seguinte ao esperado — 1 frame de
        diferença que poderia tornar o coyote inefficaz em 60 FPS.
        """
        if self.jump_buffer_timer > 0.0 and self._pode_pular():
            self._executar_pulo()

    def _resolve_collisions(
        self,
        plataformas: pygame.sprite.Group,
        dt:          float,
    ) -> None:
        """
        Move o jogador e resolve colisões por eixo separado.

        Eixo X → Eixo Y. Cada eixo resolvido independentemente.
        Re-sincroniza float ← rect após cada correção (anti-jitter).
        """
        # ── EIXO X ────────────────────────────────────────────────────
        self.x     += self.vel_x * dt
        self.rect.x = int(self.x)

        for plat in pygame.sprite.spritecollide(self, plataformas, False):
            if self.vel_x > 0:
                self.rect.right = plat.rect.left
            elif self.vel_x < 0:
                self.rect.left  = plat.rect.right
            self.x     = float(self.rect.x)   # anti-jitter
            self.vel_x = 0.0

        # ── EIXO Y ────────────────────────────────────────────────────
        self.y     += self.vel_y * dt
        self.rect.y = int(self.y)

        # Reseta no_chao — True apenas se houver colisão vertical neste frame
        self.no_chao = False

        for plat in pygame.sprite.spritecollide(self, plataformas, False):
            if self.vel_y > 0:
                self.rect.bottom = plat.rect.top
                self.no_chao     = True
            elif self.vel_y < 0:
                self.rect.top    = plat.rect.bottom
            self.y     = float(self.rect.y)   # anti-jitter
            self.vel_y = 0.0

        # ── LIMITES DO MUNDO ──────────────────────────────────────────
        self.x      = max(0.0, min(self.x, float(config.WORLD_WIDTH - self.WIDTH)))
        self.rect.x = int(self.x)

    # ══════════════════════════════════════════════════════════════════
    # ANIMAÇÃO  (métodos privados)
    # ══════════════════════════════════════════════════════════════════

    def _atualizar_estado_animacao(self) -> None:
        """
        Determina o estado de animação a partir das variáveis de física.

        Prioridade:
          1. No ar          → "pulando"   (domina qualquer vel_x)
          2. No chão + mov. → "correndo"
          3. No chão parado → "parado"

        Ao trocar de estado: reinicia frame e cronômetro (sem "entrar
        no meio" de uma animação).
        """
        if not self.no_chao:
            novo = "pulando"
        elif self.vel_x != 0.0:
            novo = "correndo"
        else:
            novo = "parado"

        if novo != self.estado_animacao:
            self.estado_animacao = novo
            self.frame_atual     = 0
            self.tempo_animacao  = 0.0

    def _atualizar_frames(self, dt: float) -> None:
        """
        Avança frame_atual quando o cronômetro atinge _INTERVALO.

        Usa -= em vez de = 0 para preservar o "troco" de tempo
        (ritmo constante mesmo com lag spikes). O while cobre
        lag spikes onde dois frames deveriam avançar no mesmo update.
        """
        if self.estado_animacao == "correndo":
            self.tempo_animacao += dt
            while self.tempo_animacao >= self._INTERVALO:
                self.tempo_animacao -= self._INTERVALO
                self.frame_atual     = (self.frame_atual + 1) % self.TOTAL_FRAMES
        else:
            self.frame_atual    = 0
            self.tempo_animacao = 0.0

    # ══════════════════════════════════════════════════════════════════
    # UPDATE PRINCIPAL  (método público)
    # ══════════════════════════════════════════════════════════════════

    def update(self, dt: float, plataformas: pygame.sprite.Group) -> None:
        """
        Executa um passo lógico completo para este frame.

        Ordem obrigatória — cada passo depende do anterior:
        ──────────────────────────────────────────────────
        1. Input horizontal    define vel_x e virado_direita
        2. Gravidade           acumula vel_y
        3. Colisões            move, corrige, atualiza no_chao
        4. Sync floats         re-sincroniza x/y ← rect final
        5. Timers game feel    decrementa coyote e buffer com dt
                               (após colisões — lê no_chao correto)
        6. Processar pulo      executa se buffer+condições alinhados
        7. Estado animação     lê estado físico final
        8. Frames animação     avança cronômetro

        Por que game feel APÓS colisões (passos 5–6)?
        ───────────────────────────────────────────────
        Os timers dependem de no_chao, que só é confiável após
        _resolve_collisions(). Se decrementarmos antes, o coyote_timer
        seria atualizado com o valor de no_chao do frame anterior —
        1 frame de erro que tornaria a janela 1 frame menor do que o
        esperado (problema especialmente visível em 30 FPS).
        """
        self._handle_input()
        self._apply_gravity(dt)
        self._resolve_collisions(plataformas, dt)

        # Re-sincronização após todas as correções de colisão e limites
        self.x = float(self.rect.x)
        self.y = float(self.rect.y)

        # ── I-frames: decrementa timers ───────────────────────────────
        # invulneravel_timer decrementado por dt até atingir 0.
        # max(0.0, ...) evita valores negativos — o timer é uma duração,
        # não um contador regressivo arbitrário.
        # pisca_timer acumula APENAS enquanto invulnerável; zera junto
        # com invulneravel_timer para não poluir ciclos futuros.
        if self.invulneravel_timer > 0.0:
            self.invulneravel_timer = max(0.0, self.invulneravel_timer - dt)
            self.pisca_timer       += dt
            if self.invulneravel_timer == 0.0:
                self.pisca_timer = 0.0   # reset limpo ao sair dos i-frames

        # Game feel — ordem: decrementar → tentar pular
        # (timers refletem estado físico atual antes da decisão)
        self._atualizar_timers_game_feel(dt)
        self._processar_pulo()

        self._atualizar_estado_animacao()
        self._atualizar_frames(dt)

    # ══════════════════════════════════════════════════════════════════
    # RENDERIZAÇÃO POR SPRITESHEET  (método público)
    # ══════════════════════════════════════════════════════════════════

    def draw(
        self,
        surface:   pygame.Surface,
        rect_tela: pygame.Rect | None = None,
    ) -> None:
        """
        Desenha o frame correto da spritesheet na tela.

        Efeito de piscar durante i-frames
        ──────────────────────────────────
        Enquanto invulneravel_timer > 0, o sprite alterna entre visível
        e invisível a cada PISCA_FREQUENCIA segundos.

        Matemática dt-based (determinística):
            fase = int(pisca_timer / PISCA_FREQUENCIA)
            visivel = (fase % 2 == 0)

        Com PISCA_FREQUENCIA=0.07s e 60 FPS:
          t=0.00–0.07  fase=0 (par)   → VISÍVEL
          t=0.07–0.14  fase=1 (ímpar) → INVISÍVEL
          t=0.14–0.21  fase=2 (par)   → VISÍVEL  ... (ciclo)

        Por que divisão inteira e não toggle booleano?
          Um bool toggle dependeria de ser executado exatamente uma vez
          por intervalo — sensível a lag spikes. A divisão inteira do
          tempo acumulado é determinística: para o mesmo pisca_timer,
          o resultado é sempre o mesmo, independente do FPS.

        Pipeline normal (sem i-frames):
          1. Escolhe atlas pela direção (animacoes_dir ou animacoes_esq)
          2. Indexa por [estado_animacao][frame_atual]
          3. Blita em rect_tela (screen-space com offset de câmera)

        Se rect_tela for None, usa self.rect — conveniente para testes.
        """
        # ── Efeito de piscar durante i-frames ─────────────────────────
        # Verifica se este frame deve ser invisível antes de qualquer blit.
        if self.invulneravel_timer > 0.0:
            fase = int(self.pisca_timer / self.PISCA_FREQUENCIA)
            if fase % 2 == 1:
                return   # frame invisível — sai sem desenhar nada

        # ── Renderização normal ────────────────────────────────────────
        destino = rect_tela if rect_tela is not None else self.rect
        atlas   = self.animacoes_dir if self.virado_direita else self.animacoes_esq
        frame   = atlas[self.estado_animacao][self.frame_atual]
        surface.blit(frame, destino)
