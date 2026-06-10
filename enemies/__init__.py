# enemies/__init__.py
# Pacote de inimigos — expose a factory como ponto de entrada público.
from enemies.enemy_factory import create_enemy

__all__ = ["create_enemy"]
