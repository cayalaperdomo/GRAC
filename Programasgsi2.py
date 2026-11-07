# Arkyntech GRAC - entrada modular para Render (bajo consumo).
# Generado desde Programasgsi2(20261107-021916).py sin eliminar rutas.
# Todas las partes ejecutan en ESTE modulo y comparten los mismos globals().
from pathlib import Path as _GRAC_Path
import importlib.util as _grac_importlib_util
import marshal as _grac_marshal
import os as _grac_os
import sys as _grac_sys

_GRAC_PARTS_DIR = _GRAC_Path(__file__).resolve().parent / "grac_parts"
_GRAC_PART_FILES = sorted(_GRAC_PARTS_DIR.glob("part_[0-9][0-9][0-9].py"))
if len(_GRAC_PART_FILES) != 25:
    raise RuntimeError("GRAC incompleto: faltan archivos grac_parts/part_*.py. Suba el ZIP DESCOMPRIMIDO a la raiz de GitHub.")

def _grac_loader_rss():
    try:
        with open('/proc/self/status', 'r', encoding='ascii') as fh:
            for line in fh:
                if line.startswith('VmRSS:'):
                    return round(int(line.split()[1]) / 1024, 1)
    except Exception:
        return None

_GRAC_LOG_LOADING = _grac_os.getenv('GRAC_RAM_LOG', '0').strip().lower() in ('1','true','yes','on')
for _grac_part_file in _GRAC_PART_FILES:
    _grac_cache = _grac_importlib_util.cache_from_source(str(_grac_part_file))
    if _grac_os.path.isfile(_grac_cache):
        try:
            with open(_grac_cache, "rb") as _grac_pyc:
                _grac_pyc.read(16)  # cabecera .pyc de CPython 3.11
                _grac_code = _grac_marshal.load(_grac_pyc)
        except Exception:
            _grac_code = compile(_grac_part_file.read_bytes(), str(_grac_part_file), "exec")
    else:
        _grac_code = compile(_grac_part_file.read_bytes(), str(_grac_part_file), "exec")
    exec(_grac_code, globals())
    del _grac_code
    if _GRAC_LOG_LOADING:
        print('[GRAC-RAM-LOAD] part=%s rss_mb=%s' % (_grac_part_file.name, _grac_loader_rss()), flush=True)

# app, db, rutas y blueprints se definen en las partes precedentes.
