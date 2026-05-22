"""
player.py
═════════
Entidade principal do jogo — física, input, colisão e animação.

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

AABB = Axis-Aligned Bounding Box. Dois AABB colidem quando se
sobrepõem simultaneamente nos dois eixos.

O problema de resolver os dois eixos juntos
─────────────────────────────────────────────
Se movermos X e Y ao mesmo tempo antes de resolver a colisão, perdemos
a informação de QUAL eixo causou o contato:

    jogador se move → sobrepõe plataforma → "colidiu, mas de onde?"

Sem saber a direção, o engine pode empurrar o jogador na direção errada
— o bug clássico onde o personagem "gruda" nas paredes ao pular rente
a elas (wall-sticking).

A solução: separação de eixos
──────────────────────────────
    1. Move  só em X  →  detecta colisão  →  corrige X  (colisão lateral)
    2. Move  só em Y  →  detecta colisão  →  corrige Y  (pouso / teto)

Agora cada colisão tem direção inequívoca:
  Colisão no passo 1 → vem do lado   → empurra horizontalmente
  Colisão no passo 2 → vem de cima/baixo → empurra verticalmente

Prevenção de jitter (tremor)
─────────────────────────────
Jitter ocorre quando o solver oscila entre "dentro" e "fora" da
superfície a cada frame. A causa mais comum: após resolver a colisão,
o float acumulado (self.x / self.y) discorda do int do rect — e na
próxima frame o sprite "remerge" parcialmente na plataforma.

Solução aplicada aqui: após cada correção de rect, re-sincronizamos
IMEDIATAMENTE o float a partir do rect corrigido (e não o contrário):

    self.rect.bottom = plat.rect.top        # 1. rect corrigido (int)
    self.y = float(self.rect.y)             # 2. float sincronizado ← rect

Isso garante que a próxima frame começa a integração exatamente na
borda da plataforma, sem acúmulo de erro.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MÁQUINA DE ESTADOS DE ANIMAÇÃO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

A animação é gerenciada por três variáveis independentes:

    estado_animacao   →  QUAL sequência tocar  ("parado"|"correndo"|"pulando")
    frame_atual       →  QUAL frame da sequência exibir agora  (0…N-1)
    tempo_animacao    →  cronômetro que decide QUANDO avançar o frame

Camada 1 — _atualizar_estado_animacao()
  Lê as variáveis de física (no_chao, vel_x) e determina o estado.
  Ao trocar de estado, reinicia frame e cronômetro — o personagem
  nunca "entra no meio" de uma animação.

Camada 2 — _atualizar_frames(dt)
  Acumula dt no cronômetro. Quando ultrapassa _INTERVALO, avança
  frame_atual com módulo. Usa -= em vez de = 0 para preservar o
  "troco" de tempo — mantém o ritmo correto mesmo com lag spikes.

Camada 3 — draw() / _draw_*()
  Renderiza o estado atual. HOJE usa primitivas geométricas.
  FUTURO: basta trocar por:

      atlas = {"parado": [s0], "correndo": [s0,s1,s2,s3], "pulando": [s0]}
      img = atlas[self.estado_animacao][self.frame_atual]
      if not self.virado_direita:
          img = pygame.transform.flip(img, True, False)
      surface.blit(img, rect_tela)

  As camadas 1 e 2 não mudam nada — são independentes da renderização.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FLAG DE EVENTO DE UM FRAME (pulou)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Player não conhece o sistema de áudio. Quando o pulo é aplicado,
self.pulou = True sinaliza ao Game que "algo aconteceu neste frame".
O Game lê a flag, toca o som e a zera — sem acoplamento bidirecional.
Esse padrão é chamado de "One-Frame Event Flag" e é usado em engines
como Unity (Input.GetButtonDown retorna true por exatamente 1 frame).
"""

from __future__ import annotations

import pygame
import config


class Player:
    """
    Entidade controlada pelo jogador.

    Responsabilidades
    ─────────────────
    • Física:     gravidade, aceleração e integração com delta time
    • Input:      teclado (movimento, direção do sprite)
    • Colisão:    AABB por eixo separado com grupo de plataformas
    • Animação:   máquina de estados com cronômetro de frames
    • Renderização: procedural (pronta para receber spritesheets)

    Invariante central
    ───────────────────
    self.x / self.y  são os floats autoritativos da posição.
    self.rect        é derivado deles (int truncado).
    Após qualquer correção de rect pela colisão, os floats são
    re-sincronizados IMEDIATAMENTE para evitar jitter.
    """

    # ── Dimensões ─────────────────────────────────────────────────────
    WIDTH:  int = 40
    HEIGHT: int = 60

    # ── Física (lidas de config para facilitar tuning centralizado) ───
    SPEED:      float = config.PLAYER_SPEED
    GRAVITY:    float = config.PLAYER_GRAVITY
    FORCA_PULO: float = config.PLAYER_JUMP_FORCE

    # ── Animação ──────────────────────────────────────────────────────
    TOTAL_FRAMES: int   = 4      # frames no ciclo de corrida: 0 → 3
    FPS_CORRIDA:  float = 10.0   # trocas de frame por segundo
    _INTERVALO:   float = 1.0 / FPS_CORRIDA   # segundos por frame

    # ── Paleta procedural — uma cor por estado ─────────────────────────
    _COR_PARADO:   tuple = config.RED
    _COR_CORRENDO: tuple = (200, 60, 60)    # vermelho mais escuro — esforço
    _COR_PULANDO:  tuple = (255, 80, 80)    # vermelho claro — leveza

    # ──────────────────────────────────────────────────────────────────
    def __init__(self, x: float, y: float) -> None:
        """
        Parâmetros
        ──────────
        x, y : posição inicial do canto superior-esquerdo, em world-space.
        """
        # ── Posição (floats autoritativos) ────────────────────────────
        self.x: float = float(x)
        self.y: float = float(y)

        # ── Velocidade (px/s) ─────────────────────────────────────────
        self.vel_x: float = 0.0
        self.vel_y: float = 0.0

        # ── Estado de chão — True apenas quando rect.bottom == plataforma
        self.no_chao: bool = False

        # ── Rect derivado — único ponto de interação com o Pygame ─────
        self.rect: pygame.Rect = pygame.Rect(
            int(self.x), int(self.y), self.WIDTH, self.HEIGHT
        )

        # ── Direção do sprite ─────────────────────────────────────────
        # True = virado para a direita.
        # Com spritesheets: pygame.transform.flip(img, not virado_direita, False)
        self.virado_direita: bool = True

        # ── Máquina de estados de animação ────────────────────────────
        self.estado_animacao: str  = "parado"   # "parado"|"correndo"|"pulando"
        self.frame_atual:     int  = 0           # índice no ciclo de frames
        self.tempo_animacao:  float = 0.0        # cronômetro em segundos

        # ── Flag de evento de um frame (One-Frame Event Flag) ─────────
        # Levantada em handle_jump; lida e zerada pelo Game.
        # Desacopla o Player do sistema de áudio. Ver docstring do módulo.
        self.pulou: bool = False

    # ══════════════════════════════════════════════════════════════════
    # INPUT  (métodos públicos chamados pelo Game)
    # ══════════════════════════════════════════════════════════════════

    def handle_jump(self, event: pygame.event.Event) -> None:
        """
        Processa o evento de pulo — deve ser chamado dentro do loop de
        eventos do Game, uma vez por evento recebido.

        Por que KEYDOWN e não get_pressed()?
        ──────────────────────────────────────
        get_pressed() retorna True durante TODOS os frames em que a
        tecla está pressionada. Se o jogador segurar Espaço por 10 frames,
        a força de pulo seria aplicada 10 vezes — o personagem voaria.

        KEYDOWN dispara exatamente UMA VEZ por pressionamento — o impulso
        é aplicado uma única vez, como esperado fisicamente.
        """
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
                if self.no_chao:
                    self.vel_y   = self.FORCA_PULO
                    self.no_chao = False
                    self.pulou   = True    # sinaliza ao Game → tocar SFX

    # ══════════════════════════════════════════════════════════════════
    # FÍSICA  (métodos privados)
    # ══════════════════════════════════════════════════════════════════

    def _handle_input(self) -> None:
        """
        Lê o estado contínuo do teclado e define vel_x.

        Zerar vel_x antes de checar as teclas faz o personagem parar
        imediatamente ao soltar a tecla — sem inércia, conforme o
        comportamento esperado em plataformas arcade.
        """
        keys = pygame.key.get_pressed()
        self.vel_x = 0.0

        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.vel_x          = -self.SPEED
            self.virado_direita = False

        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.vel_x          = +self.SPEED
            self.virado_direita = True

    def _apply_gravity(self, dt: float) -> None:
        """
        Acumula gravidade em vel_y (positivo = para baixo).

        Não há terminal velocity aqui intencionalmente — a gravidade
        moderada (1 200 px/s²) e o WORLD_HEIGHT finito fazem com que
        a velocidade de queda máxima seja naturalmente limitada pelo
        tempo de queda disponível no nível.
        """
        self.vel_y += self.GRAVITY * dt

    def _resolve_collisions(self, plataformas: pygame.sprite.Group, dt: float) -> None:
        """
        Move o jogador e resolve colisões com o grupo de plataformas,
        processando cada eixo de forma completamente independente.

        Veja a docstring do módulo para a explicação completa do
        algoritmo AABB por eixo separado e da prevenção de jitter.

        Parâmetros
        ──────────
        plataformas : grupo de sprites com atributo .rect (world-space)
        dt          : delta time em segundos
        """
        # ── EIXO X ────────────────────────────────────────────────────
        # 1. Avança apenas em X
        self.x     += self.vel_x * dt
        self.rect.x = int(self.x)

        # 2. Detecta e resolve colisões laterais
        for plat in pygame.sprite.spritecollide(self, plataformas, False):
            if self.vel_x > 0:
                # Movendo para a direita → encosta a face direita no lado esquerdo da plataforma
                self.rect.right = plat.rect.left
            elif self.vel_x < 0:
                # Movendo para a esquerda → encosta a face esquerda no lado direito da plataforma
                self.rect.left  = plat.rect.right

            # Re-sincroniza float ← rect corrigido  (anti-jitter)
            self.x     = float(self.rect.x)
            self.vel_x = 0.0   # para o movimento horizontal ao colidir

        # ── EIXO Y ────────────────────────────────────────────────────
        # 3. Avança apenas em Y
        self.y     += self.vel_y * dt
        self.rect.y = int(self.y)

        # 4. Reseta no_chao antes de verificar — ele só é True se
        #    uma colisão vertical acontecer NESTE frame.
        self.no_chao = False

        # 5. Detecta e resolve colisões verticais
        for plat in pygame.sprite.spritecollide(self, plataformas, False):
            if self.vel_y > 0:
                # Caindo → pousa no topo da plataforma
                self.rect.bottom = plat.rect.top
                self.no_chao     = True
            elif self.vel_y < 0:
                # Subindo → bate a cabeça no fundo da plataforma
                self.rect.top    = plat.rect.bottom

            # Re-sincroniza float ← rect corrigido  (anti-jitter)
            self.y     = float(self.rect.y)
            self.vel_y = 0.0   # zera vel_y em ambos os casos (pouso E teto)

        # ── LIMITES DO MUNDO ──────────────────────────────────────────
        # Impede que o jogador saia pelas bordas esquerda e direita.
        # Não há limite vertical superior — o jogador pode sair pelo topo;
        # não há limite inferior — cair fora da tela pode ser tratado
        # como morte em Game.update() verificando player.rect.top > SCREEN_HEIGHT.
        self.x      = max(0.0, min(self.x, float(config.WORLD_WIDTH - self.WIDTH)))
        self.rect.x = int(self.x)

    # ══════════════════════════════════════════════════════════════════
    # ANIMAÇÃO  (métodos privados)
    # ══════════════════════════════════════════════════════════════════

    def _atualizar_estado_animacao(self) -> None:
        """
        Determina qual sequência de animação deve estar ativa,
        baseado nas variáveis de física do frame atual.

        Ordem de prioridade (a ordem das condições importa):
          1. No ar           → "pulando"   domina qualquer vel_x
          2. No chão + mov.  → "correndo"
          3. No chão + parado → "parado"

        Transição de estado
        ────────────────────
        Ao detectar uma mudança de estado, reinicia frame_atual e
        tempo_animacao. Isso evita que o personagem "entre no meio"
        de uma animação — cada sequência sempre começa do frame 0.

        Com spritesheets: este método determina qual row/strip do
        atlas de sprites será indexada por frame_atual.
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

        Só anima no estado "correndo" — parado e pulando ficam no
        frame 0 (pose neutra).

        Por que subtrair _INTERVALO em vez de zerar o cronômetro?
        ────────────────────────────────────────────────────────────
        Se um frame de lag demorar 0.18 s e _INTERVALO = 0.10 s, a
        diferença de 0.08 s seria perdida ao zerar o cronômetro —
        o ritmo da animação "escorregaria" imperceptivelmente.
        Subtraindo, o excesso (0.08 s) é carregado para o próximo
        intervalo, mantendo o timing preciso mesmo sob variação de FPS.

        O while (em vez de if) cobre lag spikes extremos onde dois ou
        mais frames de animação deveriam ter avançado no mesmo update.
        """
        if self.estado_animacao == "correndo":
            self.tempo_animacao += dt
            while self.tempo_animacao >= self._INTERVALO:
                self.tempo_animacao -= self._INTERVALO
                self.frame_atual = (self.frame_atual + 1) % self.TOTAL_FRAMES
        else:
            # Estado estático: reinicia para pose neutra
            self.frame_atual    = 0
            self.tempo_animacao = 0.0

    # ══════════════════════════════════════════════════════════════════
    # UPDATE PRINCIPAL  (método público)
    # ══════════════════════════════════════════════════════════════════

    def update(self, dt: float, plataformas: pygame.sprite.Group) -> None:
        """
        Executa um passo lógico completo para este frame.

        Ordem de operações — a sequência não pode ser alterada:
        ──────────────────────────────────────────────────────
        1. Input          define vel_x baseado nas teclas pressionadas
        2. Gravidade      acumula vel_y (independente do input)
        3. Colisões       move e corrige posição; atualiza no_chao
        4. Sincronização  re-sincroniza floats ← rect final corrigido
        5. Estado anim.   lê no_chao e vel_x para decidir a sequência
        6. Frames anim.   avança o cronômetro e o índice de frame

        Os passos 5 e 6 devem ser os últimos: dependem do estado
        físico final do frame, não do estado antes das correções.

        Parâmetros
        ──────────
        dt          : delta time em segundos (de Clock.tick / 1000)
        plataformas : grupo de sprites de colisão (world-space)
        """
        self._handle_input()
        self._apply_gravity(dt)
        self._resolve_collisions(plataformas, dt)

        # Re-sincronização final: garante que self.x/y refletem
        # o rect após todas as correções de colisão e limites de mundo.
        self.x = float(self.rect.x)
        self.y = float(self.rect.y)

        # Animação — lida depois da física para ler o estado correto
        self._atualizar_estado_animacao()
        self._atualizar_frames(dt)

    # ══════════════════════════════════════════════════════════════════
    # RENDERIZAÇÃO PROCEDURAL  (método público + helpers privados)
    # ══════════════════════════════════════════════════════════════════
    #
    # Estrutura de substituição por spritesheets (zero mudança na lógica):
    #
    #   atlas = {
    #       "parado":   [surf_idle_0],
    #       "correndo": [surf_run_0, surf_run_1, surf_run_2, surf_run_3],
    #       "pulando":  [surf_jump_0],
    #   }
    #   img = atlas[self.estado_animacao][self.frame_atual]
    #   if not self.virado_direita:
    #       img = pygame.transform.flip(img, True, False)
    #   surface.blit(img, rect_tela)
    #
    # self.virado_direita já está sendo mantido por _handle_input.
    # ══════════════════════════════════════════════════════════════════

    def draw(
        self,
        surface: pygame.Surface,
        rect_tela: pygame.Rect | None = None,
    ) -> None:
        """
        Renderiza o jogador no estado de animação atual.

        Parâmetros
        ──────────
        surface   : Surface de destino (normalmente Game.screen)
        rect_tela : Rect em screen-space (com offset de câmera aplicado).
                    Se None, usa self.rect diretamente — útil em testes
                    unitários ou quando não há câmera.
        """
        r = rect_tela if rect_tela is not None else self.rect

        if self.estado_animacao == "parado":
            self._draw_parado(surface, r)
        elif self.estado_animacao == "correndo":
            self._draw_correndo(surface, r)
        elif self.estado_animacao == "pulando":
            self._draw_pulando(surface, r)

    # ------------------------------------------------------------------
    # Helpers de renderização — um por estado de animação
    # ------------------------------------------------------------------

    def _draw_olhos(self, surface: pygame.Surface, r: pygame.Rect) -> None:
        """
        Olhos brancos com pupila preta direcional.

        Extraído como helper porque todos os três estados de animação
        compartilham exatamente o mesmo visual de olhos — elimina
        duplicação e centraliza qualquer ajuste futuro.

        A pupila é deslocada +2px (dir.) ou -2px (esq.) para indicar
        a direção que o personagem está olhando, usando Rect.move()
        e Rect.inflate() para ajuste não-destrutivo.
        """
        ow, oh = 7, 7            # dimensões de cada olho
        oy     = r.top + 10      # Y dos olhos: terço superior do corpo
        desl   = 2 if self.virado_direita else -2   # deslocamento da pupila

        olho_esq = pygame.Rect(r.left  + 5,  oy, ow, oh)
        olho_dir = pygame.Rect(r.right - 14, oy, ow, oh)

        for olho in (olho_esq, olho_dir):
            pygame.draw.rect(surface, config.WHITE, olho)
            # inflate(-3, -3) reduz o rect em 3px em cada dimensão → pupila menor
            pygame.draw.rect(surface, config.BLACK, olho.move(desl, 1).inflate(-3, -3))

    def _draw_parado(self, surface: pygame.Surface, r: pygame.Rect) -> None:
        """
        Pose neutra: corpo vermelho sólido.
        frame_atual é sempre 0 neste estado — nenhum ciclo de frames.
        """
        pygame.draw.rect(surface, self._COR_PARADO, r)
        self._draw_olhos(surface, r)

    def _draw_correndo(self, surface: pygame.Surface, r: pygame.Rect) -> None:
        """
        Ciclo de corrida: 4 frames com pernas alternadas.

        As pernas são linhas verticais saindo da base do corpo.
        Cada frame desloca as pernas em Y de forma espelhada:

            frame 0 → perna esq. +8px  perna dir. -8px  (passada A)
            frame 1 → ambas  0px                         (neutro)
            frame 2 → perna esq. -8px  perna dir. +8px  (passada B)
            frame 3 → ambas  0px                         (neutro)

        Este ciclo de 4 frames (A–neutro–B–neutro) é o padrão de ciclo
        de caminhada usado em spritesheets de plataformas 2D clássicos.
        """
        pygame.draw.rect(surface, self._COR_CORRENDO, r)
        self._draw_olhos(surface, r)

        # Tabela de offsets verticais: frame → (delta_esq, delta_dir)
        _OFFSETS_PERNAS: dict[int, tuple[int, int]] = {
            0: ( 8, -8),   # passada A
            1: ( 0,  0),   # neutro
            2: (-8,  8),   # passada B
            3: ( 0,  0),   # neutro
        }
        oe, od  = _OFFSETS_PERNAS[self.frame_atual]
        cx      = r.centerx
        base_y  = r.bottom
        perna_h = 10       # comprimento base da perna em pixels

        pygame.draw.line(
            surface, config.BLACK,
            (cx - 8, base_y),
            (cx - 8, base_y + perna_h + oe), 3,
        )
        pygame.draw.line(
            surface, config.BLACK,
            (cx + 8, base_y),
            (cx + 8, base_y + perna_h + od), 3,
        )

    def _draw_pulando(self, surface: pygame.Surface, r: pygame.Rect) -> None:
        """
        Pose de pulo: corpo claro + braços abertos + pernas dinâmicas.

        As pernas mudam de posição baseadas em vel_y (não em frame_atual):
          vel_y < 0  →  subindo:  pernas dobradas para CIMA  (recolhidas)
          vel_y >= 0 →  caindo:   pernas abertas para BAIXO  (estendidas)

        Esse detalhe diferencia visualmente a fase de subida da descida
        sem custo adicional de animação — um truque comum em sprites 2D.
        """
        pygame.draw.rect(surface, self._COR_PULANDO, r)
        self._draw_olhos(surface, r)

        cx = r.centerx
        cy = r.centery

        # Braços: linha horizontal atravessando o corpo
        pygame.draw.line(
            surface, config.BLACK,
            (r.left  - 6, cy - 5),
            (r.right + 6, cy - 5), 3,
        )

        # Pernas: ângulo muda com a fase do pulo
        if self.vel_y < 0:
            # Subindo — pernas em V invertido (recolhidas)
            extremos = [
                ((cx - 8, r.bottom), (cx - 14, r.bottom - 10)),
                ((cx + 8, r.bottom), (cx + 14, r.bottom - 10)),
            ]
        else:
            # Caindo — pernas em V (abertas)
            extremos = [
                ((cx - 8, r.bottom), (cx - 14, r.bottom + 12)),
                ((cx + 8, r.bottom), (cx + 14, r.bottom + 12)),
            ]

        for inicio, fim in extremos:
            pygame.draw.line(surface, config.BLACK, inicio, fim, 3)
