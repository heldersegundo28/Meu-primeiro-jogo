# camera.py
# Calcula o deslocamento (offset) que deve ser aplicado a todos os objetos
# do mundo na hora do desenho, dando a ilusão de uma câmera que segue o jogador.
#
# Conceito central
# ─────────────────
# Nada se move de verdade: o jogador e as plataformas sempre existem nas suas
# coordenadas de mundo (world-space). O que a câmera faz é calcular um vetor
# de deslocamento (offset_x) que, subtraído de cada posição antes de desenhar,
# cria a ilusão de scroll.
#
#   posição_na_tela = posição_no_mundo - camera.offset_x
#
# Exemplo: jogador em x=1000, offset_x=600 → desenhado em x=400 (centro da tela).

import pygame
import config


class Camera:
    """
    Câmera de scroll horizontal com centralização suave e limites de mundo.

    Estratégia: centralização simples ("snap to center")
    ─────────────────────────────────────────────────────
    A câmera tenta manter o jogador exatamente no centro horizontal da tela.
    Quando o jogador se aproxima das bordas do mundo (< metade da tela de
    distância da borda), o offset é travado para não mostrar área fora do mundo.

    Variação futura: "dead zone" / câmera com inércia
    ──────────────────────────────────────────────────
    Para uma câmera mais suave, você pode interpolar o offset em direção ao
    alvo em vez de encaixar diretamente:
        self.offset_x += (alvo - self.offset_x) * LERP_SPEED * dt
    Isso cria uma câmera com atraso que parece mais cinematográfica.
    """

    def __init__(self):
        # Deslocamento horizontal atual em pixels.
        # Aplicado como: rect_na_tela.x = rect_no_mundo.x - self.offset_x
        self.offset_x: float = 0.0

        # Ponto de ancoragem: queremos o jogador nesta posição X da tela.
        # Centralizar = metade da largura da tela.
        self._ancora_x: float = config.SCREEN_WIDTH / 2.0

        # Limites do offset calculados uma vez (não mudam durante o nível).
        self._offset_min: float = 0.0
        self._offset_max: float = float(config.WORLD_WIDTH - config.SCREEN_WIDTH)

    # ------------------------------------------------------------------
    def update(self, alvo: pygame.Rect):
        """
        Recalcula offset_x para centralizar o alvo na tela.

        Parâmetro
        ---------
        alvo : rect do objeto a seguir (normalmente player.rect)

        Cálculo passo a passo
        ─────────────────────
        1. Queremos que  alvo.centerx - offset_x  ==  âncora_x
        2. Logo:         offset_x = alvo.centerx - âncora_x
        3. Depois travamos o resultado entre offset_min e offset_max
           para não mostrar área além das bordas do mundo.
        """
        alvo_offset = float(alvo.centerx) - self._ancora_x

        # clamp: garante  offset_min <= offset_x <= offset_max
        self.offset_x = max(self._offset_min, min(alvo_offset, self._offset_max))

    # ------------------------------------------------------------------
    def aplicar(self, rect: pygame.Rect) -> pygame.Rect:
        """
        Retorna um novo Rect com a posição ajustada para a tela.

        Uso no draw():
            rect_tela = camera.aplicar(sprite.rect)
            surface.blit(sprite.image, rect_tela)

        NÃO modifica o rect original — as coordenadas de mundo permanecem
        intactas para física e colisões.
        """
        return pygame.Rect(
            int(rect.x - self.offset_x),
            rect.y,
            rect.width,
            rect.height,
        )
