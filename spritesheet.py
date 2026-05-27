"""
spritesheet.py
══════════════
Utilitário de carregamento e fatiamento de spritesheets para pixel art.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
O QUE É UMA SPRITESHEET E POR QUE USÁ-LA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Uma spritesheet é um único arquivo PNG que contém múltiplos frames de
animação organizados em uma grade regular (grid):

    player_sheet.png  (128 × 96 px para 4 colunas × 3 linhas de 32×32)
    ┌─────────┬─────────┬─────────┬─────────┐
    │ idle  0 │ idle  1 │ idle  2 │ idle  3 │  ← row 0  y = 0
    ├─────────┼─────────┼─────────┼─────────┤
    │  run  0 │  run  1 │  run  2 │  run  3 │  ← row 1  y = 32
    ├─────────┼─────────┼─────────┼─────────┤
    │ jump  0 │ jump  1 │ jump  2 │ jump  3 │  ← row 2  y = 64
    └─────────┴─────────┴─────────┴─────────┘
      col 0     col 1     col 2     col 3
      x = 0     x = 32    x = 64    x = 96

Vantagens em relação a arquivos individuais por frame:
  • Uma única chamada a pygame.image.load() e .convert_alpha()
  • Um único objeto Surface na memória — sem cópia; subsurfaces
    compartilham o buffer de pixels da Surface pai (veja abaixo)
  • Melhor cache de GPU / menos trocas de textura (batch rendering)
  • Distribuição simplificada: um arquivo por personagem/objeto

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SUBSURFACES — A MATEMÁTICA DO FATIAMENTO EM MEMÓRIA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

pygame.Surface.subsurface(rect) retorna uma "janela" sobre a Surface
pai — não copia pixels, apenas registra um ponteiro + offset:

    ┌─────────────────────── sheet (RAM) ─────────────────────────────┐
    │  . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .   │
    │  . . . ┌──────────┐ . . . . . . . . . . . . . . . . . . . .   │
    │  . . . │ subsurface│ . . . . . . . . . . . . . . . . . . . .   │
    │  . . . │  (frame) │ . . . . . . . . . . . . . . . . . . . .   │
    │  . . . └──────────┘ . . . . . . . . . . . . . . . . . . . .   │
    └─────────────────────────────────────────────────────────────────┘

Consequências práticas:
  1. Custo de memória O(1) — independente do número de frames cortados.
  2. Modificar pixels da subsurface modifica a Surface pai (e vice-versa).
     → Por isso get_frame() retorna uma CÓPIA (.copy()) quando isolamento
       é necessário (ex.: aplicar colorize por estado de dano).
     → get_sequencia() retorna subsurfaces diretas (sem copy) para uso
       somente-leitura no loop de animação — máxima eficiência.
  3. A Surface pai NÃO pode ser liberada enquanto subsurfaces existirem.
     → A instância de Spritesheet deve ter o mesmo ciclo de vida que
       os sprites que a consomem (normalmente: todo o nível).

Fórmula de conversão  (coluna/linha) → coordenadas de pixel:
    x  =  coluna  × largura_frame
    y  =  linha   × altura_frame

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
convert_alpha() — POR QUE É OBRIGATÓRIO PARA PIXEL ART
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

pygame.image.load() retorna uma Surface no formato de pixel do arquivo
(normalmente RGBA de 32 bits ou RGB de 24 bits).

.convert_alpha() re-codifica a Surface para o formato de pixel nativo
do display do sistema operacional, adicionando canal alfa por pixel.
Isso elimina a conversão de formato a cada blit() — que ocorreria 60
vezes por segundo por sprite sem convert_alpha().

Benchmark típico: blit() com convert_alpha() é 3–5× mais rápido do que
sem, especialmente em spritesheets com muita transparência (pixel art).

Restrição: convert_alpha() só pode ser chamado DEPOIS de
pygame.display.set_mode() — antes disso o display ainda não tem formato
nativo definido. Spritesheet.__init__() assume que o display já foi
inicializado (o que é sempre verdade quando chamado de Game.__init__).
"""

from __future__ import annotations

import warnings

import pygame

import config


class Spritesheet:
    """
    Carrega uma spritesheet e expõe métodos para fatiamento de frames.

    Ciclo de vida esperado
    ──────────────────────
    Uma instância por arquivo de imagem, criada no __init__ do sprite
    ou do Game que a utiliza. Deve permanecer viva enquanto qualquer
    subsurface retornada por get_sequencia() estiver em uso.

    Atributos públicos
    ──────────────────
    sheet    : pygame.Surface — a imagem completa em memória
    largura  : int            — largura total da sheet em pixels
    altura   : int            — altura total da sheet em pixels
    carregada: bool           — False se o fallback foi usado
    """

    # Cor do fallback quando o arquivo não é encontrado.
    # Magenta puro é convenção de "textura faltando" em engines profissionais
    # (Valve Source Engine, Unreal) — imediatamente visível em jogo.
    _COR_FALLBACK: tuple[int, int, int, int] = (255, 0, 255, 255)

    def __init__(self, caminho_imagem: str) -> None:
        """
        Carrega a imagem e a converte para o formato nativo do display.

        Comportamento de fallback
        ──────────────────────────
        Se o arquivo não existir ou o Pygame não conseguir decodificá-lo,
        uma Surface de fallback magenta é criada com as dimensões padrão
        de config (FRAME_WIDTH × FRAME_HEIGHT). O jogo continua rodando —
        o sprite aparece como um quadrado magenta em vez de travar.

        Um UserWarning é emitido em vez de print() porque:
          • warnings.warn() respeita filtros de silêncio (-W ignore)
          • IDEs e sistemas de CI capturam warnings automaticamente
          • O stack trace aponta para o caller, não para este __init__

        Parâmetro
        ─────────
        caminho_imagem : str
            Caminho absoluto ou relativo para o arquivo PNG.
            Use as constantes de config.py (ex.: config.SPRITE_PLAYER)
            para garantir portabilidade entre sistemas operacionais.
        """
        self.carregada: bool = True

        try:
            # Carrega do disco e converte para o formato nativo do display.
            # .convert_alpha() é obrigatório para transparência eficiente
            # — veja a docstring do módulo para detalhes de desempenho.
            self.sheet: pygame.Surface = (
                pygame.image.load(caminho_imagem).convert_alpha()
            )

        except (FileNotFoundError, pygame.error) as exc:
            # ── Fallback: Surface magenta ──────────────────────────────
            # Tamanho = um único frame padrão — evita erro de subsurface
            # ao tentar recortar frames de uma Surface vazia.
            fb_w = config.FRAME_WIDTH
            fb_h = config.FRAME_HEIGHT

            self.sheet = pygame.Surface((fb_w, fb_h), pygame.SRCALPHA)
            self.sheet.fill(self._COR_FALLBACK)
            self.carregada = False

            warnings.warn(
                f"[Spritesheet] Imagem não encontrada: '{caminho_imagem}' — {exc}. "
                f"Usando fallback {fb_w}×{fb_h}px magenta.",
                UserWarning,
                stacklevel=2,   # aponta o aviso para o caller, não para cá
            )

        # Dimensões cached — evita chamar get_size() repetidamente
        self.largura: int
        self.altura:  int
        self.largura, self.altura = self.sheet.get_size()

    # ══════════════════════════════════════════════════════════════════
    # MÉTODOS DE FATIAMENTO
    # ══════════════════════════════════════════════════════════════════

    def get_frame(
        self,
        x:       int,
        y:       int,
        largura: int,
        altura:  int,
        *,
        escala:  tuple[int, int] | None = None,
    ) -> pygame.Surface:
        """
        Recorta e retorna um único frame da spritesheet.

        Matemática do fatiamento
        ──────────────────────────
        O Rect passado para subsurface define uma janela sobre a Surface
        pai em coordenadas de pixel:

            Rect(x, y, largura, altura)
              │    │
              │    └── y = linha × altura_frame
              └──────── x = coluna × largura_frame

        Retorna uma CÓPIA (.copy()) da subsurface para que operações de
        transformação (flip, colorize, scale) não afetem a sheet original
        nem os frames de outros sprites que compartilham a mesma instância.

        Parâmetros
        ──────────
        x, y          : origem do frame em pixels na sheet
        largura, altura : dimensões do frame em pixels
        escala        : se fornecido, redimensiona para (w, h) após o corte
                        — útil para escalar frames de 32×32 para o tamanho
                          de colisão do Player (40×60) antes do blit

        Levanta
        ───────
        ValueError   : se o Rect estiver fora dos limites da sheet
        """
        area      = pygame.Rect(x, y, largura, altura)
        sheet_rect = self.sheet.get_rect()

        if not sheet_rect.contains(area):
            if not self.carregada:
                # Sheet é fallback — retorna frame magenta do tamanho pedido
                # em vez de travar. O erro visual (magenta) indica o problema.
                frame = pygame.Surface((largura, altura), pygame.SRCALPHA)
                frame.fill(self._COR_FALLBACK)
                if escala is not None:
                    frame = pygame.transform.scale(frame, escala)
                return frame
            # Sheet real com coordenadas erradas — levanta com mensagem clara
            raise ValueError(
                f"Frame Rect({x}, {y}, {largura}, {altura}) está fora dos "
                f"limites da sheet ({self.largura}×{self.altura}px). "
                f"Verifique as constantes FRAME_WIDTH/HEIGHT em config.py."
            )

        # .copy() garante isolamento — veja docstring do módulo (seção SUBSURFACES)
        frame = self.sheet.subsurface(area).copy()

        if escala is not None:
            frame = pygame.transform.scale(frame, escala)

        return frame

    # ------------------------------------------------------------------
    def get_sequencia(
        self,
        linha:         int,
        total_frames:  int,
        largura_frame: int,
        altura_frame:  int,
        *,
        escala:        tuple[int, int] | None = None,
        espelhar_x:    bool = False,
    ) -> list[pygame.Surface]:
        """
        Retorna todos os frames de uma linha (strip) da spritesheet.

        Este é o método principal do pipeline de animação. Normalmente
        chamado uma vez na inicialização do sprite para cada estado
        ("parado", "correndo", "pulando") e o resultado é armazenado
        em um dicionário de atlas:

            atlas = {
                "parado":   sheet.get_sequencia(0, 4, 32, 32),
                "correndo": sheet.get_sequencia(1, 4, 32, 32),
                "pulando":  sheet.get_sequencia(2, 4, 32, 32),
            }

        O frame correto é acessado por índice a cada frame de jogo:
            frame_surf = atlas[estado_animacao][frame_atual]

        Matemática da sequência
        ────────────────────────
        Para a linha `linha` e o frame de índice `i` (0-based):

            x  =  i     × largura_frame      (avança horizontalmente)
            y  =  linha × altura_frame        (seleciona a strip)

        Visualização para linha=1, 4 frames de 32×32:
            i=0 → Rect(  0, 32, 32, 32)
            i=1 → Rect( 32, 32, 32, 32)
            i=2 → Rect( 64, 32, 32, 32)
            i=3 → Rect( 96, 32, 32, 32)

        Subsurfaces vs. cópias neste método
        ─────────────────────────────────────
        Retornamos subsurfaces diretas (sem .copy()) quando escala e
        espelhar_x estão desativados — máxima eficiência para o loop
        de animação somente-leitura. Quando escala ou espelhar estão
        ativos, o resultado já é uma nova Surface independente.

        Parâmetros
        ──────────
        linha          : índice da linha na sheet (0-based)
        total_frames   : número de frames na sequência
        largura_frame  : largura de cada frame em pixels
        altura_frame   : altura de cada frame em pixels
        escala         : redimensiona cada frame para (w, h) se fornecido
        espelhar_x     : se True, aplica flip horizontal em cada frame
                         (útil para gerar a versão "virado para a esquerda"
                          sem duplicar a sheet no arquivo de imagem)

        Retorno
        ───────
        list[pygame.Surface] com exatamente `total_frames` elementos,
        indexados de 0 (primeiro frame) a total_frames-1 (último).
        """
        y_origem = linha * altura_frame

        sequencia: list[pygame.Surface] = []

        for i in range(total_frames):
            x_origem = i * largura_frame
            area     = pygame.Rect(x_origem, y_origem, largura_frame, altura_frame)

            # ── Corte seguro: tenta subsurface, usa fallback se fora dos limites ──
            # Quando self.carregada=False (arquivo não encontrado), a sheet
            # tem apenas 32×32px — qualquer sequência com mais de 1 frame ou
            # linha > 0 ficaria fora dos limites. Em vez de propagar ValueError,
            # geramos um frame magenta do tamanho correto para que o jogo
            # continue rodando visivelmente, mas sem travar.
            if self.sheet.get_rect().contains(area):
                frame: pygame.Surface = self.sheet.subsurface(area)
            else:
                # Frame fallback individual — tamanho exato do que foi pedido
                frame = pygame.Surface((largura_frame, altura_frame), pygame.SRCALPHA)
                frame.fill(self._COR_FALLBACK)

            # Escala e/ou flip produzem uma Surface nova e independente
            if escala is not None:
                frame = pygame.transform.scale(frame, escala)
            if espelhar_x:
                frame = pygame.transform.flip(frame, True, False)

            sequencia.append(frame)

        return sequencia

    # ══════════════════════════════════════════════════════════════════
    # UTILITÁRIOS DE INSPEÇÃO
    # ══════════════════════════════════════════════════════════════════

    def total_colunas(self, largura_frame: int) -> int:
        """
        Retorna quantos frames cabem horizontalmente na sheet.

        Útil para validar config.py antes de rodar:
            assert sheet.total_colunas(config.FRAME_WIDTH) >= 4
        """
        return self.largura // largura_frame

    def total_linhas(self, altura_frame: int) -> int:
        """
        Retorna quantas strips (linhas de animação) a sheet contém.

        Útil para verificar se a sheet tem todas as animações esperadas:
            assert sheet.total_linhas(config.FRAME_HEIGHT) >= 3  # idle, run, jump
        """
        return self.altura // altura_frame

    def __repr__(self) -> str:
        """Representação de depuração legível no terminal e no debugger."""
        status = "carregada" if self.carregada else "FALLBACK"
        return (
            f"Spritesheet({self.largura}×{self.altura}px, {status})"
        )
