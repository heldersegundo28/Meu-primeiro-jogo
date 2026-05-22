"""
sprites.py
══════════
Sprites estáticos e dinâmicos do cenário — Plataforma, Moeda e Inimigo.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
O SISTEMA DE SPRITES DO PYGAME
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

pygame.sprite.Sprite é uma classe-base que conecta objetos ao sistema
de gerenciamento em lote do Pygame. Herdar dela dá acesso a:

  Group.draw(surface)
      Itera pelo grupo e chama surface.blit(sprite.image, sprite.rect)
      para cada membro — uma linha no Game substitui um loop manual.
      ATENÇÃO: não usado diretamente neste projeto porque a câmera
      precisa aplicar o offset antes do blit. O método aplicar() da
      Camera retorna um Rect ajustado para screen-space sem modificar
      o rect original (world-space). Ver camera.py.

  Group.update(*args, **kwargs)
      Repassa todos os argumentos para o método update() de cada
      sprite — permite um único Group.update(dt) no Game.

  sprite.kill()
      Remove o sprite de TODOS os grupos a que pertence de uma vez,
      sem referências pendentes. Usado em moedas coletadas e inimigos
      pisados.

CONTRATO DE ATRIBUTOS OBRIGATÓRIOS
────────────────────────────────────
Todo sprite deve expor exatamente dois atributos públicos:

  self.image : pygame.Surface
      O que será desenhado. Criado no __init__ e reutilizado nos
      frames seguintes (sem recriar a cada frame — custo zero).

  self.rect  : pygame.Rect
      Posição e dimensão em world-space. É a fonte-da-verdade para
      física e colisões; nunca deve ser modificado pela câmera.

Hierarquia deste módulo
────────────────────────
  pygame.sprite.Sprite
      ├── Plataforma   estático  — image/rect criados e nunca mais alterados
      ├── Moeda        estático  — SRCALPHA para transparência nos cantos
      └── Inimigo      dinâmico  — patrulha com dt-physics e float-precision
"""

from __future__ import annotations

import pygame
import config


# ══════════════════════════════════════════════════════════════════════
# PLATAFORMA
# ══════════════════════════════════════════════════════════════════════

class Plataforma(pygame.sprite.Sprite):
    """
    Bloco sólido e estático do cenário.

    Não declara update() — o Pygame usa a herança: Group.update() chama
    update() no sprite; como Plataforma não o define, herda o no-op de
    pygame.sprite.Sprite (que simplesmente não faz nada). Isso é mais
    explícito do que definir ``def update(self): pass``.

    Extensão futura
    ────────────────
    Plataformas móveis (elevadores, armadilhas) podem herdar desta
    classe e sobrescrever update(dt) sem quebrar nenhum código existente,
    pois o contrato de image/rect permanece idêntico.
    """

    # Constantes visuais como atributos de classe:
    # fáceis de sobrescrever numa subclasse sem tocar no __init__.
    COR_PADRAO: tuple = config.GREEN
    COR_BORDA:  tuple = (30, 150, 50)    # verde escuro — linha superior de volume

    def __init__(
        self,
        x: int,
        y: int,
        largura: int,
        altura: int,
        cor: tuple | None = None,
    ) -> None:
        """
        Parâmetros
        ──────────
        x, y         : topleft em coordenadas de mundo (pixels)
        largura, altura : dimensões do bloco (pixels)
        cor          : cor de preenchimento; usa COR_PADRAO se None
        """
        super().__init__()

        # ``cor if cor is not None`` (e não ``cor or default``) porque
        # (0, 0, 0) — preto — é uma cor válida e seria avaliada como
        # falsy por ``or``, trocando-a pelo default incorretamente.
        cor_final = cor if cor is not None else self.COR_PADRAO

        # Surface opaca — plataformas não precisam de transparência.
        # Surfaces sem SRCALPHA são mais rápidas de compor (blit).
        self.image = pygame.Surface((largura, altura))
        self.image.fill(cor_final)

        # Linha mais escura no topo: ilusão de volume com custo mínimo.
        # Só desenhada se a altura permite pelo menos 2 px de margem.
        if altura >= 4:
            pygame.draw.line(
                self.image, self.COR_BORDA,
                (0, 0), (largura - 1, 0),
                2,
            )

        self.rect = self.image.get_rect(topleft=(x, y))


# ══════════════════════════════════════════════════════════════════════
# MOEDA
# ══════════════════════════════════════════════════════════════════════

class Moeda(pygame.sprite.Sprite):
    """
    Coletável circular que concede pontos ao toque do jogador.

    SRCALPHA e transparência
    ─────────────────────────
    pygame.Surface((w, h)) cria uma surface opaca preta por padrão.
    O flag pygame.SRCALPHA adiciona um canal alfa de 8 bits a cada pixel,
    permitindo que áreas fora do círculo fiquem com alfa = 0 (invisíveis).
    Sem ele, o bounding box quadrado apareceria como um quadrado preto
    sobre o fundo azul do céu.

    Custo: surfaces SRCALPHA são compostas com blending por pixel,
    ligeiramente mais lentas que surfaces opacas. Para ~32 moedas
    simultâneas, o impacto é imperceptível.

    Hitbox quadrada vs. colisão circular
    ──────────────────────────────────────
    self.rect é o bounding box quadrado do círculo. Isso torna a
    detecção de colisão com spritecollide() ligeiramente mais permissiva
    que o círculo exato, mas:
      a) É imperceptível em gameplay (18px de diferença máxima).
      b) Elimina um cálculo de distância euclidiana por frame por moeda.
    Para colisão circular precisa, use pygame.sprite.collide_circle().
    """

    DIAMETRO: int = 18
    VALOR:    int = 10    # pontos concedidos ao coletar (lido por Game)

    def __init__(self, x: int, y: int) -> None:
        """
        Parâmetros
        ──────────
        x, y : centro da moeda em coordenadas de mundo.

        Posicionamento pelo centro (em vez do topleft) simplifica o
        level design: "centro do tile" = tile_x + TILE_SIZE // 2.
        get_rect(center=...) ajusta o topleft do rect automaticamente.
        """
        super().__init__()

        d = self.DIAMETRO
        r = d // 2

        # Surface quadrada transparente que envolve o círculo.
        self.image = pygame.Surface((d, d), pygame.SRCALPHA)

        # Camadas do visual, de baixo para cima (ordem de composição):
        # 1. Disco amarelo preenchido — corpo da moeda
        pygame.draw.circle(self.image, config.YELLOW, (r, r), r)
        # 2. Anel dourado (espessura 2px) — borda decorativa
        pygame.draw.circle(self.image, config.GOLD,   (r, r), r, 2)
        # 3. Ponto de reflexo — simula iluminação sem asset externo
        pygame.draw.circle(self.image, (255, 255, 200), (r - 3, r - 3), 2)

        # Rect centrado em (x, y); largura e altura = DIAMETRO
        self.rect = self.image.get_rect(center=(x, y))


# ══════════════════════════════════════════════════════════════════════
# INIMIGO
# ══════════════════════════════════════════════════════════════════════

class Inimigo(pygame.sprite.Sprite):
    """
    Patrulheiro horizontal autônomo.

    Física independente de frame rate (dt-physics)
    ────────────────────────────────────────────────
    A posição é acumulada em ``self.fx`` (float) e sincronizada para
    ``self.rect.x`` (int) a cada frame. Isso resolve dois problemas:

      1. Float drift: pygame.Rect só aceita inteiros. Mover diretamente
         ``rect.x += velocidade * dt`` descartaria a parte fracionária
         a cada frame (ex.: 0.37px descartado → inimigo perderia ~22px
         por segundo em 60 FPS). Com fx, a fração é preservada.

      2. Independência de FPS: ``fx += velocidade * dt`` garante que
         o inimigo percorre a mesma distância por segundo a qualquer
         frame rate, pelo mesmo princípio da Integração de Euler.

    Inversão de direção idempotente
    ─────────────────────────────────
    A velocidade é invertida com abs() / -abs() em vez de *= -1.
    Idempotência significa: aplicar a operação N vezes produz o mesmo
    resultado que aplicar uma vez. Se dois inimigos colidirem no mesmo
    frame e ambos tentassem inverter a direção do outro, *= -1 aplicado
    duas vezes restauraria a direção original — bug invisível. abs()
    força sempre o mesmo sinal, independente de quantas vezes é chamado.

    Correção de posição após inversão
    ────────────────────────────────────
    Ao detectar que rect.left <= x_min:
      1. Corrigimos rect.left = x_min   (tira o sprite do lado de fora)
      2. Sincronizamos fx = float(rect.x) (evita que fx contradiga rect)
      3. Invertemos velocidade             (muda a direção)
    A ordem importa: inverter antes de corrigir causaria um frame de
    movimento na direção errada antes da correção.

    Compatibilidade com Group.update()
    ────────────────────────────────────
    A assinatura ``update(self, dt, *args, **kwargs)`` aceita argumentos
    extras silenciosamente. O Game chama ``inimigos.update(dt)`` e
    ``Group.update`` repassa dt a cada sprite — sem precisar de um loop
    separado ou uma assinatura diferente por tipo de sprite.
    """

    WIDTH:  int = 30
    HEIGHT: int = 40

    def __init__(
        self,
        x: int,
        y: int,
        x_min: int,
        x_max: int,
        velocidade: float = 110.0,
    ) -> None:
        """
        Parâmetros
        ──────────
        x, y        : topleft em coordenadas de mundo (pixels)
        x_min       : limite esquerdo da patrulha — rect.left mínimo
        x_max       : limite direito  da patrulha — rect.right máximo
        velocidade  : px/s; valor positivo = começa indo para a direita
        """
        super().__init__()

        # Surface SRCALPHA: usada para o visual do sprite, mas aqui
        # serve principalmente para compatibilidade com o padrão de blit
        # da câmera (que sempre usa surface.blit(sprite.image, rect_tela)).
        self.image = pygame.Surface((self.WIDTH, self.HEIGHT), pygame.SRCALPHA)
        self._desenhar_sprite()

        self.rect = self.image.get_rect(topleft=(x, y))

        # fx: posição horizontal em float — fonte-da-verdade para o movimento.
        # rect.x é derivado de fx (int truncado), nunca o contrário.
        self.fx: float = float(x)

        self.velocidade: float = velocidade
        self.x_min:      int   = x_min
        self.x_max:      int   = x_max

    # ------------------------------------------------------------------
    def _desenhar_sprite(self) -> None:
        """
        Compõe o visual do inimigo diretamente na surface interna.

        Chamado uma única vez no __init__. Isolado em método próprio
        para permitir recolorir em estados futuros (ex.: piscar em
        vermelho ao ser atingido) sem duplicar código de desenho.
        """
        img = self.image
        w, h = self.WIDTH, self.HEIGHT

        # ── Corpo ─────────────────────────────────────────────────────
        img.fill(config.PURPLE)

        # Destaque superior: linha mais clara simula volume/curvatura
        pygame.draw.line(img, (200, 60, 240), (2, 0), (w - 3, 0), 2)

        # ── Olhos ─────────────────────────────────────────────────────
        # Quadrado vermelho-escuro + ponto branco de brilho
        pygame.draw.rect(img, config.DARK_RED, ( 5, 8, 7, 7))   # olho esquerdo
        pygame.draw.rect(img, config.DARK_RED, (18, 8, 7, 7))   # olho direito
        pygame.draw.rect(img, config.WHITE,    ( 9, 9, 2, 2))   # brilho esquerdo
        pygame.draw.rect(img, config.WHITE,    (22, 9, 2, 2))   # brilho direito

        # ── Boca ──────────────────────────────────────────────────────
        pygame.draw.line(img, config.DARK_RED, (7, 26), (23, 26), 2)

    # ------------------------------------------------------------------
    def update(self, dt: float, *args, **kwargs) -> None:
        """
        Executa um passo de patrulha para este frame.

        Fluxo de execução
        ─────────────────
          1. Integra posição: fx += velocidade × dt      (Euler explícito)
          2. Sincroniza rect.x ← int(fx)                (world-space inteiro)
          3. Verifica limite esquerdo → corrige e inverte para direita
          4. Verifica limite direito  → corrige e inverte para esquerda

        Os passos 3 e 4 são mutuamente exclusivos (elif): um inimigo
        não pode atingir os dois limites no mesmo frame, pois x_min < x_max.

        Parâmetros
        ──────────
        dt     : delta time em segundos desde o último frame
        *args, **kwargs : ignorados — permitem Group.update(dt, extras)
                          sem exigir assinatura específica por sprite
        """
        # ── Passo 1-2: integração e sincronização ─────────────────────
        self.fx    += self.velocidade * dt
        self.rect.x = int(self.fx)

        # ── Passo 3: limite esquerdo ───────────────────────────────────
        if self.rect.left <= self.x_min:
            self.rect.left  = self.x_min           # 1. corrige posição
            self.fx         = float(self.rect.x)   # 2. sincroniza float
            self.velocidade = abs(self.velocidade)  # 3. força direita (+)

        # ── Passo 4: limite direito ────────────────────────────────────
        elif self.rect.right >= self.x_max:
            self.rect.right = self.x_max
            self.fx         = float(self.rect.x)
            self.velocidade = -abs(self.velocidade) # força esquerda (-)
