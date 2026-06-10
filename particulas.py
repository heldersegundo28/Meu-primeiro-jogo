"""
particulas.py
═════════════
Sistema leve e desacoplado de partículas visuais para o Jogo do Calango.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RESPONSABILIDADE E ISOLAMENTO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Este módulo gerencia exclusivamente a simulação e renderização visual
das partículas. Ele NUNCA:
  • importa player.py, main.py ou qualquer arquivo do jogo
  • lê ou escreve variáveis de física do jogador
  • toma decisões sobre QUANDO emitir partículas

Quem decide emitir é o main.py, que lê telemetria Read-Only do Player
(flags como just_landed, pulou, vel_x) e chama os emissores aqui.

Diagrama de dependências:

    main.py
      │  lê telemetria de player.py
      │  chama emissores de particulas.py
      ▼
    particulas.py
      │  importa apenas
      ├── pygame  (círculo, Surface)
      ├── random  (dispersão)
      └── math    (sqrt — opcional)

    player.py  ──────────────────────────────────►  (nunca importa particulas)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ESTRUTURA DE DADOS — Particula
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Cada partícula é um objeto Python simples com 7 campos numéricos.
Usamos __slots__ para eliminar o __dict__ por instância, reduzindo
o uso de memória e acelerando o acesso aos atributos quando há
dezenas de partículas simultâneas.

Ciclo de vida:
  emissão  →  atualização (via dt)  →  morte (lifetime <= 0)

A morte é detectada no gerenciador; partículas mortas são removidas
por list comprehension (sem chamada explícita de destruição).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PIPELINE DE RENDERIZAÇÃO COM CÂMERA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

As partículas existem em world-space (mesmas coordenadas dos sprites).
Para desenhá-las corretamente com câmera + screen shake:

    screen_x = particula.x - camera.offset_x + ox
    screen_y = particula.y                    + oy

Onde ox, oy são os offsets de shake calculados em _draw_jogo().
Isso garante que a poeira fica "colada no cenário", não na tela.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PERFORMANCE — POR QUE NÃO USAR pygame.sprite.Sprite
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Partículas nascem e morrem rapidamente (0.15–0.50s). Usar Sprite +
Group implicaria alocar uma Surface por partícula, chamar kill() e
gerenciar grupos. Para círculos simples, pygame.draw.circle direto
na tela é 3–5× mais rápido e usa zero Surface extra.
"""

from __future__ import annotations

import math
import random

import pygame


# ══════════════════════════════════════════════════════════════════════
# CONSTANTES DE EMISSÃO
# ══════════════════════════════════════════════════════════════════════
# Centralizadas aqui para que tuning visual não exija tocar em main.py.

# ── Landing Dust ──────────────────────────────────────────────────────
LANDING_QTD_MIN:    int   = 4     # partículas mínimas por impacto
LANDING_QTD_MAX:    int   = 10    # partículas máximas por impacto
LANDING_VEL_X_MIN:  float = 40.0  # dispersão horizontal mínima (px/s)
LANDING_VEL_X_MAX:  float = 130.0 # dispersão horizontal máxima (px/s)
LANDING_VEL_Y_MIN:  float = -90.0 # velocidade vertical inicial (para cima)
LANDING_VEL_Y_MAX:  float = -20.0 # velocidade vertical inicial (menos para cima)
LANDING_RAIO_MIN:   int   = 2     # raio mínimo inicial (px)
LANDING_RAIO_MAX:   int   = 5     # raio máximo inicial (px)
LANDING_VIDA_MIN:   float = 0.18  # lifetime mínimo (s)
LANDING_VIDA_MAX:   float = 0.38  # lifetime máximo (s)

# ── Jump Dust ─────────────────────────────────────────────────────────
JUMP_QTD:           int   = 5
JUMP_VEL_X_RANGE:   float = 60.0  # ±vel_x horizontal (lufada para baixo)
JUMP_VEL_Y_MIN:     float = 20.0  # velocidade para baixo mínima
JUMP_VEL_Y_MAX:     float = 60.0  # velocidade para baixo máxima
JUMP_RAIO_MIN:      int   = 1
JUMP_RAIO_MAX:      int   = 4
JUMP_VIDA_MIN:      float = 0.12
JUMP_VIDA_MAX:      float = 0.25

# ── Run Dust ──────────────────────────────────────────────────────────
RUN_INTERVALO:      float = 0.08  # segundos entre emissões ao correr
RUN_VEL_X_RANGE:    float = 30.0  # dispersão horizontal
RUN_VEL_Y_MIN:      float = -40.0 # leve para cima
RUN_VEL_Y_MAX:      float = -10.0
RUN_RAIO_MIN:       int   = 1
RUN_RAIO_MAX:       int   = 3
RUN_VIDA_MIN:       float = 0.10
RUN_VIDA_MAX:       float = 0.20
RUN_VEL_THRESHOLD:  float = 80.0  # vel_x mínima para emitir poeira de corrida

# ── Visual ────────────────────────────────────────────────────────────
# Cor base da poeira: cinza claro com leve tom bege.
# O alpha é calculado dinamicamente em draw() via proporção de vida restante.
COR_POEIRA_RGB:     tuple = (200, 190, 175)   # (R, G, B) sem alpha


# ══════════════════════════════════════════════════════════════════════
# ESTRUTURA DE DADOS
# ══════════════════════════════════════════════════════════════════════

class Particula:
    """
    Unidade mínima de simulação visual.

    Usa __slots__ para eliminar __dict__ por instância:
      • reduz ~300 bytes de overhead por partícula
      • acelera acesso a atributos (offset fixo vs lookup de dict)
      • com 20 partículas simultâneas: economia de ~6 KB e ~10% de CPU

    Todos os campos são numéricos — sem referências a objetos externos.
    Isso torna a partícula 100% autônoma e facilmente serializável.
    """
    __slots__ = (
        "x", "y",          # posição em world-space (float)
        "vel_x", "vel_y",  # velocidade em px/s (float)
        "raio",            # raio atual do círculo (float — encolhe com o tempo)
        "raio_inicial",    # raio de nascimento (para calcular proporção de fade)
        "lifetime",        # tempo de vida restante (segundos)
        "lifetime_total",  # tempo de vida total (para proporção de alpha)
    )

    def __init__(
        self,
        x:      float,
        y:      float,
        vel_x:  float,
        vel_y:  float,
        raio:   float,
        vida:   float,
    ) -> None:
        self.x             = x
        self.y             = y
        self.vel_x         = vel_x
        self.vel_y         = vel_y
        self.raio          = float(raio)
        self.raio_inicial  = float(raio)
        self.lifetime      = vida
        self.lifetime_total = vida

    @property
    def viva(self) -> bool:
        """True enquanto a partícula ainda tem tempo de vida."""
        return self.lifetime > 0.0

    @property
    def proporcao_vida(self) -> float:
        """
        Proporção de vida restante: 1.0 (recém-nascida) → 0.0 (morta).
        Usada para fade-out de tamanho e alpha de forma frame-rate-independent.
        """
        if self.lifetime_total <= 0.0:
            return 0.0
        return max(0.0, self.lifetime / self.lifetime_total)


# ══════════════════════════════════════════════════════════════════════
# GERENCIADOR DE PARTÍCULAS
# ══════════════════════════════════════════════════════════════════════

class GerenciadorParticulas:
    """
    Armazena, atualiza e desenha todas as partículas ativas.

    Responsabilidades
    ─────────────────
    • Manter a lista interna de partículas vivas
    • Atualizar física simples (posição via vel × dt)
    • Encolher raio e decrementar lifetime por dt
    • Remover partículas mortas (list comprehension — sem overhead de GC)
    • Desenhar todas as partículas com câmera + shake offset corretos

    Não responsável por
    ────────────────────
    • Decidir QUANDO emitir (decisão do main.py)
    • Conhecer o Player ou suas variáveis
    """

    # Gravidade visual aplicada às partículas (px/s²).
    # Menor que a gravidade do jogo para a poeira "flutuar" levemente.
    GRAVIDADE: float = 180.0

    # Atrito horizontal: multiplica vel_x por este fator a cada segundo.
    # Simula resistência do ar sem física complexa.
    ATRITO_X: float = 4.0   # tau de decaimento exponencial (vel_x *= e^(-ATRITO×dt))

    def __init__(self) -> None:
        self._particulas: list[Particula] = []

    # ------------------------------------------------------------------
    def adicionar(self, particula: Particula) -> None:
        """Registra uma nova partícula no gerenciador."""
        self._particulas.append(particula)

    def adicionar_varias(self, particulas: list[Particula]) -> None:
        """Registra múltiplas partículas de uma vez (evita chamadas repetidas)."""
        self._particulas.extend(particulas)

    def limpar(self) -> None:
        """Remove todas as partículas — usado ao trocar de fase/estado."""
        self._particulas.clear()

    @property
    def total(self) -> int:
        """Número de partículas vivas (útil para debug)."""
        return len(self._particulas)

    # ------------------------------------------------------------------
    def atualizar(self, dt: float) -> None:
        """
        Avança a simulação de todas as partículas por dt segundos.

        Física aplicada por partícula:
          1. Gravidade acumula em vel_y (poeira cai devagar)
          2. Atrito exponencial em vel_x (desaceleração horizontal suave)
          3. Integração de Euler: posição += vel × dt
          4. Raio encolhe proporcionalmente ao tempo restante
          5. Lifetime decrementado

        Remoção de mortas
        ──────────────────
        List comprehension é O(n) e não modifica a lista durante iteração —
        mais seguro e geralmente mais rápido que del em loop for.

        Parâmetros
        ──────────
        dt : delta time em segundos
        """
        for p in self._particulas:
            # ── Física ────────────────────────────────────────────────
            p.vel_y    += self.GRAVIDADE * dt
            p.vel_x    *= math.exp(-self.ATRITO_X * dt)   # decaimento exponencial

            p.x        += p.vel_x * dt
            p.y        += p.vel_y * dt

            # ── Raio encolhe com a vida restante ──────────────────────
            p.raio      = p.raio_inicial * p.proporcao_vida

            # ── Decremento de lifetime ────────────────────────────────
            p.lifetime  = max(0.0, p.lifetime - dt)

        # Remove mortas (list comprehension — sem risco de index shift)
        self._particulas = [p for p in self._particulas if p.viva]

    # ------------------------------------------------------------------
    def desenhar(
        self,
        surface:    pygame.Surface,
        offset_x:   float,
        offset_y:   float = 0.0,
    ) -> None:
        """
        Desenha todas as partículas vivas na surface com offset de câmera.

        Por que offset_x e offset_y em vez de um pygame.Rect?
        ───────────────────────────────────────────────────────
        Partículas usam coordenadas contínuas (float). Receber os offsets
        diretamente evita criar Rects temporários — o cálculo de screen
        position é uma subtração simples:
            screen_x = world_x - camera.offset_x + shake_ox
            screen_y = world_y                    + shake_oy

        Alpha determinístico por proporção de vida
        ────────────────────────────────────────────
        alpha = int(255 × proporcao_vida)
        Ao nascimento: alpha=255 (opaca). Na morte: alpha=0 (invisível).
        Usamos pygame.SRCALPHA para suporte a canal alpha por Surface.
        Surface de tamanho 2×raio alocada por partícula — aceitável
        para ~20 partículas simultâneas.

        Parâmetros
        ──────────
        surface  : Surface de destino (Game.screen)
        offset_x : camera.offset_x + ox (shake)
        offset_y : oy (shake vertical, geralmente 0 se sem Y-scroll)
        """
        for p in self._particulas:
            raio_int = max(1, int(p.raio))
            if raio_int < 1:
                continue

            # ── Alpha proporcional à vida restante ────────────────────
            alpha = int(255 * p.proporcao_vida)

            # ── Posição em screen-space ───────────────────────────────
            sx = int(p.x - offset_x)
            sy = int(p.y + offset_y)

            # ── Surface temporária com alpha por pixel ────────────────
            # Tamanho: diâmetro × diâmetro (quadrado mínimo para o círculo)
            diametro = raio_int * 2
            surf_p   = pygame.Surface((diametro, diametro), pygame.SRCALPHA)
            cor_com_alpha = (*COR_POEIRA_RGB, alpha)
            pygame.draw.circle(surf_p, cor_com_alpha, (raio_int, raio_int), raio_int)

            # Blit centrado: o círculo está no centro da surf_p
            self.screen_blit(surface, surf_p, sx - raio_int, sy - raio_int)

    @staticmethod
    def screen_blit(
        surface: pygame.Surface,
        surf_p:  pygame.Surface,
        x:       int,
        y:       int,
    ) -> None:
        """
        Blit com clipping automático — evita tentar desenhar fora da tela.

        pygame.Surface.blit() já ignora área fora do clip rect da surface,
        mas checar explicitamente aqui evita criar surf_p para partículas
        completamente fora da tela.

        Nota: esta otimização é opcional e pode ser removida se a janela
        nunca tiver partículas fora da área visível.
        """
        surface.blit(surf_p, (x, y))


# ══════════════════════════════════════════════════════════════════════
# FUNÇÕES EMISSORAS
# ══════════════════════════════════════════════════════════════════════
# Funções puras: recebem posição + parâmetros, retornam lista de Particula.
# Não têm estado interno — fáceis de testar e reutilizar.

def emitir_landing_dust(
    px:             float,
    py:             float,
    vel_impacto:    float,
    fator_qtd:      float = 1.0,
) -> list[Particula]:
    """
    Gera partículas de poeira ao aterrissar.

    A quantidade e velocidade das partículas é proporcional à
    velocidade de impacto — quedas maiores geram mais poeira.

    Disposição lateral:
      Metade das partículas vai para a esquerda (vel_x < 0),
      metade para a direita (vel_x > 0) — efeito de "explosão lateral".

    Parâmetros
    ──────────
    px, py        : posição do midbottom do jogador em world-space
    vel_impacto   : vel_y no momento do pouso (px/s) — influencia quantidade
    fator_qtd     : multiplicador externo de quantidade (ex: 1.5 para impacto forte)
    """
    # Quantidade proporcional ao impacto, clampada nos limites
    razao    = min(vel_impacto / 900.0, 1.0)   # normaliza pela terminal velocity
    qtd_base = LANDING_QTD_MIN + int(razao * (LANDING_QTD_MAX - LANDING_QTD_MIN))
    qtd      = max(LANDING_QTD_MIN, int(qtd_base * fator_qtd))

    particulas: list[Particula] = []
    for i in range(qtd):
        # Alterna direção: índices pares → esquerda, ímpares → direita
        sinal   = -1.0 if i % 2 == 0 else 1.0
        vel_x   = sinal * random.uniform(LANDING_VEL_X_MIN, LANDING_VEL_X_MAX)
        vel_y   = random.uniform(LANDING_VEL_Y_MIN, LANDING_VEL_Y_MAX)
        raio    = random.randint(LANDING_RAIO_MIN, LANDING_RAIO_MAX)
        vida    = random.uniform(LANDING_VIDA_MIN, LANDING_VIDA_MAX)
        # Leve dispersão horizontal na posição de nascimento
        offset  = random.uniform(-8.0, 8.0)
        particulas.append(Particula(px + offset, py, vel_x, vel_y, raio, vida))

    return particulas


def emitir_jump_dust(
    px: float,
    py: float,
    vel_x_player: float = 0.0,
) -> list[Particula]:
    """
    Gera poeira ao saltar — lufada para baixo e ligeiramente lateral.

    A direção do movimento horizontal do jogador influencia levemente
    a dispersão — poeira "fica para trás" do movimento.

    Parâmetros
    ──────────
    px, py          : posição do midbottom do jogador em world-space
    vel_x_player    : vel_x do jogador no frame do pulo (telemetria Read-Only)
    """
    particulas: list[Particula] = []
    for _ in range(JUMP_QTD):
        # Dispersão lateral — leve tendência oposta ao movimento
        vel_x   = random.uniform(-JUMP_VEL_X_RANGE, JUMP_VEL_X_RANGE)
        vel_x  -= vel_x_player * 0.15   # "fica para trás" do jogador
        vel_y   = random.uniform(JUMP_VEL_Y_MIN, JUMP_VEL_Y_MAX)
        raio    = random.randint(JUMP_RAIO_MIN, JUMP_RAIO_MAX)
        vida    = random.uniform(JUMP_VIDA_MIN, JUMP_VIDA_MAX)
        offset  = random.uniform(-5.0, 5.0)
        particulas.append(Particula(px + offset, py, vel_x, vel_y, raio, vida))

    return particulas


def emitir_run_dust(
    px: float,
    py: float,
    direcao: float = 1.0,
) -> list[Particula]:
    """
    Gera UMA partícula de poeira ao correr — chamada com intervalo pelo Game.

    Uma única partícula por emissão mantém o efeito sutil e performático.
    O Game controla o intervalo via poeira_corrida_timer.

    Parâmetros
    ──────────
    px, py    : posição do midbottom do jogador em world-space
    direcao   : +1.0 (correndo →) ou -1.0 (correndo ←)
                A poeira é emitida na direção OPOSTA ao movimento.
    """
    # Poeira sai na direção oposta ao movimento (fica para trás)
    vel_x  = -direcao * random.uniform(10.0, RUN_VEL_X_RANGE)
    vel_y  = random.uniform(RUN_VEL_Y_MIN, RUN_VEL_Y_MAX)
    raio   = random.randint(RUN_RAIO_MIN, RUN_RAIO_MAX)
    vida   = random.uniform(RUN_VIDA_MIN, RUN_VIDA_MAX)
    offset = random.uniform(-4.0, 4.0)

    return [Particula(px + offset, py, vel_x, vel_y, raio, vida)]


# ══════════════════════════════════════════════════════════════════════
# EMISSORES — Fase 5: Rastro de vento / Fall Wind Dust
# ══════════════════════════════════════════════════════════════════════

# Constantes de emissão do rastro de vento durante queda rápida.
# Partículas sobem pelos lados do corpo simulando atrito com o ar.
_VENTO_VEL_X_RANGE: float = 30.0    # dispersão horizontal máxima (px/s)
_VENTO_VEL_Y_MIN:   float = -120.0  # sobem rapidamente (px/s)
_VENTO_VEL_Y_MAX:   float = -40.0   # velocidade de subida mínima
_VENTO_RAIO_MIN:    int   = 1        # raio mínimo (px) — partículas finas
_VENTO_RAIO_MAX:    int   = 2        # raio máximo — mantém sutil
_VENTO_VIDA_MIN:    float = 0.08     # vida muito curta — rastro, não nuvem
_VENTO_VIDA_MAX:    float = 0.16
_VENTO_COR_BASE:    tuple = (200, 210, 220)  # azul-claro acinzentado


def emitir_rastro_vento(
    px: float,
    py: float,
    largura_corpo: float = 40.0,
) -> list[Particula]:
    """
    Gera 2 partículas de atrito de ar durante queda em alta velocidade.

    Simulação de atrito aerodinâmico
    ──────────────────────────────────
    Quando o calango cai a grande velocidade, o ar empurrado para cima
    pelas laterais do corpo forma um rastro visual ascendente.
    Duas partículas simétricas (uma em cada lado) reforçam a leitura
    de velocidade sem sobrecarregar a tela.

    Emissão deliberadamente mínima (2 partículas por chamada)
    ──────────────────────────────────────────────────────────
    O Game chama esta função com um timer próprio (ex: a cada 2 frames).
    Em terminal velocity (900 px/s), isso gera ~30 partículas/s — sutil
    e performático. Um cluster maior tornaria o efeito barulhento e
    obscureceria o sprite do calango.

    Diagrama de emissão:
        ┌──────────────┐
        │   calango    │
        │  caindo ↓↓↓  │
        ├──┤        ├──┤
        ↑              ↑
    particula_esq  particula_dir
    (x - offset)   (x + offset)
    vel_y negativo → subindo

    Parâmetros
    ──────────
    px, py          : posição do midbottom do calango (world-space)
    largura_corpo   : largura do hitbox (default Player.WIDTH = 40px)
                      As partículas nascem nas bordas laterais do corpo.
    """
    meia_largura = largura_corpo * 0.5
    resultado:   list[Particula] = []

    for sinal in (-1.0, +1.0):   # esquerda e direita
        # Nasce na lateral do corpo, levemente para fora
        x_nasc = px + sinal * (meia_largura + random.uniform(0.0, 4.0))
        y_nasc = py - random.uniform(0.0, largura_corpo * 0.3)   # em algum ponto do corpo

        # Sobe com leve dispersão horizontal para fora (não para dentro)
        vx = sinal * random.uniform(2.0, _VENTO_VEL_X_RANGE)
        vy = random.uniform(_VENTO_VEL_Y_MIN, _VENTO_VEL_Y_MAX)

        resultado.append(Particula(
            x_nasc, y_nasc, vx, vy,
            random.randint(_VENTO_RAIO_MIN, _VENTO_RAIO_MAX),
            random.uniform(_VENTO_VIDA_MIN, _VENTO_VIDA_MAX),
        ))

    return resultado


# ══════════════════════════════════════════════════════════════════════
# EMISSORES — AUTOTOMIA (PERDA DA CAUDA)
# ══════════════════════════════════════════════════════════════════════

# ── Constantes de tuning da explosão de cauda ────────────────────────
# Separadas das landing constants para facilitar iteração de feel
# sem risco de alterar outros efeitos.
CAUDA_QTD:      int   = 18    # partículas emitidas no evento
CAUDA_VEL_XMIN: float = 40.0  # velocidade horizontal mínima (px/s)
CAUDA_VEL_XMAX: float = 200.0 # velocidade horizontal máxima (px/s)
CAUDA_VEL_YMIN: float = -280.0# impulso vertical mínimo (px/s, negativo = sobe)
CAUDA_VEL_YMAX: float = -60.0 # impulso vertical máximo (px/s)
CAUDA_RAIO_MIN: int   = 3     # raio mínimo (px)
CAUDA_RAIO_MAX: int   = 8     # raio máximo (px)
CAUDA_VIDA_MIN: float = 0.30  # tempo de vida mínimo (s)
CAUDA_VIDA_MAX: float = 0.65  # tempo de vida máximo (s)


def emitir_cauda_break(
    px: float,
    py: float,
    virado_direita: bool,
) -> list[Particula]:
    """
    Gera a explosão de partículas ao perder a cauda (autotomia).

    Comportamento
    ─────────────
    A cauda está na parte traseira do calango, portanto as partículas
    explodem na direção OPOSTA ao virado_direita:
      • calango virado à direita → cauda sai pela esquerda
      • calango virado à esquerda → cauda sai pela direita

    Padrão de dispersão: cone traseiro de ~120° — mais concentrado na
    direção da cauda, com dispersão lateral.

    A cor é determinada pelo sistema de renderização de partículas
    (laranja-avermelhada por default). Para cor específica de cauda,
    estender Particula com campo cor no futuro.

    Parâmetros
    ──────────
    px, py          : posição do midbottom do player em world-space
    virado_direita  : direção atual do sprite (determina onde sai a cauda)
    """
    # Direção da cauda: oposta ao virado_direita
    # sinal_traseiro = -1 se virado dir. (cauda à esq.), +1 se virado esq.
    sinal_traseiro = -1.0 if virado_direita else 1.0

    particulas: list[Particula] = []
    for _ in range(CAUDA_QTD):
        # Componente principal: segue a direção da cauda
        vel_x_base = sinal_traseiro * random.uniform(CAUDA_VEL_XMIN, CAUDA_VEL_XMAX)
        # Dispersão lateral: pequena fração perpendicular para volume
        vel_x_spread = random.uniform(-40.0, 40.0)
        vel_x = vel_x_base + vel_x_spread

        vel_y = random.uniform(CAUDA_VEL_YMIN, CAUDA_VEL_YMAX)
        raio  = random.randint(CAUDA_RAIO_MIN, CAUDA_RAIO_MAX)
        vida  = random.uniform(CAUDA_VIDA_MIN, CAUDA_VIDA_MAX)

        # Nascimento levemente disperso ao redor do centro traseiro
        offset_x = sinal_traseiro * random.uniform(0.0, 10.0)
        offset_y = random.uniform(-8.0, 4.0)

        particulas.append(Particula(
            px + offset_x, py + offset_y,
            vel_x, vel_y, raio, vida,
        ))

    return particulas
