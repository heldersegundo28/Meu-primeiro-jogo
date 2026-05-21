# player.py
# Define o jogador: posição, velocidade e lógica de movimento.

import pygame
import config


class Player:
    """
    Representa o personagem controlado pelo jogador.

    Responsabilidades:
      - Guardar estado (posição, velocidade, no_chao)
      - Ler input do teclado
      - Aplicar gravidade
      - Resolver colisões reais com um Group de plataformas (AABB)
      - Desenhar a si mesmo
    """

    # --- Dimensões e aparência ---
    WIDTH  = 40
    HEIGHT = 60
    COLOR  = config.RED

    # --- Física ---
    SPEED      = 250     # pixels/segundo (horizontal)
    GRAVITY    = 1200.0  # pixels/segundo² (aceleração para baixo)
    FORCA_PULO = -550.0  # pixels/segundo (impulso inicial do pulo)

    def __init__(self, x: float, y: float):
        self.x: float = float(x)
        self.y: float = float(y)

        self.vel_x: float = 0.0
        self.vel_y: float = 0.0

        self.no_chao: bool = False

        self.rect = pygame.Rect(int(self.x), int(self.y), self.WIDTH, self.HEIGHT)

    # ------------------------------------------------------------------
    def _handle_input(self):
        keys = pygame.key.get_pressed()
        self.vel_x = 0.0
        if keys[pygame.K_LEFT]  or keys[pygame.K_a]:
            self.vel_x = -self.SPEED
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.vel_x = +self.SPEED

    # ------------------------------------------------------------------
    def handle_jump(self, event: pygame.event.Event):
        """Chamado pelo Game para cada event do loop — aplica pulo via KEYDOWN."""
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
                if self.no_chao:
                    self.vel_y   = self.FORCA_PULO
                    self.no_chao = False

    # ------------------------------------------------------------------
    def _apply_gravity(self, dt: float):
        self.vel_y += self.GRAVITY * dt

    # ------------------------------------------------------------------
    def _resolve_collisions(self, plataformas: pygame.sprite.Group):
        """
        Detecção e resolução de colisão AABB (Axis-Aligned Bounding Box)
        separada por eixo.

        Por que separar eixos?
        ──────────────────────
        Se movermos x e y juntos e depois corrigirmos, não sabemos de qual
        direção veio a colisão. Separando:
          1. Move apenas em X → verifica → corrige horizontal
          2. Move apenas em Y → verifica → corrige vertical (pouso ou teto)
        Isso elimina o bug clássico de "grudar na parede ao pular rente a ela".

        Algoritmo de resolução por eixo
        ────────────────────────────────
        Para cada plataforma colidida:
          • Eixo X: empurra o jogador para fora pelo lado mais próximo.
          • Eixo Y: se vel_y > 0 (caindo) → pousa no topo (no_chao = True).
                    se vel_y < 0 (subindo) → bate no teto, zera vel_y.
        """
        # ── Passo 1: movimento e colisão HORIZONTAL ──────────────────
        self.x += self.vel_x * self._dt
        self.rect.x = int(self.x)

        for plat in pygame.sprite.spritecollide(self, plataformas, False):
            if self.vel_x > 0:                        # movendo para direita
                self.rect.right = plat.rect.left
            elif self.vel_x < 0:                      # movendo para esquerda
                self.rect.left  = plat.rect.right
            self.x = float(self.rect.x)
            self.vel_x = 0.0

        # ── Passo 2: movimento e colisão VERTICAL ────────────────────
        self.y += self.vel_y * self._dt
        self.rect.y = int(self.y)

        self.no_chao = False   # assume no ar; reavalia abaixo

        for plat in pygame.sprite.spritecollide(self, plataformas, False):
            if self.vel_y > 0:                        # caindo → pousa no topo
                self.rect.bottom = plat.rect.top
                self.no_chao     = True
            elif self.vel_y < 0:                      # subindo → bate no teto
                self.rect.top    = plat.rect.bottom
            self.vel_y = 0.0
            self.y = float(self.rect.y)

        # ── Passo 3: limites horizontais do MUNDO (não da tela) ──────
        self.x = max(0.0, min(float(self.rect.x), config.WORLD_WIDTH - self.WIDTH))
        self.rect.x = int(self.x)

    # ------------------------------------------------------------------
    def update(self, dt: float, plataformas: pygame.sprite.Group):
        """
        Atualiza o jogador para o frame atual.

        Parâmetros
        ----------
        dt          : delta time em segundos
        plataformas : Group com todas as plataformas do nível
        """
        self._dt = dt               # guardado para uso interno em _resolve_collisions

        self._handle_input()
        self._apply_gravity(dt)
        self._resolve_collisions(plataformas)

        # Sincroniza floats com o rect corrigido pelas colisões
        self.x = float(self.rect.x)
        self.y = float(self.rect.y)

    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface):
        pygame.draw.rect(surface, self.COLOR, self.rect)
