"""
entities/insects/insect_factory.py
════════════════════════════════════
Factory de insetos — ponto único de criação para todo o projeto.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PADRÃO REGISTRY — sem if/elif
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_REGISTRY: dict[str, type[InsectBase]] = {
    "wandering": WanderingInsect,
    # futuro:
    # "mosca":    FlyInsect,
    # "formiga":  AntInsect,
    # "besouro":  BeetleInsect,
    # "grilo":    CricketInsect,
}

Para adicionar novo inseto:
  1. Criar entities/insects/fly_insect.py
  2. Importar e adicionar ao _REGISTRY — UMA LINHA
  3. No Tiled, criar objeto tipo="mosca"
  4. Zero mudança em main.py ou tilemap_loader.py

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DEPENDÊNCIAS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  entities.insects.*   — subclasses de InsectBase

NÃO importa: pygame, config, main, player, tongue, hud.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from entities.insects.insect_base     import InsectBase
from entities.insects.wandering_insect import WanderingInsect

if TYPE_CHECKING:
    from tilemap_loader import InsetoDado


# ══════════════════════════════════════════════════════════════════════
# REGISTRY
# ══════════════════════════════════════════════════════════════════════

_REGISTRY: dict[str, type[InsectBase]] = {
    "wandering":   WanderingInsect,   # andador errante
    "inseto":      WanderingInsect,   # alias genérico para TMX simples

    # ── Futuras entradas ──────────────────────────────────────────────
    # "mosca":    FlyInsect,
    # "formiga":  AntInsect,
    # "besouro":  BeetleInsect,
    # "grilo":    CricketInsect,
    # "raro":     RareInsect,
}

_TIPO_PADRAO: str = "wandering"


# ══════════════════════════════════════════════════════════════════════
# FUNÇÃO PÚBLICA
# ══════════════════════════════════════════════════════════════════════

def create_insect(dados: "InsetoDado") -> InsectBase | None:
    """
    Instancia e retorna o inseto correto para os dados fornecidos.

    Parâmetros
    ──────────
    dados : InsetoDado com campos:
        x          : int   — topleft X em world-space
        y          : int   — topleft Y em world-space
        tipo       : str   — chave no registry (ex: "wandering")
        velocidade : float — px/s (opcional; default 28.0)
        area       : int   — raio de confinamento em px (opcional; default 120)

    Retorno
    ───────
    InsectBase concreto ou None se tipo desconhecido.
    None → main.py ignora silenciosamente (sem crash).
    """
    tipo = dados.get("tipo", _TIPO_PADRAO)
    cls  = _REGISTRY.get(tipo)

    if cls is None:
        print(
            f"[InsectFactory] AVISO: tipo '{tipo}' não reconhecido. "
            f"Tipos disponíveis: {sorted(_REGISTRY.keys())}. "
            f"Inseto ignorado em ({dados.get('x','?')}, {dados.get('y','?')})."
        )
        return None

    return cls(
        x          = dados["x"],
        y          = dados["y"],
        velocidade = float(dados.get("velocidade", 28.0)),
        area       = int(dados.get("area", 120)),
    )
