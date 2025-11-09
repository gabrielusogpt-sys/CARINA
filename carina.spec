# -*- mode: python ; coding: utf-8 -*-
# CARINA Spec File - Versão Completa (com todas as dependências)
from PyInstaller.utils.hooks import collect_all
import sys
import os

# --- Usa os.getcwd() para obter o diretório raiz do projeto ---
project_base = os.getcwd()
print(f"INFO: Project base directory detected as: {project_base}")
# --- Fim ---

# --- Bloco de Coleta Seguro (v7) ---
# Inicializa as listas
all_hiddenimports = []
all_datas = []
all_binaries = []

# Lista de pacotes que precisam de coleta profunda
packages_to_collect = [
    'torch_geometric',
    'captum',
    'pandas',
    'scipy',
    'sklearn',
    'websockets'
]

def _is_valid_spec(item):
    """Verifica se um item está no formato (str, str) que o PyInstaller espera."""
    return (
        isinstance(item, (list, tuple)) and
        len(item) == 2 and
        isinstance(item[0], str) and
        isinstance(item[1], str)
    )

print("INFO: Iniciando coleta profunda de pacotes...")
for package in packages_to_collect:
    try:
        print(f"INFO: Coletando de '{package}'...")
        # Coleta tudo que o pacote precisa
        hi, da, bi = collect_all(package)
        
        # Adiciona os resultados às listas, verificando se não são Nulos
        if hi:
            all_hiddenimports.extend(hi)
        
        # --- CORREÇÃO v7 (ValueError) ---
        # Filtramos agressivamente para incluir APENAS 2-tuplas de strings.
        if da:
            for item in da:
                if _is_valid_spec(item):
                    all_datas.append(item)
                else:
                    print(f"AVISO (data): Ignorando item mal formatado de '{package}': {item}")
        
        if bi:
            for item in bi:
                if _is_valid_spec(item):
                    all_binaries.append(item)
                else:
                    print(f"AVISO (binary): Ignorando item mal formatado de '{package}': {item}")
        # --- Fim da Correção v7 ---

        print(f"INFO: Coleta de '{package}' concluída.")
    except Exception as e:
        print(f"ERRO: Falha ao coletar de '{package}'. Erro: {e}")
        raise # Para o build se a coleta falhar

print("INFO: Coleta profunda de pacotes concluída.")

# --- Adiciona importações manuais (Correções) ---
all_hiddenimports.extend([
    'PySide6.QtSvg',
    'PySide6.QtNetwork',
    # --- CORREÇÃO 1 (Erro do AI Process) ---
    'scipy._lib.array_api_compat.numpy.fft'
])

# --- Adiciona Dados do Projeto (Assets, Configs) ---
all_datas.extend([
    # Assets da UI
    (os.path.join(project_base, 'ui/assets'), 'ui/assets'),
    # Assets de localização da UI
    (os.path.join(project_base, 'ui/locales'), 'ui/locales'),
    # Assets de localização do Backend
    (os.path.join(project_base, 'src/locale_backend'), 'locale_backend'),
    # Arquivo de Configuração
    (os.path.join(project_base, 'config/settings.ini'), 'config')
])
# --- Fim da Coleta ---


# 4. Hooks de Runtime:
# O hook personalizado para adicionar 'src' ao sys.path.
runtime_hooks = [os.path.join(project_base, 'src/hooks/pyi_runtime_hooks.py')]

a = Analysis(
    ['carina.py'], # Script principal na raiz
    
    pathex=[project_base], # Adiciona a raiz do projeto ao path de análise
    
    # Passa as listas filtradas e corretas
    binaries=all_binaries,
    datas=all_datas,
    hiddenimports=all_hiddenimports,
    
    hookspath=[],
    hooksconfig={},
    runtime_hooks=runtime_hooks, # Hook está em src/hooks
    
    # --- CORREÇÃO 2 (Erro do netconvert / GLIBCXX) ---
    # Exclui a biblioteca C++ do build. O programa usará a
    # biblioteca do sistema Ubuntu, resolvendo o conflito.
    excludes=['libstdc++.so.6'],
    # --- FIM DA CORREÇÃO 2 ---
    
    noarchive=False, # Manter False pode ajudar com spawn
    optimize=0, # Manter 0 durante debug
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='carina', # Nome final do executável
    debug=False, # Mudar para True se precisar de mais debug do PyInstaller
    bootloader_ignore_signals=False,
    strip=False,
    upx=False, # UPX Desativado (recomendado para debug e compatibilidade)
    console=True, # Mantém console visível
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # Caminho do ícone relativo à raiz (onde o .spec está)
    icon=os.path.join('ui', 'assets', 'images', 'logo.png')
)

# --- Bloco de Coleta e Agrupamento (Inalterado) ---
# Adiciona os binários e dados coletados ao executável final.
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False, # UPX Desativado
    upx_exclude=[],
    name='carina' # Nome da pasta final em 'dist/'
)