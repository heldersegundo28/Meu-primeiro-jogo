"""
player.py
═════════
Entidade principal do jogo — física, input, colisão, animação e game feel.
Protagonista: Calango Filhote — movimentação de nenenzinho com escalada.

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

A detecção de escalada ocorre no eixo X: colisão lateral + tecla de
movimento na mesma direção = calango agarrou a parede.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ESCALADA DE FILHOTE — FÍSICA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

O calango filhote tem garras fracas: consegue se agarrar em paredes
mas escorrega lentamente quando não está subindo ativamente.

Ciclo de estados da escalada:

  NO CHÃO → pressiona contra parede → ESCALANDO
  ESCALANDO:
    ↑ pressionado         → sobe (VEL_ESCALA_SOBE   = -100 px/s)
    ↓ pressionado         → desce (VEL_ESCALA_DESCE  = +120 px/s)
    sem tecla vertical    → escorrega (VEL_ESCORREGA = +40  px/s)
    direção oposta / CHÃO → desativa escalada normalmente
    ESPAÇO               → pulo de parede (wall-jump leve)
  ESCALANDO → toca o chão → desativa escalada automaticamente

Por que vel_y e não posição direta?
──────────────────────────────────────
Usar vel_y mantém o sistema de colisão AABB intacto: _resolve_collisions
continua detectando e corrigindo sobreposições normalmente. Se
manipulássemos rect.y diretamente, o jogador poderia "atravessar" tiles.

Gravidade durante escalada
───────────────────────────
_apply_gravity é ignorado quando self.escalando = True. Sem isso, a
gravidade acumularia vel_y rapidamente e superaria as velocidades de
escalada — o filhote escorregaria muito mais rápido do que o esperado.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GAME FEEL — COYOTE TIME E INPUT BUFFERING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Coyote Time:   janela de 0.15s após sair do chão onde o pulo é válido.
Input Buffer:  intenção de pulo fica "na fila" por 0.12s antes do pouso.

Juntos cobrem os dois lados da interação com o chão — controles que
"sentem" instantâneos mesmo com física discreta a 60 FPS.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ANIMAÇÃO POR SPRITESHEET — ARQUITETURA DE TRÊS CAMADAS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Camada 1 — QUAL sequência?   _atualizar_estado_animacao()
  Camada 2 — QUAL frame?       _atualizar_frames(dt)
  Camada 3 — COMO renderizar?  draw() → blit direto do atlas

Layout esperado da spritesheet (FRAME_WIDTH × FRAME_HEIGHT px):
  ┌──────────┬──────────┬──────────┬──────────┐
  │ idle   0 │ idle   1 │ idle   2 │ idle   3 │  row 0  (parado)
  ├──────────┼──────────┼──────────┼──────────┤
  │ run    0 │ run    1 │ run    2 │ run    3 │  row 1  (correndo)
  ├──────────┼──────────┼──────────┼──────────┤
  │ jump   0 │ jump   1 │ jump   2 │ jump   3 │  row 2  (pulando)
  ├──────────┼──────────┼──────────┼──────────┤
  │ climb  0 │ climb  1 │ climb  2 │ climb  3 │  row 3  (escalando) ← NOVO
  └──────────┴──────────┴──────────┴──────────┘

  Se a spritesheet não tiver a row 3, _carregar_animacoes() usa
  os frames de "parado" como fallback — o jogo não quebra.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FLAG DE EVENTO DE UM FRAME (pulou)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Player não conhece o sistema de áudio. self.pulou = True sinaliza ao
Game para tocar o SFX de pulo. One-Frame Event Flag: o Game lê e zera.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
I-FRAMES (INVULNERABILIDADE TEMPORÁRIA) E EFEITO DE PISCAR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

tomar_dano() → ativa invulneravel_timer = INVULNERAVEL_DURATION
update()     → decrementa invulneravel_timer com dt
tomar_dano() → se invulneravel_timer > 0: retorna False (bloqueado)

Efeito visual: pisca_timer acumula dt enquanto invulnerável. Fase par
= visível; fase ímpar = invisível. Determinístico e independente de FPS.
"""

from __future__ import annotations

import pygame

import config
from spritesheet import Spritesheet


class Player:
    """
    Calango Filhote — entidade controlada pelo jogador.

    Responsabilidades
    ─────────────────
    • Física:       gravidade, aceleração dt-based; escalada sem gravidade
    • Game feel:    Coyote Time + Input Buffering + wall-jump leve
    • Input:        horizontal, vertical (escalada), buffer de pulo
    • Colisão:      AABB por eixo separado; ativa escalada no eixo X
    • Animação:     FSM com 4 estados + CLIMB; fallback seguro
    • I-frames:     invulnerabilidade + efeito de piscar pós-dano

    Invariante central
    ───────────────────
    self.x / self.y  →  floats autoritativos (world-space)
    self.rect        →  derivado int; sincronizado após colisões
    """

    # ── Hitbox de colisão ─────────────────────────────────────────────
    WIDTH:  int = 40
    HEIGHT: int = 60

    # ── Física do filhote ─────────────────────────────────────────────
    # SPEED reduzida para 160 px/s: nenenzinho não corre perfeitamente.
    # GRAVITY e FORCA_PULO lidos de config — tuning centralizado.
    SPEED:      float = 160.0
    GRAVITY:    float = config.PLAYER_GRAVITY
    FORCA_PULO: float = config.PLAYER_JUMP_FORCE

    # ── Física de escalada ────────────────────────────────────────────
    #
    # VEL_ESCALA_SOBE:  vel_y ao pressionar ↑ na parede. Negativo = sobe.
    #   -100 px/s: lento, esforçado — sente-se o peso do filhote.
    #
    # VEL_ESCALA_DESCE: vel_y ao pressionar ↓. Positivo = desce.
    #   +120 px/s: desce mais rápido que sobe — garras fracas.
    #
    # VEL_ESCORREGA:    vel_y sem tecla vertical — "escorregamento" passivo.
    #   +40 px/s: lento o suficiente para o jogador reagir, rápido o
    #   suficiente para sentir o peso das garras fracas do filhote.
    #
    # FORCA_WALL_JUMP:  impulso horizontal ao pular da parede.
    #   Oposto à direção da parede — empurra o filhote para longe.
    VEL_ESCALA_SOBE:  float = -100.0
    VEL_ESCALA_DESCE: float =  120.0
    VEL_ESCORREGA:    float =   40.0
    FORCA_WALL_JUMP:  float =  220.0   # px/s lateral ao sair da parede

    # ── Game Feel ─────────────────────────────────────────────────────
    COYOTE_DURATION:      float = 0.15
    JUMP_BUFFER_DURATION: float = 0.12

    # ── Animação ──────────────────────────────────────────────────────
    TOTAL_FRAMES: int   = 4
    _INTERVALO:   float = config.VELOCIDADE_ANIMACAO

    # Mapeamento estado → linha da spritesheet.
    # "CLIMB" usa row 3 se disponível; _carregar_animacoes() faz fallback.
    _LINHA_SHEET: dict[str, int] = {
        "parado":   0,
        "correndo": 1,
        "pulando":  2,
        "CLIMB":    3,
    }

    # ── I-frames ──────────────────────────────────────────────────────
    INVULNERAVEL_DURATION: float = 1.5
    PISCA_FREQUENCIA:      float = 0.07

    # ── Knockback ─────────────────────────────────────────────────────
    KNOCKBACK_VY: float = -350.0
    KNOCKBACK_VX: float =  300.0

    # ──────────────────────────────────────────────────────────────────
    def __init__(self, x: float, y: float) -> None:
        """
        Inicializa física, escalada, timers de game feel e spritesheet.

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
        self.no_chao: bool = False

        # ── Escalada de filhote ───────────────────────────────────────
        # escalando: True enquanto o calango está agarrado a uma parede.
        #   Desativa gravidade; controla vel_y pelas teclas verticais.
        # _parede_dir: sinal da parede ativa (+1 = parede à direita,
        #   -1 = parede à esquerda). Usado para detectar desconexão
        #   (pressionar a direção oposta) e para o wall-jump.
        self.escalando:  bool  = False
        self._parede_dir: int  = 0   # +1 ou -1

        # ── Timers de game feel ───────────────────────────────────────
        self.coyote_timer:      float = 0.0
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

        # ── One-Frame Event Flag ──────────────────────────────────────
        self.pulou: bool = False

        # ── I-frames ──────────────────────────────────────────────────
        self.invulneravel_timer: float = 0.0
        self.pisca_timer:        float = 0.0

        # ── Spritesheet ───────────────────────────────────────────────
        self._carregar_animacoes()

    # ══════════════════════════════════════════════════════════════════
    # CARREGAMENTO DE ANIMAÇÕES
    # ══════════════════════════════════════════════════════════════════

    def _carregar_animacoes(self) -> None:
        """
        Carrega spritesheet e monta dicionários de animação com fallback.

        Para "CLIMB" (row 3): tenta carregar da spritesheet. Se a row
        não existir (sheet menor), usa os frames de "parado" como
        substituto — o jogo continua sem quebrar. O sprite idle durante
        a escalada é aceitável enquanto a arte não estiver pronta.

        O flip de direção é pré-calculado: draw() é O(1) de indexação.
        """
        sheet  = Spritesheet(config.SPRITE_PLAYER)
        escala = (self.WIDTH, self.HEIGHT)
        fw, fh, n = config.FRAME_WIDTH, config.FRAME_HEIGHT, self.TOTAL_FRAMES

        self.animacoes_dir: dict[str, list[pygame.Surface]] = {}
        self.animacoes_esq: dict[str, list[pygame.Surface]] = {}

        for estado, linha in self._LINHA_SHEET.items():
            if estado == "CLIMB":
                # Tenta carregar a linha de escalada; usa idle como fallback
                try:
                    frames_dir = sheet.get_sequencia(linha, n, fw, fh, escala=escala)
                    frames_esq = sheet.get_sequencia(
                        linha, n, fw, fh, escala=escala, espelhar_x=True
                    )
                    # Verifica se os frames retornados são válidos (não são
                    # todos iguais ao fallback magenta de largura 32x32 —
                    # um frame de 40x60 correto veio da sheet real)
                    self.animacoes_dir["CLIMB"] = frames_dir
                    self.animacoes_esq["CLIMB"] = frames_esq
                except Exception:
                    # Fallback: usa frames idle para não travar o jogo
                    self.animacoes_dir["CLIMB"] = self.animacoes_dir.get(
                        "parado", self.animacoes_dir.get("correndo", [])
                    )
                    self.animacoes_esq["CLIMB"] = self.animacoes_esq.get(
                        "parado", self.animacoes_esq.get("correndo", [])
                    )
            else:
                self.animacoes_dir[estado] = sheet.get_sequencia(
                    linha, n, fw, fh, escala=escala,
                )
                self.animacoes_esq[estado] = sheet.get_sequencia(
                    linha, n, fw, fh, escala=escala, espelhar_x=True,
                )

        # Garante que "CLIMB" sempre existe, mesmo que o loop falhe
        if "CLIMB" not in self.animacoes_dir:
            fallback_dir = self.animacoes_dir.get("parado", [])
            fallback_esq = self.animacoes_esq.get("parado", [])
            self.animacoes_dir["CLIMB"] = fallback_dir
            self.animacoes_esq["CLIMB"] = fallback_esq

    # ══════════════════════════════════════════════════════════════════
    # INPUT  (métodos públicos chamados pelo Game)
    # ══════════════════════════════════════════════════════════════════

    def handle_jump(self, event: pygame.event.Event) -> None:
        """
        Registra a intenção de pulo ou executa wall-jump se escalando.

        Durante escalada: ESPAÇO dispara o wall-jump diretamente (sem
        buffer — é uma ação imediata de desconexão da parede).
        Fora da escalada: registra no jump_buffer_timer normalmente.

        Por que KEYDOWN e não get_pressed()?
        KEYDOWN dispara UMA vez por pressionamento — o buffer não é
        reativado a cada frame enquanto Espaço está pressionado.
        """
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
                if self.escalando:
                    # Wall-jump: desconecta da parede e dá impulso
                    self._executar_wall_jump()
                else:
                    # Pulo normal: registra no buffer
                    self.jump_buffer_timer = self.JUMP_BUFFER_DURATION

    # ══════════════════════════════════════════════════════════════════
    # FÍSICA  (métodos públicos e privados)
    # ══════════════════════════════════════════════════════════════════

    def tomar_dano(self) -> bool:
        """
        Aplica dano se o jogador não estiver invulnerável.

        Retorna True se o dano foi aplicado (Game decrementa lives).
        Retorna False se invulnerável (Game ignora completamente).

        Tomar dano também encerra a escalada — o knockback lança o
        jogador para longe da parede.
        """
        if self.invulneravel_timer > 0.0:
            return False

        self.invulneravel_timer = self.INVULNERAVEL_DURATION
        self.pisca_timer        = 0.0

        # Encerra escalada antes de aplicar knockback
        self.escalando   = False
        self._parede_dir = 0

        self.vel_y = self.KNOCKBACK_VY
        self.vel_x = (
            -self.KNOCKBACK_VX if self.virado_direita
            else +self.KNOCKBACK_VX
        )

        self.no_chao           = False
        self.coyote_timer      = 0.0
        self.jump_buffer_timer = 0.0

        return True

    def _handle_input(self) -> None:
        """
        Lê o estado contínuo do teclado e define vel_x.

        Durante escalada, vel_x é forçado a zero — o calango não se
        move horizontalmente enquanto está agarrado. A direção do olhar
        é atualizada normalmente para refletir o lado da parede.
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
        """
        Acumula gravidade em vel_y, exceto durante a escalada.

        Quando escalando=True, a gravidade é suprimida completamente —
        vel_y é controlada exclusivamente por _processar_escalada().
        Sem esta supressão, a gravidade acumularia rapidamente e
        superaria as velocidades de escalada configuradas.
        """
        if not self.escalando:
            self.vel_y += self.GRAVITY * dt

    def _executar_pulo(self) -> None:
        """
        Aplica a força de pulo padrão (chão ou coyote).
        Reseta timers atomicamente para evitar pulos duplos.
        """
        self.vel_y             = self.FORCA_PULO
        self.no_chao           = False
        self.coyote_timer      = 0.0
        self.jump_buffer_timer = 0.0
        self.pulou             = True

    def _executar_wall_jump(self) -> None:
        """
        Pulo de parede: desconecta da parede e aplica impulso em arco.

        O impulso horizontal é OPOSTO à parede atual (_parede_dir):
          _parede_dir = +1 (parede à direita) → vel_x negativo (vai para ←)
          _parede_dir = -1 (parede à esquerda) → vel_x positivo (vai para →)

        O pulo vertical é menor que o pulo normal (60% de FORCA_PULO)
        para comunicar ao jogador que é um pulo de emergência, não de
        plataforma — expectativa correta de altura.

        Por que não usar FORCA_PULO completo?
        ────────────────────────────────────────
        Um wall-jump tão alto quanto o pulo normal tornaria a escalada
        muito poderosa: o filhote poderia escalar qualquer obstáculo
        via wall-jumps encadeados sem esforço. A redução preserva o
        desafio e a sensação de "garras fracas" do filhote.
        """
        self.escalando   = False
        self._parede_dir = 0

        # Impulso horizontal oposto à parede
        self.vel_x = -self._parede_dir * self.FORCA_WALL_JUMP

        # Impulso vertical reduzido (pulo de emergência)
        self.vel_y = self.FORCA_PULO * 0.60

        self.virado_direita = self.vel_x > 0
        self.no_chao        = False
        self.coyote_timer   = 0.0
        self.pulou          = True   # Game toca SFX de pulo

    def _pode_pular(self) -> bool:
        """True se o jogador pode pular (chão físico OU janela de coyote)."""
        return self.no_chao or self.coyote_timer > 0.0

    def _atualizar_timers_game_feel(self, dt: float) -> None:
        """
        Decrementa Coyote Timer e Jump Buffer após _resolve_collisions.

        Durante escalada: coyote_timer é mantido em zero — o jogador
        não ganha janela de coyote ao sair de uma parede (só do chão).
        O buffer de pulo também é zerado para que o handle_jump redirecione
        para wall-jump enquanto escalando=True.
        """
        if self.escalando:
            # Na parede: sem coyote (saiu de parede, não de chão)
            self.coyote_timer      = 0.0
            self.jump_buffer_timer = 0.0
            return

        if self.no_chao:
            self.coyote_timer = self.COYOTE_DURATION
        else:
            self.coyote_timer = max(0.0, self.coyote_timer - dt)

        self.jump_buffer_timer = max(0.0, self.jump_buffer_timer - dt)

    def _processar_pulo(self) -> None:
        """Executa pulo se buffer + condições alinhados. Não age se escalando."""
        if self.escalando:
            return   # wall-jump já tratado em handle_jump → KEYDOWN

        if self.jump_buffer_timer > 0.0 and self._pode_pular():
            self._executar_pulo()

    def _processar_escalada(self) -> None:
        """
        Controla vel_y e desconexão enquanto self.escalando = True.

        Chamado em update() ANTES de _resolve_collisions() para que a
        velocidade já esteja correta quando as colisões forem testadas.

        Hierarquia de teclas verticais (prioridade de cima para baixo):
          K_UP / K_w   → sobe  (VEL_ESCALA_SOBE)
          K_DOWN / K_s → desce (VEL_ESCALA_DESCE)
          nenhuma      → escorrega (VEL_ESCORREGA)

        Desconexão por direção oposta:
          _parede_dir = +1  e  vel_x < 0  → afastando da parede → solta
          _parede_dir = -1  e  vel_x > 0  → afastando da parede → solta
        """
        if not self.escalando:
            return

        keys = pygame.key.get_pressed()

        # ── Controle vertical ─────────────────────────────────────────
        subindo = keys[pygame.K_UP]   or keys[pygame.K_w]
        descendo = keys[pygame.K_DOWN] or keys[pygame.K_s]

        if subindo:
            self.vel_y = self.VEL_ESCALA_SOBE
        elif descendo:
            self.vel_y = self.VEL_ESCALA_DESCE
        else:
            # Escorregamento passivo — garras fracas do filhote
            self.vel_y = self.VEL_ESCORREGA

        # ── Detecção de desconexão por direção oposta ─────────────────
        # Se o jogador pressiona a direção CONTRÁRIA à parede, solta.
        # _parede_dir=+1 (parede à direita): vel_x<0 = pressionando ←
        # _parede_dir=-1 (parede à esquerda): vel_x>0 = pressionando →
        if (self._parede_dir == +1 and self.vel_x < 0) or \
           (self._parede_dir == -1 and self.vel_x > 0):
            self.escalando   = False
            self._parede_dir = 0
            # vel_y permanece como estava — o filhote "cai" da parede
            # naturalmente com o vel_y atual antes da gravidade retomar

    def _resolve_collisions(
        self,
        plataformas: pygame.sprite.Group,
        dt:          float,
    ) -> None:
        """
        Move o jogador e resolve colisões por eixo separado.

        Novidade: detecção de escalada no eixo X.
        ──────────────────────────────────────────
        Quando há colisão lateral E o jogador está pressionando a tecla
        de movimento NA MESMA DIREÇÃO da parede (tentando "entrar" nela),
        o calango ativa a escalada. O simples toque lateral sem intenção
        (ex.: inimigo empurrou o jogador) NÃO ativa a escalada.

        Condições para ativar escalada:
          1. vel_x > 0  e  colisão pela direita  (pressionando →, parede →)
          2. vel_x < 0  e  colisão pela esquerda (pressionando ←, parede ←)
          3. NÃO está no chão (não escalamos plataformas pelo chão)
          4. NÃO está invulnerável (knockback não ativa escalada)
        """
        # ── EIXO X ────────────────────────────────────────────────────
        self.x     += self.vel_x * dt
        self.rect.x = int(self.x)

        for plat in pygame.sprite.spritecollide(self, plataformas, False):
            if self.vel_x > 0:
                self.rect.right = plat.rect.left
                # Verificar escalada: pressionando → e colidiu com parede →
                if not self.no_chao and self.invulneravel_timer == 0.0:
                    self.escalando   = True
                    self._parede_dir = +1
                    self.vel_y       = 0.0          # cancela velocidade acumulada
                    self.coyote_timer = 0.0          # sem coyote de parede
            elif self.vel_x < 0:
                self.rect.left  = plat.rect.right
                # Verificar escalada: pressionando ← e colidiu com parede ←
                if not self.no_chao and self.invulneravel_timer == 0.0:
                    self.escalando   = True
                    self._parede_dir = -1
                    self.vel_y       = 0.0
                    self.coyote_timer = 0.0
            self.x     = float(self.rect.x)   # anti-jitter
            self.vel_x = 0.0

        # ── EIXO Y ────────────────────────────────────────────────────
        self.y     += self.vel_y * dt
        self.rect.y = int(self.y)

        self.no_chao = False

        for plat in pygame.sprite.spritecollide(self, plataformas, False):
            if self.vel_y > 0:
                self.rect.bottom = plat.rect.top
                self.no_chao     = True
                # Tocar o chão desativa a escalada
                if self.escalando:
                    self.escalando   = False
                    self._parede_dir = 0
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

        Prioridade (primeira condição verdadeira vence):
          1. escalando = True   → "CLIMB"   (domina tudo durante escalada)
          2. no ar              → "pulando"
          3. no chão + mov.     → "correndo"
          4. no chão parado     → "parado"

        Escalada tem prioridade máxima: mesmo que no_chao seja True
        (transição de frame), o estado visual já reflete a parede.
        """
        if self.escalando:
            novo = "CLIMB"
        elif not self.no_chao:
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
        Avança frame_atual pelo cronômetro.

        Anima em "correndo" e "CLIMB" — os outros estados ficam em
        frame 0. Usar -= em vez de = 0 preserva o "troco" de tempo
        para ritmo constante mesmo com lag spikes.
        """
        if self.estado_animacao in ("correndo", "CLIMB"):
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

        Ordem obrigatória
        ──────────────────
        1. Input horizontal   → vel_x, virado_direita
        2. Escalada           → vel_y controlado, checar desconexão
        3. Gravidade          → ignorada se escalando
        4. Colisões           → move, corrige, ativa/desativa escalada
        5. Sync floats        → re-sincroniza x/y ← rect final
        6. I-frames           → decrementa timers de invulnerabilidade
        7. Timers game feel   → coyote, buffer (zerados se escalando)
        8. Processar pulo     → chão/coyote; ignorado se escalando
        9. Estado animação    → lê escalando, no_chao, vel_x
       10. Frames animação    → avança cronômetro

        Por que escalada ANTES de gravidade (passo 2 antes de 3)?
        ────────────────────────────────────────────────────────────
        _processar_escalada() define vel_y. Se chamada DEPOIS de
        _apply_gravity(), a gravidade já teria acumulado em vel_y e
        seria necessário subtraí-la — mais frágil. Antes da gravidade,
        basta não chamar _apply_gravity quando escalando=True.
        """
        self._handle_input()
        self._processar_escalada()    # antes da gravidade
        self._apply_gravity(dt)       # ignorada internamente se escalando
        self._resolve_collisions(plataformas, dt)

        # Re-sincronização após todas as correções
        self.x = float(self.rect.x)
        self.y = float(self.rect.y)

        # ── I-frames ──────────────────────────────────────────────────
        if self.invulneravel_timer > 0.0:
            self.invulneravel_timer = max(0.0, self.invulneravel_timer - dt)
            self.pisca_timer       += dt
            if self.invulneravel_timer == 0.0:
                self.pisca_timer = 0.0

        # ── Game feel ─────────────────────────────────────────────────
        self._atualizar_timers_game_feel(dt)
        self._processar_pulo()

        self._atualizar_estado_animacao()
        self._atualizar_frames(dt)

    # ══════════════════════════════════════════════════════════════════
    # RENDERIZAÇÃO  (método público)
    # ══════════════════════════════════════════════════════════════════

    def draw(
        self,
        surface:   pygame.Surface,
        rect_tela: pygame.Rect | None = None,
    ) -> None:
        """
        Desenha o frame correto da spritesheet com efeito de piscar.

        Durante i-frames: alterna visível/invisível por PISCA_FREQUENCIA.
        Determinístico: mesmo pisca_timer → mesmo resultado (sem toggle).

        Fallback de atlas "CLIMB":
        Se animacoes_dir["CLIMB"] estiver vazio (sheet sem row 3),
        usa "parado" como segurança — o blit simplesmente não ocorre
        se a lista estiver vazia de alguma forma inesperada.
        """
        # ── Efeito de piscar durante i-frames ─────────────────────────
        if self.invulneravel_timer > 0.0:
            fase = int(self.pisca_timer / self.PISCA_FREQUENCIA)
            if fase % 2 == 1:
                return   # frame invisível

        # ── Renderização normal ────────────────────────────────────────
        destino = rect_tela if rect_tela is not None else self.rect
        atlas   = self.animacoes_dir if self.virado_direita else self.animacoes_esq

        # Garante que o estado existe no atlas (fallback para "parado")
        estado = self.estado_animacao if self.estado_animacao in atlas else "parado"
        frames = atlas[estado]

        if frames:
            frame = frames[self.frame_atual % len(frames)]
            surface.blit(frame, destino)
