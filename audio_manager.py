"""audio_manager.py
════════════════════════
Gerencia sons e música do jogo com fallback silencioso.

Este arquivo existe apenas porque main.py importa AudioManager.
Ele oferece uma implementação mínima que não trava se o mixer
não estiver disponível ou se os arquivos de áudio estiverem ausentes.
"""

from __future__ import annotations

import pygame
import config


class AudioManager:
    def __init__(self) -> None:
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            self.enabled = True
        except pygame.error:
            self.enabled = False
        self._cache: dict[str, pygame.mixer.Sound | None] = {}

    def preload(self, mapa: dict[str, str], volumes: dict[str, float]) -> None:
        if not self.enabled:
            for chave in mapa:
                self._cache[chave] = None
            return

        for chave, caminho in mapa.items():
            try:
                som = pygame.mixer.Sound(caminho)
                if chave in volumes:
                    som.set_volume(volumes[chave])
                self._cache[chave] = som
            except (pygame.error, FileNotFoundError):
                self._cache[chave] = None

    def play(self, chave: str) -> None:
        if not self.enabled:
            return
        som = self._cache.get(chave)
        if som is not None:
            try:
                som.play()
            except pygame.error:
                pass

    def play_music(self, arquivo: str, volume: float = 0.40) -> None:
        if not self.enabled:
            return
        try:
            pygame.mixer.music.load(arquivo)
            pygame.mixer.music.set_volume(volume)
            pygame.mixer.music.play(-1)
        except (pygame.error, FileNotFoundError):
            pass

    def stop_music(self) -> None:
        if not self.enabled:
            return
        try:
            pygame.mixer.music.stop()
        except pygame.error:
            pass
