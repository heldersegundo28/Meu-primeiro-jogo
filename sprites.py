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
