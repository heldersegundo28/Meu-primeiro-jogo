"""
save_manager.py
═══════════════
Sistema de Save Game — persistência entre sessões.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RESPONSABILIDADE ÚNICA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Este módulo lê e escreve arquivos JSON. Ele NUNCA:
  • importa pygame, config, main, player ou qualquer outro módulo do projeto
  • chama métodos de transição de estado
  • modifica variáveis de jogo

O fluxo é exclusivamente:
  Game → save_manager.save(dados)   (escrita)
  save_manager.load() → Game        (leitura de primitivos)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FORMATO DO SAVE (save/savegame.json)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{
    "versao":              1,
    "fase_atual":          3,
    "checkpoint_x":        1250.0,
    "checkpoint_y":        480.0,
    "moedas_coletadas":    17,
    "vidas":               3,
    "tempo_total_jogado":  523.4
}

"versao" permite migrar saves antigos quando o formato mudar.
Todos os outros campos são primitivos Python — sem dependência de
pygame ou tipos customizados.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CAMPOS RESERVADOS PARA FUTURAS EXTENSÕES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_CAMPOS_DEFAULTS abaixo define todos os campos com seus valores padrão.
Para adicionar "habilidades_desbloqueadas", "skins", "bestiario" etc.:
  1. Adicionar entrada em _CAMPOS_DEFAULTS
  2. Adicionar coleta em Game._build_save_data()
  3. Adicionar aplicação em Game._apply_save_data()
  Nenhuma mudança em save_manager.py necessária.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DEPENDÊNCIAS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  json, pathlib, time — stdlib pura. Zero dependências externas.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing  import Any


# ══════════════════════════════════════════════════════════════════════
# CONSTANTES DE CONFIGURAÇÃO
# ══════════════════════════════════════════════════════════════════════

# Versão do formato do save — incrementar quando a estrutura mudar.
# Saves com versão menor serão migrados (ver _migrar_se_necessario).
VERSAO_SAVE: int = 1

# Localização padrão do arquivo. Pode ser sobrescrita no __init__.
PASTA_SAVE_PADRAO:   Path = Path("save")
ARQUIVO_SAVE_PADRAO: Path = PASTA_SAVE_PADRAO / "savegame.json"

# Campos obrigatórios e seus valores default.
# Um save válido deve conter TODOS estes campos.
# Campos ausentes são preenchidos com o default (tolerância a saves antigos).
_CAMPOS_DEFAULTS: dict[str, Any] = {
    "versao":             VERSAO_SAVE,
    "fase_atual":         1,
    "checkpoint_x":       None,   # None = sem checkpoint ativo
    "checkpoint_y":       None,
    "moedas_coletadas":   0,
    "vidas":              3,
    "tempo_total_jogado": 0.0,
    # ── Campos reservados para expansão futura ────────────────────────
    # "habilidades":      [],
    # "skins_desbloqueadas": [],
    # "bestiario":        {},
    # "conquistas":       [],
    # "porcentagem":      0.0,
}


# ══════════════════════════════════════════════════════════════════════
# SAVE MANAGER
# ══════════════════════════════════════════════════════════════════════

class SaveManager:
    """
    Gerencia leitura, escrita, validação e reset do save game.

    Não é um singleton — instanciar uma vez em Game.__init__() e
    manter como self._save. Não armazena estado de jogo internamente;
    apenas serializa e desserializa o dict fornecido pelo Game.

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    INTERFACE PÚBLICA
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

      exists()   → bool        — True se o arquivo de save existe
      load()     → dict | None — dados do save ou None se ausente/inválido
      save(dados)→ bool        — True se escreveu com sucesso
      reset()    → bool        — apaga o save; True se apagou com sucesso
      validate(dados) → bool   — True se todos os campos obrigatórios existem
    """

    def __init__(
        self,
        arquivo: Path | str | None = None,
    ) -> None:
        """
        Parâmetros
        ──────────
        arquivo : caminho para o savegame.json.
                  None → usa ARQUIVO_SAVE_PADRAO (save/savegame.json).
        """
        self._arquivo: Path = Path(arquivo) if arquivo else ARQUIVO_SAVE_PADRAO
        self._pasta:   Path = self._arquivo.parent

    # ------------------------------------------------------------------
    # INTERFACE PÚBLICA
    # ------------------------------------------------------------------

    def exists(self) -> bool:
        """True se o arquivo de save existe e não está vazio."""
        return self._arquivo.exists() and self._arquivo.stat().st_size > 0

    def load(self) -> dict[str, Any] | None:
        """
        Carrega e valida o save game.

        Retorno
        ───────
        dict com os dados do save — todos os campos obrigatórios garantidos
        (campos ausentes são preenchidos com defaults).

        None se:
          • arquivo não existe
          • JSON inválido (corrompido)
          • dados não passam na validação estrutural mínima

        Em caso de erro: imprime aviso no terminal, não levanta exceção.
        O Game trata None como "novo jogo".
        """
        if not self.exists():
            return None

        try:
            with open(self._arquivo, encoding="utf-8") as f:
                dados = json.load(f)
        except (json.JSONDecodeError, OSError, UnicodeDecodeError) as e:
            print(f"[SaveManager] AVISO: save corrompido ({e}). Iniciando novo jogo.")
            self._fazer_backup_corrompido()
            return None

        if not isinstance(dados, dict):
            print("[SaveManager] AVISO: save com formato inválido. Iniciando novo jogo.")
            return None

        # Migra campos ausentes com defaults (tolerância a saves antigos)
        dados = self._preencher_defaults(dados)

        # Migração de versão (reservado para futuro)
        dados = self._migrar_se_necessario(dados)

        if not self.validate(dados):
            print("[SaveManager] AVISO: save com dados inválidos. Iniciando novo jogo.")
            return None

        print(f"[SaveManager] Save carregado — Fase {dados['fase_atual']}, "
              f"Vidas {dados['vidas']}, "
              f"Tempo {dados['tempo_total_jogado']:.0f}s")
        return dados

    def save(self, dados: dict[str, Any]) -> bool:
        """
        Escreve os dados no arquivo de save.

        Estratégia de escrita segura (write-then-replace):
          1. Escreve em arquivo temporário (savegame.tmp)
          2. Valida o JSON escrito (confirmação de integridade)
          3. Substitui o save real atomicamente

        Isso garante que uma queda de energia durante a escrita não
        corrompe o save existente — o .tmp incompleto é simplesmente
        ignorado na próxima execução.

        Retorno
        ───────
        True se salvou com sucesso, False se houve erro de I/O.
        """
        try:
            self._pasta.mkdir(parents=True, exist_ok=True)

            # Garante que versão está presente
            dados_com_versao = {**dados, "versao": VERSAO_SAVE}

            # Escrita em arquivo temporário
            arquivo_tmp = self._arquivo.with_suffix(".tmp")
            with open(arquivo_tmp, "w", encoding="utf-8") as f:
                json.dump(dados_com_versao, f, ensure_ascii=False, indent=2)

            # Substituição atômica
            arquivo_tmp.replace(self._arquivo)

            return True

        except OSError as e:
            print(f"[SaveManager] ERRO ao salvar: {e}")
            return False

    def reset(self) -> bool:
        """
        Apaga o arquivo de save.

        Retorno
        ───────
        True se apagou (ou já não existia), False se houve erro de I/O.
        """
        if not self.exists():
            return True

        try:
            self._arquivo.unlink()
            print("[SaveManager] Save apagado. Novo jogo será iniciado.")
            return True
        except OSError as e:
            print(f"[SaveManager] ERRO ao resetar save: {e}")
            return False

    def validate(self, dados: dict[str, Any]) -> bool:
        """
        Verifica se os dados têm a estrutura mínima necessária.

        Valida:
          • fase_atual é int >= 1
          • vidas é int >= 0
          • tempo_total_jogado é número >= 0
          • checkpoint_x/y são None ou float

        Retorna False se qualquer verificação falhar.
        Não levanta exceção.
        """
        try:
            if not isinstance(dados.get("fase_atual"), int):
                return False
            if dados["fase_atual"] < 1:
                return False

            if not isinstance(dados.get("vidas"), int):
                return False
            if dados["vidas"] < 0:
                return False

            tempo = dados.get("tempo_total_jogado", 0)
            if not isinstance(tempo, (int, float)):
                return False
            if tempo < 0:
                return False

            cp_x = dados.get("checkpoint_x")
            cp_y = dados.get("checkpoint_y")
            if cp_x is not None and not isinstance(cp_x, (int, float)):
                return False
            if cp_y is not None and not isinstance(cp_y, (int, float)):
                return False

            return True

        except (KeyError, TypeError):
            return False

    # ------------------------------------------------------------------
    # HELPERS INTERNOS
    # ------------------------------------------------------------------

    def _preencher_defaults(self, dados: dict[str, Any]) -> dict[str, Any]:
        """
        Completa campos ausentes com os valores default.

        Permite carregar saves de versões anteriores que não tinham
        determinados campos — retrocompatibilidade sem crash.
        """
        resultado = dict(_CAMPOS_DEFAULTS)   # começa com todos os defaults
        resultado.update(dados)              # sobrescreve com o que existe no save
        return resultado

    def _migrar_se_necessario(self, dados: dict[str, Any]) -> dict[str, Any]:
        """
        Migra saves de versões antigas para o formato atual.

        Como usar no futuro:
            versao_save = dados.get("versao", 0)
            if versao_save < 2:
                dados["novo_campo"] = valor_default
                dados["versao"] = 2
            if versao_save < 3:
                ...
        """
        # Versão 1 → 1: nenhuma migração necessária ainda
        dados["versao"] = VERSAO_SAVE
        return dados

    def _fazer_backup_corrompido(self) -> None:
        """
        Renomeia o save corrompido para .bak antes de descartá-lo.

        Útil para debug: o designer pode inspecionar o arquivo .bak
        para entender o que causou a corrupção.
        """
        try:
            backup = self._arquivo.with_suffix(".bak")
            self._arquivo.rename(backup)
            print(f"[SaveManager] Save corrompido renomeado para: {backup}")
        except OSError:
            pass   # se não conseguir renomear, simplesmente ignora
