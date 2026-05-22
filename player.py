# player.py
# Define o jogador: física, input, colisões e animação procedural.
#
# Arquitetura de animação (sem arquivos externos)
# ─────────────────────────────────────────────────────────────────────
# Um sistema de animação real com spritesheets funciona assim:
#
#   1. estado_animacao  → QUAL sequência de frames tocar ("correndo", etc.)
#   2. frame_atual      → QUAL frame da sequência mostrar agora (0, 1, 2…)
#   3. tempo_animacao   → cronômetro que decide quando avançar o frame
#
# Aqui implementamos exatamente essa estrutura, mas em vez de trocar
# imagens, mudamos como o retângulo é desenhado — deixando a lógica
# de animação 100% funcional e pronta para receber sprites reais
# substituindo apenas o método draw().

import math
import pygame
import config


class Player:
    """
    Responsabilidades:
      - Física (gravidade, pulo, dt-based)
      - Input do teclado
      - Colisão AABB por eixo com plataformas
      - Máquina de estados de animação
      - Renderização procedural (prontos para sprites)
    """

    # ── Dimensões ────────────────────────────────────────────────────
    WIDTH  = 40
    HEIGHT = 60

    # ── Física ───────────────────────────────────────────────────────
    SPEED      = 250.0    # pixels/segundo
    GRAVITY    = 1200.0   # pixels/segundo²
    FORCA_PULO = -550.0   # pixels/segundo (negativo = para cima)

    # ── Animação ─────────────────────────────────────────────────────
    TOTAL_FRAMES    = 4      # frames na sequência de corrida: 0, 1, 2, 3
    FPS_CORRIDA     = 10.0   # frames de animação por segundo ao correr
    # Intervalo em segundos entre troca de frame  = 1 / FPS_CORRIDA
    _INTERVALO      = 1.0 / FPS_CORRIDA

    # ── Paleta procedural ────────────────────────────────────────────
    # Cores base para cada estado — variam ligeiramente entre frames
    _COR_PARADO  = config.RED
    _COR_CORRENDO = (200, 60, 60)   # vermelho levemente diferente
    _COR_PULANDO  = (255, 80, 80)   # mais claro — sensação de leveza

    # ─────────────────────────────────────────────────────────────────
    def __init__(self, x: float, y: float):
        # ── Posição e física ─────────────────────────────────────────
        self.x: float = float(x)
        self.y: float = float(y)
        self.vel_x: float = 0.0
        self.vel_y: float = 0.0
        self.no_chao: bool = False
        self.rect = pygame.Rect(int(self.x), int(self.y), self.WIDTH, self.HEIGHT)
        self._dt: float = 0.0          # guardado para _resolve_collisions

        # ── Direção do sprite ────────────────────────────────────────
        # True = virado para a direita; False = para a esquerda.
        # Quando usarmos spritesheets, basta fazer flip da Surface aqui.
        self.virado_direita: bool = True

        # ── Máquina de estados de animação ───────────────────────────
        self.estado_animacao: str = "parado"   # "parado" | "correndo" | "pulando"
        self.frame_atual:     int = 0          # 0 … TOTAL_FRAMES-1
        self.tempo_animacao: float = 0.0       # cronômetro em segundos

        # ── Flag de pulo para o sistema de áudio ─────────────────────
        # Levantada em handle_jump e lida (e zerada) pelo Game no update.
        # Evita passar referência ao mixer para dentro do Player —
        # o Player apenas sinaliza "algo aconteceu"; quem decide tocar
        # o som é o Game. Padrão: Flag de Evento de Um Frame.
        self.pulou: bool = False

    # ══════════════════════════════════════════════════════════════════
    # FÍSICA
    # ══════════════════════════════════════════════════════════════════

    def _handle_input(self):
        keys = pygame.key.get_pressed()
        self.vel_x = 0.0
        if keys[pygame.K_LEFT]  or keys[pygame.K_a]:
            self.vel_x = -self.SPEED
            self.virado_direita = False
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.vel_x = +self.SPEED
            self.virado_direita = True

    def handle_jump(self, event: pygame.event.Event):
        """Chamado pelo Game para cada event — aplica pulo via KEYDOWN."""
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
                if self.no_chao:
                    self.vel_y   = self.FORCA_PULO
                    self.no_chao = False
                    self.pulou   = True   # sinaliza ao Game para tocar o som

    def _apply_gravity(self, dt: float):
        self.vel_y += self.GRAVITY * dt

    def _resolve_collisions(self, plataformas: pygame.sprite.Group):
        # ── Eixo X ───────────────────────────────────────────────────
        self.x += self.vel_x * self._dt
        self.rect.x = int(self.x)
        for plat in pygame.sprite.spritecollide(self, plataformas, False):
            if self.vel_x > 0:
                self.rect.right = plat.rect.left
            elif self.vel_x < 0:
                self.rect.left  = plat.rect.right
            self.x     = float(self.rect.x)
            self.vel_x = 0.0

        # ── Eixo Y ───────────────────────────────────────────────────
        self.y += self.vel_y * self._dt
        self.rect.y = int(self.y)
        self.no_chao = False
        for plat in pygame.sprite.spritecollide(self, plataformas, False):
            if self.vel_y > 0:
                self.rect.bottom = plat.rect.top
                self.no_chao     = True
            elif self.vel_y < 0:
                self.rect.top    = plat.rect.bottom
            self.vel_y = 0.0
            self.y     = float(self.rect.y)

        # ── Limites do mundo ─────────────────────────────────────────
        self.x = max(0.0, min(float(self.rect.x), config.WORLD_WIDTH - self.WIDTH))
        self.rect.x = int(self.x)

    # ══════════════════════════════════════════════════════════════════
    # ANIMAÇÃO
    # ══════════════════════════════════════════════════════════════════

    def _atualizar_estado_animacao(self):
        """
        Determina QUAL sequência de animação deve estar tocando agora,
        baseado nas variáveis de física.

        Prioridade (ordem importa):
          1. No ar  → "pulando"  (domina qualquer velocidade horizontal)
          2. Movendo-se horizontalmente no chão → "correndo"
          3. Parado no chão → "parado"

        Quando usarmos spritesheets, este método determina qual
        linha/strip do atlas de sprites será lida.
        """
        if not self.no_chao:
            novo = "pulando"
        elif self.vel_x != 0.0:
            novo = "correndo"
        else:
            novo = "parado"

        # Troca de estado: reinicia cronômetro e vai para frame 0
        # para não "entrar no meio" de uma animação.
        if novo != self.estado_animacao:
            self.estado_animacao = novo
            self.frame_atual     = 0
            self.tempo_animacao  = 0.0

    def _atualizar_frames(self, dt: float):
        """
        Avança o frame_atual quando o cronômetro atinge o intervalo.

        Só avança frames no estado "correndo" — parado e pulando
        ficam fixos no frame 0 (pose neutra).

        Lógica do cronômetro
        ────────────────────
        tempo_animacao acumula dt a cada update.
        Quando ultrapassa _INTERVALO (0.1 s para 10 FPS):
          • desconta o intervalo (não zera — preserva o resto para
            não "perder" tempo entre frames, mantendo o ritmo preciso)
          • avança frame_atual em módulo TOTAL_FRAMES (0→1→2→3→0…)

        Esta mesma estrutura funciona identicamente com spritesheets:
        basta usar frame_atual como índice na lista de Surfaces.
        """
        if self.estado_animacao == "correndo":
            self.tempo_animacao += dt
            while self.tempo_animacao >= self._INTERVALO:
                self.tempo_animacao -= self._INTERVALO          # preserva o resto
                self.frame_atual = (self.frame_atual + 1) % self.TOTAL_FRAMES
        else:
            # Parado ou pulando: pose neutra
            self.frame_atual    = 0
            self.tempo_animacao = 0.0

    # ══════════════════════════════════════════════════════════════════
    # UPDATE PRINCIPAL
    # ══════════════════════════════════════════════════════════════════

    def update(self, dt: float, plataformas: pygame.sprite.Group):
        """
        Ordem de operações por frame:
          1. Input          → define intenção do jogador
          2. Gravidade      → acumula vel_y
          3. Colisões       → move e corrige posição
          4. Sincroniza floats ← rect corrigido
          5. Estado anim.   → decide qual sequência tocar
          6. Frames         → avança o cronômetro/frame
        """
        self._dt = dt

        self._handle_input()
        self._apply_gravity(dt)
        self._resolve_collisions(plataformas)

        self.x = float(self.rect.x)
        self.y = float(self.rect.y)

        # Animação — sempre depois da física para ler o estado correto
        self._atualizar_estado_animacao()
        self._atualizar_frames(dt)

    # ══════════════════════════════════════════════════════════════════
    # RENDERIZAÇÃO PROCEDURAL
    # ══════════════════════════════════════════════════════════════════
    #
    # Este método desenha o personagem com primitivas do Pygame
    # reagindo a estado_animacao e frame_atual — exatamente como um
    # sistema de sprites reais faria, trocando Surface em vez de cor.
    #
    # Estrutura de substituição futura:
    #   sprites = { "parado": [surf0], "correndo": [s0,s1,s2,s3], ... }
    #   surface.blit(sprites[self.estado_animacao][self.frame_atual], rect_tela)
    #
    # ══════════════════════════════════════════════════════════════════

    def draw(self, surface: pygame.Surface, rect_tela: pygame.Rect = None):
        """
        Parâmetros
        ----------
        surface   : Surface de destino (normalmente self.screen de Game)
        rect_tela : Rect já com offset de câmera aplicado.
                    Se None, usa self.rect (sem câmera — útil para testes).
        """
        r = rect_tela if rect_tela is not None else self.rect

        if self.estado_animacao == "parado":
            self._draw_parado(surface, r)
        elif self.estado_animacao == "correndo":
            self._draw_correndo(surface, r)
        elif self.estado_animacao == "pulando":
            self._draw_pulando(surface, r)

    # ------------------------------------------------------------------
    # Poses por estado
    # ------------------------------------------------------------------

    def _draw_parado(self, surface: pygame.Surface, r: pygame.Rect):
        """
        Pose neutra: corpo vermelho sólido + olhos brancos fixos.
        frame_atual é sempre 0 neste estado — nenhuma animação roda.
        """
        # Corpo
        pygame.draw.rect(surface, self._COR_PARADO, r)

        # Olhos: dois quadradinhos brancos no terço superior do corpo
        ow, oh = 7, 7     # largura e altura de cada olho
        oy = r.top + 10   # posição y dos olhos
        if self.virado_direita:
            olho_esq = pygame.Rect(r.left  + 5,  oy, ow, oh)
            olho_dir = pygame.Rect(r.right - 14, oy, ow, oh)
        else:
            olho_esq = pygame.Rect(r.left  + 5,  oy, ow, oh)
            olho_dir = pygame.Rect(r.right - 14, oy, ow, oh)

        pygame.draw.rect(surface, config.WHITE, olho_esq)
        pygame.draw.rect(surface, config.WHITE, olho_dir)

        # Pupila: quadrado preto menor, deslocado para o lado que o jogador olha
        desl = 2 if self.virado_direita else -2
        pygame.draw.rect(surface, config.BLACK,
                         olho_esq.move(desl, 1).inflate(-3, -3))
        pygame.draw.rect(surface, config.BLACK,
                         olho_dir.move(desl, 1).inflate(-3, -3))

    def _draw_correndo(self, surface: pygame.Surface, r: pygame.Rect):
        """
        Animação de corrida: 4 frames que alternam a posição de duas
        'pernas' (linhas) embaixo do corpo, simulando passadas.

        Mapa de frames → posição das pernas:
          frame 0: perna esq baixa, perna dir alta    (passada A)
          frame 1: ambas no meio                      (neutro)
          frame 2: perna esq alta, perna dir baixa    (passada B)
          frame 3: ambas no meio                      (neutro)

        Este padrão de 4 frames é o mesmo usado em spritesheets de
        personagens 2D clássicos (ciclo de caminhada).
        """
        # Corpo com tom ligeiramente diferente do estado parado
        pygame.draw.rect(surface, self._COR_CORRENDO, r)

        # Olhos (mesmos do estado parado para manter identidade visual)
        self._draw_parado(surface, r)   # reutiliza olhos; corpo já foi desenhado

        # Pernas — calculamos offset vertical para cada perna por frame
        # Tabela:  frame → (offset_esq, offset_dir)  em pixels
        offsets = {
            0: ( 8, -8),   # passada A: esq baixa, dir alta
            1: ( 0,  0),   # neutro
            2: (-8,  8),   # passada B: esq alta,  dir baixa
            3: ( 0,  0),   # neutro
        }
        oe, od = offsets[self.frame_atual]

        cx     = r.centerx
        base_y = r.bottom         # linha base das pernas
        perna_h = 10              # comprimento visual da perna

        # Perna esquerda
        pygame.draw.line(
            surface, config.BLACK,
            (cx - 8, base_y),
            (cx - 8, base_y + perna_h + oe),
            3,
        )
        # Perna direita
        pygame.draw.line(
            surface, config.BLACK,
            (cx + 8, base_y),
            (cx + 8, base_y + perna_h + od),
            3,
        )

    def _draw_pulando(self, surface: pygame.Surface, r: pygame.Rect):
        """
        Pose de pulo: corpo mais claro (leveza) + braços abertos +
        pernas dobradas (linhas diagonais embaixo do corpo).

        Subindo (vel_y < 0): pernas recolhidas para cima.
        Caindo  (vel_y > 0): pernas abertas para baixo — diferencia
                              visualmente a fase de subida da descida.
        """
        # Corpo claro
        pygame.draw.rect(surface, self._COR_PULANDO, r)

        # Olhos
        self._draw_parado(surface, r)

        cx = r.centerx
        cy = r.centery

        # Braços — linha horizontal que cruza o corpo
        pygame.draw.line(surface, config.BLACK,
                         (r.left  - 6, cy - 5),
                         (r.right + 6, cy - 5), 3)

        # Pernas: recolhidas subindo, abertas caindo
        if self.vel_y < 0:
            # Subindo — pernas dobradas para cima (linhas em V invertido)
            pygame.draw.line(surface, config.BLACK,
                             (cx - 8, r.bottom),
                             (cx - 14, r.bottom - 10), 3)
            pygame.draw.line(surface, config.BLACK,
                             (cx + 8, r.bottom),
                             (cx + 14, r.bottom - 10), 3)
        else:
            # Caindo — pernas abertas para baixo (linhas em V)
            pygame.draw.line(surface, config.BLACK,
                             (cx - 8, r.bottom),
                             (cx - 14, r.bottom + 12), 3)
            pygame.draw.line(surface, config.BLACK,
                             (cx + 8, r.bottom),
                             (cx + 14, r.bottom + 12), 3)
