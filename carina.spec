# -*- mode: python ; coding: utf-8 -*-
# CARINA Spec File - Versão Completa (com todas as dependências)
from PyInstaller.utils.hooks import collect_all
import sys
import os

# --- Usa os.getcwd() para obter o diretório raiz do projeto ---
project_base = os.getcwd()
print(f"INFO: Project base directory detected as: {project_base}")
# --- Fim ---

# --- Bloco do venv/site-packages REMOVIDO/Comentado ---
# O build do Docker instala pacotes globalmente, não em um venv.
# Não precisamos mais desse bloco, pois 'hiddenimports' cuidará disso.
# venv_path = os.path.join(project_base, 'venv')
# python_version_major_minor = f'python{sys.version_info.major}.{sys.version_info.minor}'
# site_packages_path = os.path.join(venv_path, 'lib', python_version_major_minor, 'site-packages')
# if not os.path.exists(site_packages_path):
#     print(f"AVISO: Caminho site-packages não encontrado automaticamente em {site_packages_path}. Verifique a estrutura do venv.")
#     # Defina um caminho fixo aqui se necessário, ou ajuste a lógica se o venv estiver em 
# outro lugar
#     # Exemplo: site_packages_path = '/path/to/your/venv/lib/pythonX.Y/site-packages'
# else:
#      print(f"INFO: Usando site-packages de: {site_packages_path}")
# --- Fim ---


# --- Definição dos Pacotes e Bibliotecas ---

# 1. Binários:
# Bibliotecas .so cruciais que o PyInstaller pode não encontrar.
# (libmpv.so.1 é necessário para o player de vídeo python-mpv)
binaries = [
    ('/usr/lib/x86_64-linux-gnu/libmpv.so.1', '.'),
    ('/usr/lib/x86_64-linux-gnu/libmpv.so.2', '.')
]

# 2. Dados:
# Inclui todos os assets da UI (ícones, logos, fontes) e
# todos os arquivos de localização (.json).
datas = [
    # Assets da UI
    (os.path.join(project_base, 'ui/assets'), 'ui/assets'),
    # Assets de localização da UI
    (os.path.join(project_base, 'ui/locales'), 'ui/locales'),
    # Assets de localização do Backend
    (os.path.join(project_base, 'src/locale_backend'), 'locale_backend'),
    # Arquivo de Configuração
    (os.path.join(project_base, 'config/settings.ini'), 'config')
]

# 3. Importações Ocultas (Hidden Imports):
# A parte MAIS IMPORTANTE. Diz ao PyInstaller quais módulos 
# ele deve incluir, mesmo que não os encontre estaticamente.
# Isso corrige a maioria dos erros "No module named '...'".
hiddenimports = collect_all('torch_geometric')[0] + \
                collect_all('captum')[0] + \
                collect_all('pandas')[0] + \
                collect_all('scipy')[0] + \
                collect_all('sklearn')[0] + \
                collect_all('websockets')[0] + \
                ['PySide6.QtSvg', 'PySide6.QtNetwork', 
                 # --- CORREÇÃO 1 (Erro do AI Process) ---
                 # Adiciona o submódulo 'fft' do scipy que faltava
                 'scipy._lib.array_api_compat.numpy.fft'
                ]

# 4. Hooks de Runtime:
# O hook personalizado para adicionar 'src' ao sys.path.
runtime_hooks = [os.path.join(project_base, 'src/hooks/pyi_runtime_hooks.py')]

a = Analysis(
    ['carina.py'], # Script principal na raiz
    
    pathex=[project_base], # Adiciona a raiz do projeto ao path de análise
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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