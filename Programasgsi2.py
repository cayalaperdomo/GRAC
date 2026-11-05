# coding: utf-8
"""Arkyntech GRAC — arranque modular para Render (512 MB).

El código de GRAC permanece idéntico en grac_parts/*.py.
Cada bloque ejecuta sobre este mismo diccionario global, por lo que Flask,
modelos, rutas, permisos y clases mantienen sus nombres originales.
Los .pyc de los bloques se generan DURANTE el build de Render, no al arrancar.
NO BORRAR el directorio grac_parts: es parte de la aplicación.
"""
import os as _grac_v3_os
import sys as _grac_v3_sys
import time as _grac_v3_time
import importlib.machinery as _grac_v3_machinery
from pathlib import Path as _GRAC_V3_Path

# Límites para hilos BLAS y asignadores, antes de cargar NumPy u otros paquetes.
for _grac_v3_key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS',
                     'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_MAX_THREADS'):
    _grac_v3_os.environ[_grac_v3_key] = '1'
_grac_v3_os.environ.setdefault('MALLOC_ARENA_MAX', '2')
_grac_v3_os.environ.setdefault('MALLOC_TRIM_THRESHOLD_', '65536')
_grac_v3_os.environ.setdefault('MPLBACKEND', 'Agg')

def _grac_v3_rss_mb():
    try:
        with open('/proc/self/statm', encoding='ascii') as _f:
            _pages = int(_f.read().split()[1])
        return round(_pages * _grac_v3_os.sysconf('SC_PAGE_SIZE') / 1048576, 1)
    except (OSError, ValueError, IndexError):
        return 0.0

def _grac_v3_cgroup_mb():
    for _p in ('/sys/fs/cgroup/memory.current', '/sys/fs/cgroup/memory/memory.usage_in_bytes'):
        try:
            with open(_p, encoding='ascii') as _f:
                return round(int(_f.read().strip()) / 1048576, 1)
        except (OSError, ValueError):
            pass
    return 0.0

_GRAC_V3_parts = _GRAC_V3_Path(__file__).resolve().parent / 'grac_parts'
_GRAC_V3_files = sorted(_GRAC_V3_parts.glob('part_[0-9][0-9][0-9].py'))
if not _GRAC_V3_files:
    raise RuntimeError('GRAC: faltan los archivos de grac_parts; extrae el ZIP completo.')
_grac_v3_trace = _grac_v3_os.environ.get('GRAC_RAM_TRACE_STARTUP','1') != '0'
_grac_v3_begin = _grac_v3_time.monotonic()
if _grac_v3_trace:
    print('GRAC-RAM-V3 inicio bloques=%s rss=%.1fMB contenedor=%.1fMB' %
          (len(_GRAC_V3_files),_grac_v3_rss_mb(),_grac_v3_cgroup_mb()), flush=True)
for _grac_v3_num, _grac_v3_file in enumerate(_GRAC_V3_files,1):
    if _grac_v3_trace:
        print('GRAC-RAM-V3 iniciando bloque=%02d/%02d rss=%.1fMB contenedor=%.1fMB' %
            (_grac_v3_num,len(_GRAC_V3_files),_grac_v3_rss_mb(),_grac_v3_cgroup_mb()),flush=True)
    _grac_v3_loader=_grac_v3_machinery.SourceFileLoader('_grac_v3_chunk_'+str(_grac_v3_num),str(_grac_v3_file))
    _grac_v3_code=_grac_v3_loader.get_code('_grac_v3_chunk_'+str(_grac_v3_num))
    exec(_grac_v3_code,globals(),globals())
    del _grac_v3_loader,_grac_v3_code
    if _grac_v3_trace:
        print('GRAC-RAM-V3 terminado bloque=%02d/%02d rss=%.1fMB contenedor=%.1fMB' %
              (_grac_v3_num,len(_GRAC_V3_files),_grac_v3_rss_mb(),_grac_v3_cgroup_mb()),flush=True)
if _grac_v3_trace:
    print('GRAC-RAM-V3 LISTO tiempo=%.1fs rss=%.1fMB contenedor=%.1fMB' %
          (_grac_v3_time.monotonic()-_grac_v3_begin,_grac_v3_rss_mb(),_grac_v3_cgroup_mb()),flush=True)

# Registro mínimo del INICIO de cada solicitud. Si Render mata al proceso dentro
# de un reporte, la última línea GRAC-RAM-IN identifica la función que estaba
# ejecutándose, incluso cuando no llega a producir respuesta.
if _grac_v3_os.environ.get('GRAC_RAM_TRACE_REQUESTS', '1') != '0':
    @app.before_request
    def _grac_v3_memory_request_start():
        print('GRAC-RAM-IN endpoint=%s rss=%.1fMB contenedor=%.1fMB' % (
              request.endpoint or '?',_grac_v3_rss_mb(),_grac_v3_cgroup_mb()),flush=True)

# Gunicorn obtiene app directamente: Programasgsi2:app
