"""Owner-only research report adapter; no runtime toggles or weight writes."""
from functools import lru_cache
import importlib
import importlib.util
from pathlib import Path
import os
import sys

ROOT=Path(__file__).resolve().parents[4]


@lru_cache(maxsize=1)
def reader():
    name='_atlas_edge_runtime'
    spec=importlib.util.spec_from_file_location(name,ROOT/'atlas_edge/__init__.py',submodule_search_locations=[str(ROOT/'atlas_edge')])
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return importlib.import_module(name+'.status').status


def overview():
    return reader()(os.getenv('ATLAS_EDGE_V3_REPORT'))
