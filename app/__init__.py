"""app — FastAPI application package for AnnoABSA.

Currently all code lives in ``main.py``. This scaffolding defines the target
module structure for a future breakup. When ready, move code here one module
at a time, then rewire ``main.py`` to import and mount from ``app``.

Submodules:
    config      — global state (DATA_FILE_PATH, CONFIG_DATA, etc.) + config functions
    data        — data I/O (load_data, save_data, parse_triplet_column, _load_comparison_csv)
    positions   — auto_add_missing_positions
    routes/     — endpoint handlers (one file per concern group)
"""
