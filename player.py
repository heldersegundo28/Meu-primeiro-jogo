"""
player.py
═════════
Entidade principal do jogo — física, input, colisão, animação e game feel.
Protagonista: Calango Filhote — movimentação de nenenzinho com escalada.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ORDEM DE EXECUÇÃO RÍGIDA DO update(dt)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

A ordem dos passos dentro de update() é IMUTÁVEL. Reordenar qualquer
passo introduz race conditions que são difíceis de reproduzir e ainda
mais difíceis de diagnosticar. Os motivos estão documentados abaixo.

  PASSO 1 — DECREMENTAR TIMERS
  ──────────────────────────────
  Os timers (coyote, buffer, i-frames, pisca) devem ser decrementados
  ANTES de qualquer leitura de input ou aplicação de física. Se
  decrementássemos após a colisão, o coyote_timer poderia ser lido
  com o valor do frame ANTERIOR no mesmo ciclo — 1 frame de janela
  extra invisível que cria inconsistência entre frames rápidos e lentos.

  PASSO 2 — INPUT & INTENÇÕES
  ──────────────────────────────
  vel_x e virado_direita são definidos aqui. Devem ser lidos antes da
  escalada (_processar_escalada usa vel_x para detectar desconexão)
  e antes da física (gravidade e colisão usam vel_x).

  PASSO 3 — ESCALADA (se ativa)
  ──────────────────────────────
  Deve vir ANTES da gravidade. _processar_escalada() define vel_y
  diretamente. Se chamada depois de _apply_gravity(), a gravidade já
  teria acumulado em vel_y — seria necessário subtraí-la, acoplando
  duas responsabilidades num único passo.

  PASSO 4 — GRAVIDADE
  ──────────────────────────────
  Acumula GRAVITY * dt em vel_y. Suprimida automaticamente se escalando.
  Aplica terminal velocity para evitar vel_y crescendo indefinidamente.

  PASSO 5 — COLISÃO EIXO X
  ──────────────────────────────
  Move rect.x por vel_x * dt. Detecta colisão lateral, corrige AABB,
  zera vel_x. Ativa escalada se input insistir na direção da parede.

  PASSO 6 — COLISÃO EIXO Y
  ──────────────────────────────
  Move rect.y por vel_y * dt. Detecta pouso (no_chao=True, recarrega
  coyote) ou colisão de teto (zera vel_y). Se não colidir: no_chao=False.
  CRÍTICO: no_chao só é confiável APÓS este passo.

  PASSO 7 — SINCRONIZAÇÃO DE FLOATS
  ──────────────────────────────────
  Após colisões, rect pode ter sido corrigido (int). Re-sincroniza
  self.x / self.y ← float(rect.x/y) para evitar "jitter" — divergência
  entre o float e o rect que causaria oscilação de 1px a cada frame.

  PASSO 8 — PULO (jump logic)
  ──────────────────────────────
  Lê jump_buffer_timer e coyote_timer (já decrementados no passo 1,
  já com no_chao atualizado no passo 6). Executa pulo APENAS se ambas
  as condições são verdadeiras neste frame. Zera os dois timers
  atomicamente para impedir double-jump.

  PASSO 9 — ANIMAÇÃO
  ──────────────────────────────
  Lê o estado físico final (no_chao, vel_x, vel_y, escalando) para
  determinar a row da spritesheet. Deve ser o ÚLTIMO passo de lógica
  para refletir fielmente o estado pós-colisão do frame atual.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FÍSICA COM DELTA TIME (dt-physics)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Integração de Euler semi-implícita:

    vel  +=  aceleração × dt   →  px/s
    pos  +=  vel        × dt   →  px

Multiplicar por dt garante comportamento idêntico a 30, 60 ou 120 FPS.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COLISÃO AABB POR EIXO SEPARADO — POR QUE É NECESSÁRIO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Mover X e Y juntos antes de resolver colisão perde a informação de qual
eixo causou o contato. O resultado é "wall-sticking": o personagem
gruda na parede ao pular rente a ela porque o solver não sabe se empurra
na horizontal ou na vertical.

Solução:
    1. Move só X  →  detecta colisão  →  corrige X (lateral)
    2. Move só Y  →  detecta colisão  →  corrige Y (pouso/teto)

Anti-jitter após cada correção:
    self.x = float(self.rect.x)   # rect foi corrigido (int) → float resincroniza
    Se não resincronizarmos: na próxima frame, pos float contradiz rect int,
    causando micro-oscilação de 1px a cada frame (jitter visual).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GAME FEEL — COYOTE TIME E INPUT BUFFERING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

                  pressiona ESPAÇO
                       │
                       ▼
               jump_buffer_timer = 0.12s ──► decrementa por dt
                                                    │
                                                    ▼ a cada frame
                                           jump_buffer_timer > 0 ?
                    sai da borda                    │ SIM
                         │                          ▼
                         ▼                 coyote_timer > 0 ?
               coyote_timer = 0.15s              │ SIM
               decrementa por dt                 ▼
                                          _executar_pulo()
                                          zera AMBOS os timers

  Coyote:  cobre "pulo perdido na borda" — o calango AINDA pode pular
           por 0.15s após sair da plataforma.
  Buffer:  cobre "pulo antecipado antes do pouso" — a intenção fica
           registrada por 0.12s; executa assim que tocar o chão.
  Juntos:  cobrem os dois lados da interação com o chão.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ESCALADA DE FILHOTE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  NO CHÃO + pressiona contra parede  →  ESCALANDO
  ESCALANDO:
    ↑ / W pressionado    →  sobe  (VEL_ESCALA_SOBE  = -100 px/s)
    ↓ / S pressionado    →  desce (VEL_ESCALA_DESCE = +120 px/s)
    sem tecla vertical   →  escorrega (VEL_ESCORREGA = +40 px/s)
    direção oposta       →  desativa, calango cai normalmente
    ESPAÇO               →  wall-jump (60% de FORCA_PULO)
    toca o chão          →  desativa automaticamente

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
I-FRAMES E EFEITO DE PISCAR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

tomar_dano()  →  invulneravel_timer = INVULNERAVEL_DURATION
update()      →  decrementa invulneravel_timer e pisca_timer por dt
draw()        →  fase = int(pisca_timer / PISCA_FREQUENCIA) % 2 == 1
                 → frame invisível se fase ímpar (determinístico, sem toggle)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LAYOUT DA SPRITESHEET
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ┌──────────┬──────────┬──────────┬──────────┐
  │ idle   0 │ idle   1 │ idle   2 │ idle   3 │  row 0  parado
  ├──────────┼──────────┼──────────┼──────────┤
  │ run    0 │ run    1 │ run    2 │ run    3 │  row 1  correndo
  ├──────────┼──────────┼──────────┼──────────┤
  │ jump   0 │ jump   1 │ jump   2 │ jump   3 │  row 2  pulando/caindo
  ├──────────┼──────────┼──────────┼──────────┤
  │ climb  0 │ climb  1 │ climb  2 │ climb  3 │  row 3  escalando
  └──────────┴──────────┴──────────┴──────────┘
  Cada célula: FRAME_WIDTH × FRAME_HEIGHT px (default 32×32)
  Row 3 ausente → fallback para row 0 (idle) sem quebrar o jogo.
"""

from __future__ import annotations

from tongue import Lingua, TongueState

import pygame

import config
from spritesheet import Spritesheet


class Player:
    """
    Calango Filhote — entidade controlada pelo jogador.

    Invariante central
    ───────────────────
    self.x / self.y  →  floats autoritativos (world-space)
    self.rect        →  derivado int; re-sincronizado após colisões
    """

    # ══════════════════════════════════════════════════════════════════
    # CONSTANTES DE CLASSE
    # ══════════════════════════════════════════════════════════════════

    # ── Hitbox ────────────────────────────────────────────────────────
    WIDTH:  int = 40
    HEIGHT: int = 60

    # ── Física horizontal ─────────────────────────────────────────────
    # 160 px/s: nenenzinho — não corre perfeitamente ainda.
    SPEED:      float = 160.0
    GRAVITY:    float = config.PLAYER_GRAVITY
    FORCA_PULO: float = config.PLAYER_JUMP_FORCE

    # Terminal velocity: impede vel_y crescer indefinidamente em quedas longas.
    # Sem este limite, quedas de fases muito altas gerariam velocidades que
    # "saltam" múltiplos tiles por frame — a colisão não detectaria corretamente.
    TERMINAL_VELOCITY: float = 900.0   # px/s máximo de queda

    # ── Física de escalada ────────────────────────────────────────────
    VEL_ESCALA_SOBE:  float = -100.0   # ↑ pressionado: sobe devagar
    VEL_ESCALA_DESCE: float =  120.0   # ↓ pressionado: desce mais rápido
    VEL_ESCORREGA:    float =   40.0   # sem tecla: escorregamento passivo
    FORCA_WALL_JUMP:  float =  220.0   # impulso horizontal do wall-jump

    # ── Game Feel ─────────────────────────────────────────────────────
    COYOTE_DURATION:      float = 0.15   # janela pós-borda (s)
    JUMP_BUFFER_DURATION: float = 0.10   # janela pré-pouso  (s)

    # ── I-frames ──────────────────────────────────────────────────────
    INVULNERAVEL_DURATION: float = 1.5    # proteção pós-dano (s)
    PISCA_FREQUENCIA:      float = 0.07   # ciclo visível/invisível (s)

    # ── Damage Flash — janela de silhueta sólida pós-dano ─────────────
    #
    # Nos primeiros DAMAGE_FLASH_DURACAO segundos após tomar dano,
    # o sprite é sobreposto por uma silhueta sólida de DAMAGE_FLASH_COR.
    # Após este período, o piscar normal de i-frames assume.
    #
    # Por que máscara e não Surface.fill()?
    # ─────────────────────────────────────────────────────────────────
    # Surface.fill() preencheria todo o retângulo bounding-box, incluindo
    # pixels transparentes ao redor do sprite — o resultado seria um
    # bloco sólido retangular, não a silhueta do personagem.
    # pygame.mask.from_surface() isola exatamente os pixels opacos do
    # frame atual, preservando o contorno pixel-perfect do sprite.
    # A máscara é gerada a partir do frame já escalado (pós S&S) para
    # que a silhueta corresponda ao visual atual do personagem.
    #
    # DAMAGE_FLASH_COR: branco puro é o padrão clássico (Mega Man, Celeste).
    DAMAGE_FLASH_DURACAO: float = 0.10            # segundos de silhueta sólida
    DAMAGE_FLASH_COR:     tuple = (255, 255, 255)  # RGB do flash (branco puro)

    # ── Knockback ─────────────────────────────────────────────────────
    # ── Sistema de vida ──────────────────────────────────────────────
    # VIDA_MAXIMA: vidas com que o jogador começa a campanha.
    # Lido em __init__ para inicializar vida_maxima e vida_atual.
    VIDA_MAXIMA: int = 3
    # ── Autotomia (Perda da Cauda) ──────────────────────────────────
    # PLAYER_START_WITH_TAIL: False desabilita a mecânica para testes.
    # TAIL_IFRAME_DURATION: invulnerabilidade longa pós-autotomia.
    # TAIL_SHAKE_*: configuram o impacto visual (bem maior que dano normal).
    PLAYER_START_WITH_TAIL:  bool  = True
    TAIL_IFRAME_DURATION:    float = 2.5
    TAIL_SHAKE_DURATION:     float = 0.35
    TAIL_SHAKE_INTENSITY:    int   = 14


    KNOCKBACK_VY: float = -350.0
    KNOCKBACK_VX: float =  300.0

    # ── Animação ──────────────────────────────────────────────────────
    TOTAL_FRAMES: int   = 4
    _INTERVALO:   float = config.VELOCIDADE_ANIMACAO

    _LINHA_SHEET: dict[str, int] = {
        "parado":   0,
        "correndo": 1,
        "pulando":  2,
        "CLIMB":    3,
    }

    # ── Squash & Stretch — constantes visuais (puramente estéticas) ───
    #
    # Todas as constantes ficam aqui, não espalhadas pelo código.
    # Alterar o "feel" visual requer mudar apenas este bloco.
    #
    # SS_SQUASH_Y / SS_SQUASH_X
    #   Deformação aplicada no momento do pouso (Landing Impact).
    #   Squash = comprimir verticalmente (Y < 1.0) + alargar horizontalmente (X > 1.0).
    #   O par (X, Y) é inversamente proporcional: área visual aproximadamente conservada.
    #   Escala por vel_impacto: quedas maiores → squash maior (clampeado).
    #
    # SS_STRETCH_Y / SS_STRETCH_X
    #   Deformação aplicada no instante do pulo.
    #   Stretch = esticar verticalmente (Y > 1.0) + comprimir horizontalmente (X < 1.0).
    #
    # SS_FALL_STRETCH_FATOR
    #   Quanto do vel_y atual se converte em stretch visual durante a queda.
    #   Leitura puramente visual — nunca escreve em variáveis de física.
    #
    # SS_RECUPERACAO
    #   Taxa de retorno para (1.0, 1.0) por segundo. Lerp multiplicado por dt.
    #   Maior valor = recuperação mais rápida (feel mais "snappy").
    #   Independente de FPS: lerp(atual, 1.0, taxa × dt) é frame-rate-independent.
    #
    # Limites de clamp (min/max) garantem que quedas extremas ou bugs de física
    # nunca gerem distorções bizarras (escala negativa, sprite desaparecendo).
    SS_SQUASH_Y_MAX:       float = 0.55    # Y mínimo no squash (mais comprimido)
    SS_SQUASH_X_MAX:       float = 1.40    # X máximo no squash (mais largo)
    SS_SQUASH_FATOR:       float = 0.0008  # vel_impacto → intensidade de squash
    SS_STRETCH_Y:          float = 1.30    # Y no pulo (esticado)
    SS_STRETCH_X:          float = 0.80    # X no pulo (comprimido)
    SS_FALL_STRETCH_FATOR: float = 0.0003  # vel_y → stretch visual na queda
    SS_FALL_STRETCH_MAX:   float = 0.20    # delta máximo de stretch na queda
    SS_RECUPERACAO:        float = 8.0     # taxa de lerp para (1.0, 1.0) por segundo

    # ──────────────────────────────────────────────────────────────────
    def __init__(self, x: float, y: float) -> None:
        """
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

        # ── Escalada ──────────────────────────────────────────────────
        self.escalando:   bool = False
        self._parede_dir: int  = 0   # +1 = direita | -1 = esquerda

        # ── Timers de game feel ───────────────────────────────────────
        # Todos decrementados no PASSO 1 do update() para garantir
        # que as leituras subsequentes usem valores do frame atual.
        self.coyote_timer:      float = 0.0
        self.jump_buffer_timer: float = 0.0

        # ── I-frames ──────────────────────────────────────────────────
        # ── Vida e morte ─────────────────────────────────────────────
        # vida_maxima / vida_atual: campos canônicos; o Game lê vida_atual
        # para HUD e Game Over. Não decrementar fora de tomar_dano().
        # morto: True sinaliza para o Game disparar Game Over no próx. frame.
        self.vida_maxima: int  = self.VIDA_MAXIMA
        self.vida_atual:  int  = self.vida_maxima
        self.morto:       bool = False

        # ── Autotomia ─────────────────────────────────────────────────
        # tem_cauda: True = cauda disponível como escudo fatal.
        # just_lost_tail: One-Frame Flag (edge-triggered, como just_landed).
        #   Zerada em _decrementar_timers(), levantada em tomar_dano().
        #   Main.py lê e despacha: shake, partículas, SFX especial.
        self.tem_cauda:      bool = self.PLAYER_START_WITH_TAIL
        self.just_lost_tail: bool = False   # One-Frame Flag

        # ── Língua ────────────────────────────────────────────────────
        # Módulo autônomo — toda a lógica de estados, física e hitbox
        # vive em tongue.py. Player apenas gerencia o input e expõe
        # self.lingua para que o Game atualize e desenhe.
        self.lingua: Lingua = Lingua()

        self.invulneravel_timer: float = 0.0
        self.pisca_timer:        float = 0.0

        # ── Rect de colisão (world-space, int) ────────────────────────
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
        # True quando pulo é executado. Game lê, toca SFX e zera.
        self.pulou: bool = False

        # ── Landing Impact — telemetria Read-Only para o Game ─────────
        #
        # just_landed: Edge-Triggered flag — True APENAS no frame exato
        #   da transição ar → chão. Zerada no PASSO 1 de cada update()
        #   para garantir duração de exatamente 1 frame.
        #   O Game usa esta flag para decidir se dispara o screen shake
        #   de impacto. O Player nunca sabe da existência do shake.
        #
        # velocidade_impacto: snapshot de vel_y no momento do pouso.
        #   Dado de telemetria puro — capturado ANTES de vel_y ser zerado
        #   pela colisão. Permite ao Game calcular a intensidade proporcional.
        #   Nunca deve ser escrito por código externo (Read-Only por convenção).
        self.just_landed:       bool  = False
        self.velocidade_impacto: float = 0.0

        # ── Squash & Stretch — estado visual (não afeta hitbox) ────────
        #
        # squash_stretch_x / squash_stretch_y: fatores de escala visual atuais.
        #   1.0  = proporção original (sem deformação).
        #   < 1.0 = comprimido naquele eixo.
        #   > 1.0 = esticado naquele eixo.
        #
        # Modificados em _colidir_eixo_y (pouso) e _executar_pulo.
        # Recuperados em _atualizar_squash_stretch() no PASSO 9.
        # NUNCA tocam self.rect — exclusivos para draw().
        self.squash_stretch_x: float = 1.0
        self.squash_stretch_y: float = 1.0

        # ── Timer cosmético de poeira de corrida ───────────────────────
        # Não afeta física. Decrementado em _decrementar_timers (PASSO 1)
        # e lido pelo Game para ritmar a emissão de partículas enquanto
        # o calango corre no chão — evita uma linha contínua de poeira.
        # O Game zera ou decrementa; o Player apenas expõe o valor.
        self.poeira_corrida_timer: float = 0.0

        # ── Spritesheet ───────────────────────────────────────────────
        self._carregar_animacoes()

    # ══════════════════════════════════════════════════════════════════
    # CARREGAMENTO DE ANIMAÇÕES
    # ══════════════════════════════════════════════════════════════════

    def _carregar_animacoes(self) -> None:
        """
        Carrega spritesheet e monta atlas dir/esq com fallback para CLIMB.

        O flip horizontal é pré-calculado no carregamento (custo O(1) em
        draw). Row 3 ausente → frames de "parado" como substituto seguro.
        """
        sheet  = Spritesheet(config.SPRITE_PLAYER)
        escala = (self.WIDTH, self.HEIGHT)
        fw, fh, n = config.FRAME_WIDTH, config.FRAME_HEIGHT, self.TOTAL_FRAMES

        self.animacoes_dir: dict[str, list[pygame.Surface]] = {}
        self.animacoes_esq: dict[str, list[pygame.Surface]] = {}

        for estado, linha in self._LINHA_SHEET.items():
            if estado == "CLIMB":
                try:
                    self.animacoes_dir["CLIMB"] = sheet.get_sequencia(
                        linha, n, fw, fh, escala=escala
                    )
                    self.animacoes_esq["CLIMB"] = sheet.get_sequencia(
                        linha, n, fw, fh, escala=escala, espelhar_x=True
                    )
                except Exception:
                    # Row 3 não existe na sheet — usa idle como fallback
                    self.animacoes_dir["CLIMB"] = self.animacoes_dir.get("parado", [])
                    self.animacoes_esq["CLIMB"] = self.animacoes_esq.get("parado", [])
            else:
                self.animacoes_dir[estado] = sheet.get_sequencia(
                    linha, n, fw, fh, escala=escala
                )
                self.animacoes_esq[estado] = sheet.get_sequencia(
                    linha, n, fw, fh, escala=escala, espelhar_x=True
                )

        # Guarda final: garante que "CLIMB" existe mesmo se o loop falhar
        if "CLIMB" not in self.animacoes_dir:
            self.animacoes_dir["CLIMB"] = self.animacoes_dir.get("parado", [])
            self.animacoes_esq["CLIMB"] = self.animacoes_esq.get("parado", [])

    # ══════════════════════════════════════════════════════════════════
    # INPUT  (chamados pelo Game)
    # ══════════════════════════════════════════════════════════════════

    def handle_jump(self, event: pygame.event.Event) -> None:
        """
        Registra intenção de pulo (buffer) ou executa wall-jump imediato.

        KEYDOWN garante disparo único por pressionamento — get_pressed()
        reativaria o buffer a cada frame enquanto Espaço está pressionado.
        """
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
                if self.escalando:
                    self._executar_wall_jump()
                else:
                    self.jump_buffer_timer = self.JUMP_BUFFER_DURATION

    # ══════════════════════════════════════════════════════════════════
    # FÍSICA — métodos atômicos privados
    # ══════════════════════════════════════════════════════════════════

    def handle_lingua(self, event: pygame.event.Event) -> None:
        """
        Processa o input de disparo da língua (tecla X).

        Padrão idêntico ao handle_jump: KEYDOWN garante disparo único
        por pressionamento — get_pressed() dispararia a cada frame.

        A origem (boca) é o midright ou midleft do rect, dependendo
        de virado_direita. A língua segue o Player via update() a cada
        frame — o valor aqui é apenas o disparo inicial.
        """
        if event.type != pygame.KEYDOWN:
            return
        if event.key != pygame.K_x:
            return

        # Origem da língua: boca do calango (centro lateral do rect)
        if self.virado_direita:
            origem_x = float(self.rect.right)
            direcao  = 1
        else:
            origem_x = float(self.rect.left)
            direcao  = -1
        origem_y = float(self.rect.centery)

        self.lingua.disparar(origem_x, origem_y, direcao)

    def tomar_dano(self, origem_x: float | None = None) -> bool:
        """
        Aplica dano ao Player se não estiver invulnerável.

        Retorna True se o dano foi efetivamente aplicado.
        Retorna False se o jogador está nos i-frames — Game ignora o hit.

        Parâmetros
        ──────────
        origem_x : X do centro do inimigo (world-space).
                   Inimigo à direita → knockback para esquerda (vel_x < 0).
                   Inimigo à esquerda → knockback para direita (vel_x > 0).
                   None → fallback legado via self.virado_direita.

        Responsabilidades internas
        ──────────────────────────
        • Verificar i-frames
        • Decrementar vida_atual
        • Marcar morto=True se vida_atual <= 0
        • Iniciar i-frames
        • Aplicar knockback direcional
        • Cancelar escalada e timers

        Para futura perda de cauda
        ──────────────────────────
        Adicionar antes do `return True`:
            if self.cauda > 0: self.cauda -= 1
        Zero mudança na assinatura ou no sistema de dano.
        """
        if self.invulneravel_timer > 0.0:
            return False

        # ── Direção do knockback ──────────────────────────────────────
        if origem_x is not None:
            inimigo_a_direita = origem_x > self.rect.centerx
        else:
            inimigo_a_direita = self.virado_direita   # fallback legado

        # ── Vida e Autotomia ──────────────────────────────────────────
        # Fluxo de decisão (em ordem de prioridade):
#
#   vida > 1          → dano normal: decrementa, i-frame padrão
#   vida == 1 + cauda → AUTOTOMIA: vida=1, cauda=False, i-frame longo
#   vida == 1 sem cau → morte definitiva: morto=True, GAME OVER
#
        vida_apos_dano = self.vida_atual - 1

        if vida_apos_dano <= 0 and self.tem_cauda:
            # ── AUTOTOMIA ─────────────────────────────────────────────
            # Cancela morte: vida permanece 1; cauda absorve o golpe
            self.vida_atual      = 1
            self.tem_cauda       = False
            self.just_lost_tail  = True          # dispara eventos no Game
            self.invulneravel_timer = self.TAIL_IFRAME_DURATION
            self.pisca_timer        = 0.0

        elif vida_apos_dano <= 0:
            # ── MORTE DEFINITIVA ──────────────────────────────────────
            # Sem cauda: golpe fatal → morto=True
            self.vida_atual = 0
            self.morto      = True
            self.invulneravel_timer = self.INVULNERAVEL_DURATION
            self.pisca_timer        = 0.0

        else:
            # ── DANO NORMAL ───────────────────────────────────────────
            self.vida_atual = vida_apos_dano
            self.invulneravel_timer = self.INVULNERAVEL_DURATION
            self.pisca_timer        = 0.0

        # ── Física ────────────────────────────────────────────────────
        self.escalando          = False
        self._parede_dir        = 0
        self.no_chao            = False
        self.coyote_timer       = 0.0
        self.jump_buffer_timer  = 0.0
        self.vel_y              = self.KNOCKBACK_VY
        self.vel_x              = (
            -self.KNOCKBACK_VX if inimigo_a_direita
            else +self.KNOCKBACK_VX
        )
        return True

    def _decrementar_timers(self, dt: float) -> None:
        """
        PASSO 1 — Decrementa todos os timers pelo dt do frame atual.

        Executado PRIMEIRO em update() para que qualquer leitura
        posterior use valores já decrementados — sem off-by-one-frame.

        coyote_timer e jump_buffer_timer usam max(0, ...) para nunca
        ficarem negativos. invulneravel_timer idem. pisca_timer acumula
        (não decrementa) enquanto invulnerável — zerado ao sair.

        just_landed é zerada aqui para garantir duração de exatamente
        1 frame — Edge-Triggered, não Level-Triggered.
        """
        # ── Landing Impact: reset da flag de borda ────────────────────
        # Zerada no início do frame para que o valor lido pelo Game no
        # frame anterior não persista. Será levantada novamente em
        # _colidir_eixo_y() SE houver pouso neste frame específico.
        self.just_landed    = False
        self.just_lost_tail = False   # autotomia: edge-trigger reset

        # ── Timer cosmético de poeira de corrida ───────────────────────
        # Decrementado aqui (junto com os outros timers) para que o Game
        # leia um valor já atualizado quando processar os gatilhos visuais.
        self.poeira_corrida_timer = max(0.0, self.poeira_corrida_timer - dt)
        # ── Coyote Time ───────────────────────────────────────────────
        if not self.escalando:
            if self.no_chao:
                # No chão: recarrega janela para a próxima borda
                self.coyote_timer = self.COYOTE_DURATION
            else:
                self.coyote_timer = max(0.0, self.coyote_timer - dt)

        # ── Jump Buffer ───────────────────────────────────────────────
        if not self.escalando:
            self.jump_buffer_timer = max(0.0, self.jump_buffer_timer - dt)

        # ── I-frames ──────────────────────────────────────────────────
        if self.invulneravel_timer > 0.0:
            self.invulneravel_timer = max(0.0, self.invulneravel_timer - dt)
            self.pisca_timer       += dt
            if self.invulneravel_timer == 0.0:
                self.pisca_timer = 0.0   # reset limpo ao sair dos i-frames

    def _ler_input(self) -> None:
        """
        PASSO 2 — Lê teclado e define vel_x / virado_direita.

        get_pressed() é correto aqui: queremos o estado CONTÍNUO enquanto
        a tecla está pressionada (movimento suave), não um evento único.
        """
        keys       = pygame.key.get_pressed()
        self.vel_x = 0.0

        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.vel_x          = -self.SPEED
            self.virado_direita = False

        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.vel_x          = +self.SPEED
            self.virado_direita = True

    def _processar_escalada(self) -> None:
        """
        PASSO 3 — Define vel_y e detecta desconexão durante escalada.

        Executado ANTES de _aplicar_gravidade() para que vel_y esteja
        correto quando a gravidade for avaliada (que é suprimida se
        escalando=True — sem este passo antes, não saberíamos suprimir).
        """
        if not self.escalando:
            return

        keys     = pygame.key.get_pressed()
        subindo  = keys[pygame.K_UP]   or keys[pygame.K_w]
        descendo = keys[pygame.K_DOWN] or keys[pygame.K_s]

        if subindo:
            self.vel_y = self.VEL_ESCALA_SOBE
        elif descendo:
            self.vel_y = self.VEL_ESCALA_DESCE
        else:
            self.vel_y = self.VEL_ESCORREGA

        # Desconexão por direção oposta à parede
        if (self._parede_dir == +1 and self.vel_x < 0) or \
           (self._parede_dir == -1 and self.vel_x > 0):
            self.escalando   = False
            self._parede_dir = 0

    def _aplicar_gravidade(self, dt: float) -> None:
        """
        PASSO 4 — Acumula gravidade em vel_y, com terminal velocity.

        Suprimida quando escalando=True (vel_y é controlada pelo PASSO 3).

        Terminal velocity: clampeia vel_y em TERMINAL_VELOCITY para evitar
        que quedas longas gerem velocidades que "saltam" tiles inteiros —
        o que tornaria a detecção de colisão Y ineficaz (tunneling).
        """
        if self.escalando:
            return

        self.vel_y += self.GRAVITY * dt
        if self.vel_y > self.TERMINAL_VELOCITY:
            self.vel_y = self.TERMINAL_VELOCITY

    def _colidir_eixo_x(
        self,
        plataformas: pygame.sprite.Group,
        dt:          float,
    ) -> None:
        """
        PASSO 5 — Move em X, detecta colisão lateral e ativa escalada.

        Anti-jitter: após corrigir rect.x (int), sincroniza self.x (float)
        imediatamente para que a próxima integração parta do valor correto.

        Ativação de escalada
        ─────────────────────
        Condições simultâneas:
          a) Colisão lateral detectada (rect encosta na parede)
          b) vel_x aponta na direção da parede (input intencional)
          c) NOT no_chao (escalamos paredes, não bordas de plataformas)
          d) NOT invulnerável (knockback não deve ativar escalada)
        """
        self.x     += self.vel_x * dt
        self.rect.x = int(self.x)

        for plat in pygame.sprite.spritecollide(self, plataformas, False):
            if self.vel_x > 0:
                self.rect.right = plat.rect.left
                if not self.no_chao and self.invulneravel_timer == 0.0:
                    self.escalando    = True
                    self._parede_dir  = +1
                    self.vel_y        = 0.0   # cancela acúmulo de gravidade
                    self.coyote_timer = 0.0   # sem coyote de parede
            elif self.vel_x < 0:
                self.rect.left  = plat.rect.right
                if not self.no_chao and self.invulneravel_timer == 0.0:
                    self.escalando    = True
                    self._parede_dir  = -1
                    self.vel_y        = 0.0
                    self.coyote_timer = 0.0

            self.x     = float(self.rect.x)   # ← anti-jitter
            self.vel_x = 0.0

    def _colidir_eixo_y(
        self,
        plataformas: pygame.sprite.Group,
        dt:          float,
    ) -> None:
        """
        PASSO 6 — Move em Y, detecta pouso/teto e atualiza no_chao.

        no_chao é zerado no início e só fica True se houver colisão de
        pouso neste frame — qualquer leitura de no_chao APÓS este passo
        reflete o estado físico real do frame atual.

        Pouso: desativa escalada (o calango chegou ao chão).
        Teto:  zera vel_y (impede acúmulo de velocidade "para dentro" do bloco).
        """
        self.y     += self.vel_y * dt
        self.rect.y = int(self.y)

        self.no_chao = False   # será True apenas se houver colisão de pouso

        for plat in pygame.sprite.spritecollide(self, plataformas, False):
            if self.vel_y > 0:   # caindo → pouso
                self.rect.bottom  = plat.rect.top

                # ── Landing Impact — captura de telemetria ────────────
                # Edge-Triggered: dispara APENAS na transição ar → chão.
                #
                # Por que usar `not self.no_chao` como guarda?
                # ─────────────────────────────────────────────────────
                # no_chao ainda é False neste ponto do loop (foi zerado
                # em _decrementar_timers → PASSO 1, e não foi modificado
                # até a próxima linha). Isso é exatamente o sentinela que
                # precisamos: "estava no ar no início deste frame".
                #
                # Ao checar ANTES de setar no_chao=True, detectamos a
                # borda ar→chão de forma determinística. Qualquer frame
                # onde o calango já estava no chão terá no_chao=True
                # aqui (recarregado em _decrementar_timers) e a flag
                # NÃO será disparada — sem falsos positivos ao caminhar.
                #
                # velocidade_impacto capturada ANTES de vel_y ser zerada
                # (linhas abaixo) — único momento em que o valor existe.
                if not self.no_chao:
                    self.velocidade_impacto = self.vel_y   # Read-Only snapshot
                    self.just_landed        = True         # 1-frame edge flag

                    # ── Squash no impacto ─────────────────────────────
                    # Proporcional à velocidade de queda, clampeado pelos
                    # limites de classe. Conservação visual aproximada:
                    # quando Y encolhe, X alarga (área ≈ constante).
                    intensidade = min(
                        self.vel_y * self.SS_SQUASH_FATOR, 1.0
                    )
                    # Y: comprimir (1.0 → SS_SQUASH_Y_MAX)
                    self.squash_stretch_y = max(
                        self.SS_SQUASH_Y_MAX,
                        1.0 - intensidade * (1.0 - self.SS_SQUASH_Y_MAX),
                    )
                    # X: alargar inversamente (1.0 → SS_SQUASH_X_MAX)
                    self.squash_stretch_x = min(
                        self.SS_SQUASH_X_MAX,
                        1.0 + intensidade * (self.SS_SQUASH_X_MAX - 1.0),
                    )

                self.no_chao = True

                # Tocar o chão sempre encerra escalada
                if self.escalando:
                    self.escalando   = False
                    self._parede_dir = 0

            elif self.vel_y < 0:   # subindo → teto
                self.rect.top = plat.rect.bottom

            self.y     = float(self.rect.y)   # ← anti-jitter
            self.vel_y = 0.0

    def _aplicar_limites_mundo(self) -> None:
        """Impede que o calango saia pelas bordas horizontais do mundo."""
        self.x      = max(0.0, min(self.x, float(config.WORLD_WIDTH - self.WIDTH)))
        self.rect.x = int(self.x)

    def _executar_pulo(self) -> None:
        """
        Aplica força de pulo e zera ambos os timers atomicamente.

        Atomicidade: zerar coyote E buffer juntos impede que uma segunda
        leitura no mesmo frame encontre buffer > 0 e coyote > 0 novamente.

        Squash & Stretch: aplica stretch vertical no instante do salto.
        Y > 1.0 (esticado) + X < 1.0 (comprimido) — sensação de impulso.
        """
        self.vel_y             = self.FORCA_PULO
        self.no_chao           = False
        self.coyote_timer      = 0.0
        self.jump_buffer_timer = 0.0
        self.pulou             = True

        # ── Stretch no pulo ───────────────────────────────────────────
        # Valores fixos (não proporcionais): o pulo tem força constante,
        # então o stretch também é constante — previsível e legível.
        self.squash_stretch_y = self.SS_STRETCH_Y
        self.squash_stretch_x = self.SS_STRETCH_X

    def _executar_wall_jump(self) -> None:
        """
        Pulo de parede: impulso lateral oposto + vertical reduzido (60%).

        60% de FORCA_PULO: comunica "pulo de emergência", não de plataforma.
        Se fosse 100%, wall-jumps encadeados tornariam escalada trivial.
        """
        direcao_saida    = -self._parede_dir
        self.escalando   = False
        self._parede_dir = 0
        self.vel_x       = direcao_saida * self.FORCA_WALL_JUMP
        self.vel_y       = self.FORCA_PULO * 0.60
        self.virado_direita = self.vel_x > 0
        self.no_chao        = False
        self.coyote_timer   = 0.0
        self.pulou          = True

    def _processar_pulo_buffer(self) -> None:
        """
        PASSO 8 — Executa pulo se buffer e coyote estiverem alinhados.

        Lê timers já decrementados (PASSO 1) e no_chao já atualizado
        (PASSO 6) — única janela onde todos os valores são confiáveis.
        Não age se escalando (wall-jump é tratado em handle_jump via KEYDOWN).
        """
        if self.escalando:
            return
        pode_pular = self.no_chao or self.coyote_timer > 0.0
        if self.jump_buffer_timer > 0.0 and pode_pular:
            self._executar_pulo()

    # ══════════════════════════════════════════════════════════════════
    # ANIMAÇÃO  (métodos privados)
    # ══════════════════════════════════════════════════════════════════

    def _atualizar_squash_stretch(self, dt: float) -> None:
        """
        PASSO 9a — Recupera squash_stretch_x/y para (1.0, 1.0) via lerp dt-based.
        Também aplica Fall Stretch leve durante a queda (telemetria de vel_y).

        Recuperação por lerp
        ─────────────────────
        lerp(atual, alvo, taxa × dt) é frame-rate-independent:
          a 60 FPS: dt ≈ 0.0167 → fator ≈ 0.133  por frame
          a 30 FPS: dt ≈ 0.0333 → fator ≈ 0.267  por frame
          a 144 FPS: dt ≈ 0.0069 → fator ≈ 0.055 por frame
        Em todos os casos o somatório de fatores por segundo ≈ SS_RECUPERACAO,
        garantindo que o tempo visual de recuperação seja idêntico em qualquer FPS.

        Fall Stretch visual
        ────────────────────
        Durante a queda (vel_y > 0, não escalando), o calango estica
        levemente no eixo Y proporcional à velocidade. Isso reforça a
        sensação de aceleração gravitacional sem mover nada fisicamente.
        vel_y é lido como telemetria Read-Only — nunca escrito aqui.

        Por que aplicar ANTES da recuperação?
        ───────────────────────────────────────
        O fall stretch define um "alvo visual em movimento" que compete
        com a recuperação. Aplicando primeiro, a recuperação no mesmo frame
        imediatamente atenua o stretch — o efeito resultante é uma deformação
        suave proporcional a vel_y, não um salto brusco de valor.
        """
        # ── Fall Stretch (telemetria visual, Read-Only) ───────────────
        # Só aplica se estiver caindo com velocidade significativa e
        # não estiver escalando (parede já tem comportamento próprio).
        if not self.no_chao and not self.escalando and self.vel_y > 0:
            delta = min(
                self.vel_y * self.SS_FALL_STRETCH_FATOR,
                self.SS_FALL_STRETCH_MAX,
            )
            # Estica Y e comprime X levemente — inversamente proporcionais
            alvo_y = min(1.0 + delta, 1.0 + self.SS_FALL_STRETCH_MAX)
            alvo_x = max(1.0 - delta * 0.4, 1.0 - self.SS_FALL_STRETCH_MAX * 0.4)
        else:
            # Em repouso ou escalada: alvo é proporção original
            alvo_y = 1.0
            alvo_x = 1.0

        # ── Recuperação via lerp multiplicado por dt ──────────────────
        # lerp(a, b, t) = a + (b - a) * t
        # O alvo_y/alvo_x pode ser diferente de 1.0 durante a queda —
        # isso faz a recuperação perseguir o alvo corrente, não sempre 1.0.
        taxa = self.SS_RECUPERACAO * dt
        self.squash_stretch_y += (alvo_y - self.squash_stretch_y) * taxa
        self.squash_stretch_x += (alvo_x - self.squash_stretch_x) * taxa

        # ── Clamp absoluto — blindagem contra anomalias de física ──────
        # Garante que mesmo em lag spikes extremos (dt muito grande) os
        # fatores nunca ultrapassem os limites configurados.
        self.squash_stretch_y = max(self.SS_SQUASH_Y_MAX,
                                    min(self.squash_stretch_y, self.SS_STRETCH_Y))
        self.squash_stretch_x = max(self.SS_STRETCH_X,
                                    min(self.squash_stretch_x, self.SS_SQUASH_X_MAX))

    def _atualizar_estado_animacao(self) -> None:
        """
        PASSO 9 — Determina row da spritesheet pelo estado físico final.

        Prioridade (primeira verdadeira vence):
          1. escalando   →  "CLIMB"    (domina qualquer vel)
          2. vel_y < 0   →  "pulando"  (subindo)
          3. vel_y > 0   →  "pulando"  (caindo — mesma row, frame diferente)
          4. vel_x ≠ 0   →  "correndo"
          5. parado      →  "parado"

        Ao trocar de estado: reinicia frame e cronômetro para não
        "entrar no meio" de uma animação.
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
        PASSO 9b — Avança frame_atual pelo cronômetro.

        Usa -= em vez de = 0 para preservar o "troco" de tempo —
        ritmo constante mesmo com lag spikes (ver docstring do módulo).
        O while cobre lag spikes onde dois frames deveriam ter avançado.
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
    # UPDATE PRINCIPAL
    # ══════════════════════════════════════════════════════════════════

    def update(self, dt: float, plataformas: pygame.sprite.Group) -> None:
        """
        Executa um passo lógico completo para este frame.

        ORDEM IMUTÁVEL — cada numeração corresponde à seção da docstring
        do módulo. Reordenar qualquer passo introduz race conditions.

        Parâmetros
        ──────────
        dt          : delta time em segundos (Clock.tick / 1000)
        plataformas : grupo de sprites de colisão (world-space)
        """
        # ── PASSO 1: Decrementar timers ───────────────────────────────
        # Primeiro de todos — timers refletem o estado no INÍCIO do frame.
        self._decrementar_timers(dt)

        # ── PASSO 2: Input & intenções ────────────────────────────────
        self._ler_input()

        # ── PASSO 3: Escalada (controla vel_y, detecta desconexão) ────
        # Antes da gravidade para que a supressão funcione corretamente.
        self._processar_escalada()

        # ── PASSO 4: Gravidade (suprimida se escalando) ───────────────
        self._aplicar_gravidade(dt)

        # ── PASSO 5: Colisão eixo X ───────────────────────────────────
        self._colidir_eixo_x(plataformas, dt)

        # ── PASSO 6: Colisão eixo Y ───────────────────────────────────
        # no_chao é definido aqui — confiável apenas após este passo.
        self._colidir_eixo_y(plataformas, dt)

        # ── PASSO 7: Sincronização de floats ──────────────────────────
        # Rect pode ter sido corrigido nos eixos. Sincroniza floats ← rect.
        self.x = float(self.rect.x)
        self.y = float(self.rect.y)

        # Limites do mundo após sincronização
        self._aplicar_limites_mundo()

        # ── PASSO 8: Pulo (jump buffer × coyote) ─────────────────────
        # Timers já decrementados (passo 1) + no_chao atualizado (passo 6)
        # → única janela onde todos os valores são confiáveis.
        self._processar_pulo_buffer()

        # ── PASSO 9: Animação ─────────────────────────────────────────
        # Último: reflete o estado físico final pós-colisão do frame.
        self._atualizar_squash_stretch(dt)    # 9a: escala visual (S&S)
        self._atualizar_estado_animacao()     # 9b: row da spritesheet
        self._atualizar_frames(dt)            # 9c: frame_atual pelo cronômetro

    # ══════════════════════════════════════════════════════════════════
    # RENDERIZAÇÃO
    # ══════════════════════════════════════════════════════════════════

    def draw(
        self,
        surface:   pygame.Surface,
        rect_tela: pygame.Rect | None = None,
    ) -> None:
        """
        Desenha o frame correto da spritesheet na posição de tela.

        Efeito de piscar durante i-frames
        ──────────────────────────────────
        fase = int(pisca_timer / PISCA_FREQUENCIA)
        Fase par  (0, 2, 4…) → visível
        Fase ímpar (1, 3, 5…) → invisível (return sem blit)

        Determinístico: mesmo pisca_timer → mesmo resultado, sem toggle
        booleano sensível a lag spikes.

        Fallback de atlas
        ──────────────────
        Se estado_animacao não estiver no atlas (estado inesperado),
        usa "parado" como segurança — sem crash, sem blit inválido.

        Parâmetros
        ──────────
        surface   : Surface de destino (Game.screen)
        rect_tela : Rect em screen-space com offset de câmera + shake.
                    Se None, usa self.rect (útil em testes sem câmera).
        """
        # ── I-frames: efeito de piscar ────────────────────────────────
        if self.invulneravel_timer > 0.0:
            fase = int(self.pisca_timer / self.PISCA_FREQUENCIA)
            if fase % 2 == 1:
                return   # frame invisível — sai sem blit

        # ── Seleção do frame do atlas ──────────────────────────────────
        destino = rect_tela if rect_tela is not None else self.rect
        atlas   = self.animacoes_dir if self.virado_direita else self.animacoes_esq
        estado  = self.estado_animacao if self.estado_animacao in atlas else "parado"
        frames  = atlas[estado]

        if not frames:
            return

        frame_original = frames[self.frame_atual % len(frames)]

        # ── Squash & Stretch — escalonamento não-destrutivo ───────────
        sx = self.squash_stretch_x
        sy = self.squash_stretch_y
        escala_identica = (abs(sx - 1.0) < 0.005 and abs(sy - 1.0) < 0.005)

        if escala_identica:
            frame_para_blit = frame_original
            blit_x = destino.x
            blit_y = destino.y
        else:
            w_base   = destino.width
            h_base   = destino.height
            w_scaled = max(1, int(round(w_base * sx)))
            h_scaled = max(1, int(round(h_base * sy)))

            frame_para_blit = pygame.transform.scale(
                frame_original, (w_scaled, h_scaled)
            )
            blit_x = destino.centerx - w_scaled // 2
            blit_y = destino.bottom  - h_scaled

        # ── Damage Flash — silhueta sólida por máscara ────────────────
        #
        # Janela de flash: invulneravel_timer ainda está nos primeiros
        # DAMAGE_FLASH_DURACAO segundos.
        # Cálculo: invulneravel_timer > (INVULNERAVEL_DURATION - DAMAGE_FLASH_DURACAO)
        #
        # Exemplo com INVULNERAVEL_DURATION=1.5 e DAMAGE_FLASH_DURACAO=0.10:
        #   frame 0 (t=1.50): flash ativo   → 1.50 > 1.40 ✓
        #   frame 6 (t=1.10): flash ativo   → 1.10 > 1.40 ✗ → piscar assume
        #
        # Pipeline não-destrutivo:
        #   1. frame_para_blit (já escalado por S&S) → máscara dos pixels opacos
        #   2. surf_flash: Surface SRCALPHA do mesmo tamanho, toda transparente
        #   3. mask.to_surface() pinta os pixels opacos com DAMAGE_FLASH_COR
        #   4. surf_flash sobreposta ao blit normal (nunca modifica frame_para_blit)
        #
        # Diagrama de camadas (bottom → top na tela):
        #   [fundo / cenário]
        #   [sprite normal]       ← surface.blit(frame_para_blit, ...)
        #   [silhueta branca]     ← surface.blit(surf_flash, ...)   ← NOVO
        #
        em_flash = (
            self.invulneravel_timer > 0.0
            and self.invulneravel_timer
                > (self.INVULNERAVEL_DURATION - self.DAMAGE_FLASH_DURACAO)
        )

        # Blit do sprite (sempre — o flash é uma sobreposição, não substituição)
        surface.blit(frame_para_blit, (blit_x, blit_y))

        if em_flash:
            w_f = frame_para_blit.get_width()
            h_f = frame_para_blit.get_height()

            # Gera máscara a partir do frame atual (respeita transparência SRCALPHA)
            mascara  = pygame.mask.from_surface(frame_para_blit)

            # Surface de flash: transparente inicialmente
            surf_flash = pygame.Surface((w_f, h_f), pygame.SRCALPHA)
            surf_flash.fill((0, 0, 0, 0))   # limpa — sem artefatos de frame anterior

            # Pinta apenas os pixels opacos do sprite com a cor de flash
            # mask.to_surface() recebe:
            #   surface    → surface de destino (surf_flash)
            #   setcolor   → cor dos pixels dentro da máscara
            #   unsetcolor → cor dos pixels fora (transparente = (0,0,0,0))
            cor_flash = (*self.DAMAGE_FLASH_COR, 255)   # RGB → RGBA opaco
            mascara.to_surface(
                surf_flash,
                setcolor   = cor_flash,
                unsetcolor = (0, 0, 0, 0),
            )

            # Sobrepõe a silhueta sólida sobre o sprite já blitado
            surface.blit(surf_flash, (blit_x, blit_y))
