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

# --- Coleta informações do PyTorch e NumPy ---
torch_collected = collect_all('torch')
numpy_collected = collect_all('numpy')
print(f"INFO: Torch collected   - Data: {len(torch_collected[0])}, Binaries: {len(torch_collected[1])}, Hidden: {len(torch_collected[2])}")
print(f"INFO: NumPy collected   - Data: {len(numpy_collected[0])}, Binaries: {len(numpy_collected[1])}, Hidden: {len(numpy_collected[2])}")
# --- Fim da coleta ---

# --- Define os dados a serem copiados (relativos à raiz do projeto) ---
datas = [
    ('src', 'src'),                    # Código fonte principal
    ('config', 'config'),               # Arquivos de configuração (.ini)
    ('ui', 'ui'),                       # Código e ativos da UI (inclui locales da UI, assets)
    ('src/locale_backend', 'src/locale_backend'), # Locales do Backend
    
    # --- Linhas REMOVIDAS/Comentadas ---
    # Não precisamos copiar manually, 'hiddenimports' deve tratar disso.
    # (os.path.join(site_packages_path, 'torch_geometric'), 'torch_geometric'),
    # (os.path.join(site_packages_path, 'xxhash'), 'xxhash'),
 
    # Adiciona dados coletados automaticamente
]
datas += torch_collected[0] # Adiciona dados do PyTorch
datas += numpy_collected[0] # Adiciona dados do NumPy
print(f"INFO: Defined datas (Total {len(datas)}): {datas}") # Log para verificar
# --- Fim da definição de datas ---

# --- Define as importações ocultas ---
# Lista principal de módulos que PyInstaller pode não encontrar
needed_hiddenimports = [
    # Base
    'logging', 'configparser', 'datetime', 'time', 'traceback', 'multiprocessing',
    'json', 'os', 'sys', 'xxhash', 'subprocess', 'shutil', 'math', 'random',
    'collections', 'gzip', 'xml.etree', 'xml.etree.ElementTree', 'xml.etree.cElementTree',
    'warnings', '__future__', 'pkgutil', 'platform', 'encodings', 'operator', 'inspect',

   
 # Grupo 1 (Python Puras/Comuns)
    'websockets', 'prometheus_client', 'psutil', 'queue', 'threading', 'sqlite3', 'asyncio',

    # Grupo 2 (Bibliotecas com Extensões C)
    'numpy', 'pandas', 'scipy', 'scipy.special', 'scipy.linalg', 'sklearn',
    'sklearn.utils._weight_vector', 'pkg_resources.py2_warn',

    # Grupo 3 (Gráficos)
    'matplotlib', 'matplotlib._path', 'matplotlib.backends.backend_agg', 'PIL', # PIL pode ser necessário para matplotlib
    'colorsys', 'tkinter', # Tkinter pode ser dependência implícita

    # Grupo 4 (ML e Relacionados)
    'tensorboard', 'captum', 'torch_geometric', # torch_geometric já está aqui
    'sumolib', # Essencial para SUMO
 
    'flet', # Framework da UI

    # Submódulos específicos que podem falhar
    'torch._dynamo', 'torch.jit', 'torch._C',
    'pandas._libs.tslibs.timedeltas', # Exemplo de submódulo pandas
]
# Combina hiddenimports coletados com os definidos, evitando duplicatas
hiddenimports = list(set(torch_collected[2] + numpy_collected[2] + needed_hiddenimports))
print(f"INFO: Defined hiddenimports (Total {len(hiddenimports)}): {hiddenimports}") # Log para verificar
# --- Fim das importações ocultas ---

# Combina os binários coletados
binaries = torch_collected[1] + numpy_collected[1]
print(f"INFO: Defined binaries (Total {len(binaries)}): {binaries}") # Log para verificar

# Define o hook de runtime
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
    excludes=[],
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
    icon=os.path.join('ui', 'assets', 'images', 'logo.png'),
)
coll = COLLECT(
    exe,
    a.binaries, # Inclui binários coletados (torch, numpy)
    a.zipfiles,
    a.datas, # Inclui todos os dados copiados (src, config, ui, torch, numpy, etc.)
    strip=False,
    upx=False,
    upx_exclude=[],
    name='carina', # Nome da pasta de saída em dist/
)