"""
enemies/enemy_factory.py
════════════════════════
Factory de inimigos — ponto único de criação para todo o projeto.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
POR QUE REGISTRY E NÃO IF/ELIF?
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Abordagem ingênua (o que queremos EVITAR):

    if tipo == "patrulheiro":
        return PatrolEnemy(...)
    elif tipo == "cobra":
        return SnakeEnemy(...)
    elif tipo == "sapo":
        return FrogEnemy(...)
    # → cada novo inimigo exige modificar este arquivo

Abordagem registry (implementada aqui):

    _REGISTRY: dict[str, type[EnemyBase]] = {
        "patrulheiro": PatrolEnemy,
    }

    def create_enemy(dados):
        cls = _REGISTRY[dados["tipo"]]
        return cls(...)

    # Para adicionar SnakeEnemy: APENAS registrar em _REGISTRY.
    # Este arquivo (factory) não precisa ser modificado.
    # main.py não precisa ser modificado.
    # Princípio Open/Closed: aberto para extensão, fechado para modificação.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COMO ADICIONAR UM NOVO INIMIGO (exemplo futuro: SnakeEnemy)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Criar enemies/snake_enemy.py com class SnakeEnemy(EnemyBase)
2. Aqui neste arquivo, adicionar UMA linha no registry:

       from enemies.snake_enemy import SnakeEnemy

       _REGISTRY: dict[str, type[EnemyBase]] = {
           "patrulheiro": PatrolEnemy,
           "cobra":       SnakeEnemy,   ← linha nova
       }

3. No Tiled, criar objeto com:
       Nome:  inimigo
       tipo:  cobra
       (qualquer propriedade extra que SnakeEnemy.__init__ precise)

4. create_enemy() lida com o resto — ZERO mudança em main.py ou loader.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONTRATO DA FUNÇÃO PÚBLICA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    create_enemy(dados: InimigoDado) -> EnemyBase | None

    Parâmetros
    ──────────
    dados : dict com campos de InimigoDado (tilemap_loader.py):
        x          : int    — topleft X em world-space
        y          : int    — topleft Y em world-space
        x_min      : int    — limite esquerdo de patrulha
        x_max      : int    — limite direito  de patrulha
        velocidade : float  — px/s
        tipo       : str    — chave no registry (ex: "patrulheiro")

    Retorno
    ───────
    EnemyBase concreto instanciado, ou None se o tipo não for
    reconhecido (log de aviso emitido, jogo não trava).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DEPENDÊNCIAS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  enemies.enemy_base.EnemyBase
  enemies.patrol_enemy.PatrolEnemy

NÃO importa: pygame, config, main, player, sprites, hud, tilemap_loader.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from enemies.enemy_base    import EnemyBase
from enemies.patrol_enemy  import PatrolEnemy
from enemies.snake_enemy   import SnakeEnemy

if TYPE_CHECKING:
    # Importado apenas para type checking — sem custo em runtime.
    # Evita dependência circular se tilemap_loader importar de enemies.
    from tilemap_loader import InimigoDado


# ══════════════════════════════════════════════════════════════════════
# REGISTRY
# ══════════════════════════════════════════════════════════════════════

# Mapeamento de string (campo "tipo" do TMX/TXT) → classe concreta.
#
# REGRA: adicionar novos inimigos APENAS aqui — nunca em main.py.
# Importar a classe no topo do arquivo e adicionar a entrada no dict.
#
# Aliases aceitos por tipo:
#   "patrulheiro" → PatrolEnemy  (nome semântico PT-BR)
#   "inimigo"     → PatrolEnemy  (compatibilidade com fases antigas .txt
#                                  que usam tile 'E' sem campo tipo)

_REGISTRY: dict[str, type[EnemyBase]] = {
    "patrulheiro": PatrolEnemy,
    "inimigo":     PatrolEnemy,   # alias legado — tile 'E' do .txt
    "cobra":        SnakeEnemy,

    # ── Futuras entradas (descomente quando implementar) ──────────────
    # "aranha":         SpiderEnemy,
    # "sapo":           FrogEnemy,
    # "lagarto_rival":  RivalLizardEnemy,
}

# Tipo padrão usado quando o campo "tipo" está ausente no InimigoDado.
# Mantém compatibilidade com fases antigas que não têm o campo.
_TIPO_PADRAO: str = "patrulheiro"


# ══════════════════════════════════════════════════════════════════════
# FUNÇÃO PÚBLICA
# ══════════════════════════════════════════════════════════════════════

def create_enemy(dados: "InimigoDado") -> EnemyBase | None:
    """
    Instancia e retorna o inimigo correto para os dados fornecidos.

    Resolução de tipo
    ──────────────────
    1. Lê dados["tipo"] (campo adicionado ao InimigoDado no loader)
    2. Busca no _REGISTRY
    3. Se encontrado: instancia com os parâmetros padrão de patrulha
    4. Se não encontrado: imprime aviso e retorna None
       → main.py verifica None antes de adicionar ao grupo

    Extensibilidade de parâmetros
    ──────────────────────────────
    Parâmetros além de x, y, x_min, x_max, velocidade são passados
    via **dados como kwargs. Cada subclasse define quais kwargs aceita
    em seu __init__(). Parâmetros desconhecidos são ignorados pelos
    construtores que não os declaram (graças ao padrão **kwargs).

    Tratamento de erro
    ───────────────────
    Retorna None em vez de levantar exceção — o jogo nunca trava por
    um tipo de inimigo desconhecido em um TMX. O designer é avisado
    pelo print de aviso e pode corrigir o Tiled sem reiniciar.
    """
    tipo = dados.get("tipo", _TIPO_PADRAO)

    cls = _REGISTRY.get(tipo)

    if cls is None:
        # Tipo não registrado — avisa o designer mas não trava o jogo
        print(
            f"[EnemyFactory] AVISO: tipo de inimigo '{tipo}' não reconhecido. "
            f"Tipos disponíveis: {sorted(_REGISTRY.keys())}. "
            f"Inimigo ignorado em ({dados.get('x', '?')}, {dados.get('y', '?')})."
        )
        return None

    # Instancia com os parâmetros comuns a todos os inimigos de patrulha.
    # Parâmetros específicos de subclasses futuras devem ser adicionados
    # ao InimigoDado e passados como kwargs aqui.
    return cls(
        x          = dados["x"],
        y          = dados["y"],
        x_min      = dados["x_min"],
        x_max      = dados["x_max"],
        velocidade = dados.get("velocidade", 110.0),
        dano       = dados.get("dano", 1),
    )
