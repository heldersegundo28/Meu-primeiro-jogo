# Jogo de plataforma 2D com Python

Protótipo para estudar programação de jogos com Pygame: movimentação, colisões, câmera, inimigos, estados e progressão de fases.

**Status:** em desenvolvimento, com módulos experimentais e duplicados que precisam de consolidação.

## Sistemas presentes no código

- Loop com atualização por delta time.
- Movimento, salto, colisões e ataque de língua.
- Câmera, plataformas móveis, inimigos e armadilhas.
- Menu, pausa, HUD e estados de vitória e derrota.
- Fases em texto, checkpoints e salvamento local.
- Suporte opcional a mapas Tiled no carregador.

## Executar

Use Python 3.12 ou 3.13 e Git.

~~~bash
git clone https://github.com/heldersegundo28/Meu-primeiro-jogo.git
cd Meu-primeiro-jogo
python -m venv .venv
~~~

Ative no PowerShell:

~~~powershell
.\.venv\Scripts\Activate.ps1
~~~

No Linux/macOS, use `source .venv/bin/activate`.

~~~bash
python -m pip install -r requirements.txt
python main.py
~~~

Execute na raiz do projeto, mantendo pastas de recursos e arquivos de fase. Mapas `.tmx` precisam também de `pytmx`; as fases `.txt` não exigem essa biblioteca.

## Controles

| Ação | Teclas |
| --- | --- |
| Mover | A/D ou setas esquerda/direita |
| Saltar | Espaço, W ou seta para cima |
| Ataque de língua | X |
| Navegar nos menus | W/S ou setas cima/baixo |
| Confirmar no menu | Enter |
| Pausar/retomar a partida | Esc |
| Reiniciar após vitória/derrota | R |
| Voltar ao menu após vitória/derrota | M |

## Organização

| Arquivos | Função |
| --- | --- |
| `main.py` | Inicialização, loop e estados |
| `player.py`, `tongue.py` | Jogador e ataque |
| `camera.py`, `hud.py` | Câmera e interface |
| `enemies/`, `entities/` | Inimigos e insetos |
| `tilemap_loader.py`, `fase*.txt` | Leitura e definição das fases |
| `save_manager.py` | Persistência do progresso |
| `config.py` | Configurações e caminhos dos recursos |

## Verificação e limites

~~~bash
python -m compileall -q .
~~~

A integração contínua verifica sintaxe e importação dos módulos com as dependências instaladas. Isso não substitui teste manual de jogabilidade e áudio.

Há caminhos de imagens e sons configurados que não estão incluídos no repositório; alguns componentes possuem recursos alternativos. A distribuição requer revisão dos assets e teste completo da campanha antes de ser apresentada como jogo finalizado.

Os recursos de terceiros mantêm suas condições de uso. Não há licença geral definida para todo o jogo.

Próximos passos: consolidar módulos duplicados, revisar recursos necessários e testar regras independentes da renderização.
