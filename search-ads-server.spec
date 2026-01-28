# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Search-ADS server sidecar.

Build with: pyinstaller search-ads-server.spec
"""

import sys
from pathlib import Path

# Get the project root directory
project_root = Path(SPECPATH)

from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = []

# Collect dependencies
for pkg in ['chromadb', 'onnxruntime', 'tokenizers', 'sentence_transformers', 'certifi']:
    try:
        tmp_ret = collect_all(pkg)
        datas += tmp_ret[0]
        binaries += tmp_ret[1]
        hiddenimports += tmp_ret[2]
    except Exception:
        pass

a = Analysis(
    ['src/server_entry.py'],
    pathex=[str(project_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports + [
        # FastAPI and Starlette
        'fastapi',
        'starlette',
        'starlette.routing',
        'starlette.middleware',
        'starlette.middleware.cors',
        'starlette.responses',
        'starlette.requests',
        'starlette.staticfiles',
        'starlette.templating',

        # Uvicorn
        'uvicorn',
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.http.h11_impl',
        'uvicorn.protocols.http.httptools_impl',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'uvicorn.lifespan.off',

        # HTTP tools
        'httptools',
        'h11',
        'websockets',
        'watchfiles',
        'uvloop',

        # Pydantic
        'pydantic',
        'pydantic.fields',
        'pydantic_settings',
        'pydantic_core',
        'pydantic_core._pydantic_core',

        # SQLModel and SQLAlchemy
        'sqlmodel',
        'sqlalchemy',
        'sqlalchemy.sql.default_comparator',
        'sqlalchemy.ext.asyncio',
        'sqlalchemy.dialects.sqlite',

        # Multipart
        'python_multipart',
        'multipart',

        # ChromaDB
        'chromadb',
        'chromadb.api',
        'chromadb.config',
        'chromadb.db',
        'chromadb.db.impl',
        'chromadb.db.impl.sqlite',
        'chromadb.segment',
        'chromadb.telemetry',
        'chromadb.telemetry.posthog',
        'onnxruntime',
        'tokenizers',

        # OpenAI and Anthropic
        'openai',
        'openai._client',
        'anthropic',

        # PDF
        'fitz',
        'pymupdf',

        # ADS
        'ads',

        # Rich and Typer (for CLI compatibility)
        'typer',
        'rich',
        'rich.console',
        'rich.progress',
        'rich.table',

        # Utilities
        'dotenv',
        'requests',
        'httpx',
        'anyio',
        'anyio._backends._asyncio',
        'sniffio',
        'certifi',
        'charset_normalizer',
        'idna',
        'urllib3',

        # Email (sometimes needed by pydantic)
        'email_validator',

        # JSON
        'orjson',

        # Async
        'asyncio',
        'concurrent.futures',

        # Our app modules
        'src',
        'src.web',
        'src.web.main',
        'src.web.routers',
        'src.web.routers.papers',
        'src.web.routers.projects',
        'src.web.routers.citations',
        'src.web.routers.notes',
        'src.web.routers.search',
        'src.web.routers.import_',
        'src.web.routers.pdf',
        'src.web.routers.settings',
        'src.web.routers.ai',
        'src.web.routers.latex',
        'src.web.schemas',
        'src.web.dependencies',
        'src.core',
        'src.core.config',
        'src.core.ads_client',
        'src.core.llm_client',
        'src.core.pdf_handler',
        'src.core.citation_engine',
        'src.core.latex_parser',
        'src.db',
        'src.db.models',
        'src.db.repository',
        'src.db.vector_store',
        'src.cli',
        'src.cli.main',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'PIL',
        'numpy.distutils',
        'test',
        'tests',
    ],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='search-ads-server',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='search-ads-server',
)
