# sprites.py
# Contém os sprites estáticos do cenário — começando pela Plataforma.
#
# Por que herdar de pygame.sprite.Sprite?
# ────────────────────────────────────────
# Sprite é a "ficha" que o Pygame sabe gerenciar em grupo:
#   • pygame.sprite.Group.draw()        → desenha todos de uma vez
#   • pygame.sprite.spritecollide()     → testa colisão com outro sprite
# Herdando de Sprite, nossa classe entra nesses sistemas sem código extra.

import pygame
import config


class Plataforma(pygame.sprite.Sprite):
    """
    Bloco estático de cenário.

    Parâmetros
    ----------
    x, y    : posição do canto superior-esquerdo (pixels)
    largura : largura do bloco (pixels)
    altura  : altura do bloco (pixels)
    cor     : cor RGB — usa GREEN de config por padrão

    Atributos obrigatórios de pygame.sprite.Sprite
    ───────────────────────────────────────────────
    self.image  → Surface que Group.draw() vai renderizar
    self.rect   → Rect que define posição e é usado nas colisões
    Sem esses dois atributos o sistema de sprites do Pygame não funciona.
    """

    COR_PADRAO = config.GREEN

    def __init__(
        self,
        x: int,
        y: int,
        largura: int,
        altura: int,
        cor: tuple = None,
    ):
        super().__init__()          # inicializa a maquinaria interna do Sprite

        cor = cor or self.COR_PADRAO

        # image: surface sólida preenchida com a cor escolhida
        self.image = pygame.Surface((largura, altura))
        self.image.fill(cor)

        # rect: posiciona o bloco na cena e serve de hitbox
        self.rect = self.image.get_rect(topleft=(x, y))

    # Plataformas são estáticas — não precisam de update().
    # Para plataformas móveis no futuro, basta sobrescrever este método.


# ══════════════════════════════════════════════════════════════════════
class Moeda(pygame.sprite.Sprite):
    """
    Coletável que o jogador pode tocar para ganhar pontos.

    Visual: círculo amarelo com anel dourado desenhado em uma Surface
    transparente, sem depender de imagens externas.

    Por que usar SRCALPHA na Surface?
    ──────────────────────────────────
    pygame.Surface((w, h)) cria uma superfície opaca preta por padrão.
    Com o flag SRCALPHA cada pixel tem um canal alfa de 0–255, permitindo
    transparência. Assim o "fundo" do círculo não aparece — só o disco.

    Hitbox vs visual
    ─────────────────
    self.rect é quadrado (bounding box do círculo). Na colisão com o jogador
    isso é levemente mais permissivo do que o círculo exato, mas imperceptível
    em gameplay e muito mais simples de calcular.
    """

    TAMANHO   = 18            # diâmetro em pixels
    COR       = config.YELLOW
    COR_BORDA = config.GOLD
    VALOR     = 10            # pontos concedidos ao coletar

    def __init__(self, x: int, y: int):
        """
        Parâmetros
        ----------
        x, y : centro da moeda em coordenadas de mundo.
               Usar o centro facilita posicionar a moeda "acima de uma
               plataforma" sem precisar compensar pelo raio manualmente.
        """
        super().__init__()

        d = self.TAMANHO
        r = d // 2

        # Surface transparente do tamanho exato da moeda
        self.image = pygame.Surface((d, d), pygame.SRCALPHA)

        # Disco amarelo preenchido
        pygame.draw.circle(self.image, self.COR,       (r, r), r)
        # Anel dourado (borda de 2px) para dar profundidade
        pygame.draw.circle(self.image, self.COR_BORDA, (r, r), r, 2)

        # Rect centrado em (x, y) — facilita o posicionamento no level design
        self.rect = self.image.get_rect(center=(x, y))


# ══════════════════════════════════════════════════════════════════════
class Inimigo(pygame.sprite.Sprite):
    """
    Inimigo patrulheiro: anda de um lado ao outro dentro de limites fixos.

    Estratégia de patrulha: limites explícitos (x_min / x_max)
    ────────────────────────────────────────────────────────────
    Recebe as coordenadas de mundo onde deve virar. Quando rect.left
    ultrapassa x_min (ou rect.right ultrapassa x_max), a velocidade
    horizontal é invertida e o sprite é "empurrado para dentro" para
    evitar que fique oscilando na borda.

    Por que limites explícitos em vez de detecção de borda de plataforma?
    ───────────────────────────────────────────────────────────────────────
    Detectar a borda de plataforma exige um raio-cast vertical um pixel
    à frente do inimigo — mais poderoso, mas ~15 linhas extras. Para
    este estágio do projeto, limites explícitos são suficientes, mais
    simples de entender e triviais de ajustar no level design.

    Visual
    ──────
    Bloco roxo com dois "olhos" vermelhos desenhados diretamente na
    surface, sem imagens externas.
    """

    WIDTH  = 30
    HEIGHT = 40
    COR       = config.PURPLE
    COR_OLHO  = config.DARK_RED

    def __init__(
        self,
        x: int,
        y: int,
        x_min: int,
        x_max: int,
        velocidade: float = 120.0,
    ):
        """
        Parâmetros
        ----------
        x, y       : posição inicial — canto superior-esquerdo, em coords de mundo
        x_min      : limite esquerdo da patrulha (coord de mundo do rect.left)
        x_max      : limite direito  da patrulha (coord de mundo do rect.right)
        velocidade : pixels/segundo; positivo = começa indo para a direita
        """
        super().__init__()

        # --- Visual ---------------------------------------------------
        self.image = pygame.Surface((self.WIDTH, self.HEIGHT), pygame.SRCALPHA)
        self._desenhar()

        # --- Posição e física -----------------------------------------
        self.rect = self.image.get_rect(topleft=(x, y))

        # Floats precisos para acumular movimento sem perda de fração
        self.fx: float = float(x)
        self.fy: float = float(y)

        self.velocidade: float = velocidade   # pixels/segundo; sinal = direção

        # Limites de patrulha em coords de mundo
        self.x_min: int = x_min
        self.x_max: int = x_max

    # ------------------------------------------------------------------
    def _desenhar(self):
        """
        Pinta a image do inimigo.
        Separado em método próprio para facilitar recolorir no futuro
        (ex.: inimigo piscando quando atingido).
        """
        img = self.image
        w, h = self.WIDTH, self.HEIGHT

        # Corpo roxo
        img.fill(self.COR)

        # Olho esquerdo
        pygame.draw.rect(img, self.COR_OLHO, (5,  8, 7, 7))
        # Olho direito
        pygame.draw.rect(img, self.COR_OLHO, (18, 8, 7, 7))

        # Boca — linha escura simples
        pygame.draw.line(img, self.COR_OLHO, (7, 26), (23, 26), 2)

    # ------------------------------------------------------------------
    def update(self, dt: float, *args, **kwargs):
        """
        Move o inimigo horizontalmente e inverte direção nos limites.

        A assinatura aceita *args/**kwargs para compatibilidade com
        Group.update(dt, plataformas) chamado no main — o inimigo ignora
        os argumentos extras que não precisa.

        Algoritmo
        ─────────
        1. Avança fx pela velocidade * dt.
        2. Sincroniza rect.
        3. Se saiu do limite: recalcula posição encostando na borda
           e inverte o sinal da velocidade (vira de frente).
        """
        self.fx += self.velocidade * dt
        self.rect.x = int(self.fx)

        # Virada no limite ESQUERDO
        if self.rect.left <= self.x_min:
            self.rect.left = self.x_min
            self.fx        = float(self.rect.x)
            self.velocidade = abs(self.velocidade)   # garante positivo

        # Virada no limite DIREITO
        elif self.rect.right >= self.x_max:
            self.rect.right = self.x_max
            self.fx         = float(self.rect.x)
            self.velocidade = -abs(self.velocidade)  # garante negativo
