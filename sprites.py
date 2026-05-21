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
