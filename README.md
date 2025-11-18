# Antimatter Dimensions Dimboost Optimizer

**[Web viewer](https://menelajjj.github.io/ad-dimboost-optimizer/)** + source code for optimal dimboost strategies for Antimatter Dimensions game ([PC](https://ivark.github.io/AntimatterDimensions/) / [mobile](https://play.google.com/store/apps/details?id=kajfosz.antimatterdimensions)).

## Contents

- `docs/` - Web interface (HTML/JS)
    - `docs/Saved_Runs/` - Pre-computed strategy files
- `scripts/` - Windows batch scripts
- `src/` - Python/C++ optimization code

## Usage

Pre-computed strategy files are included in the repository. If you need to regenerate them:

- **Recalculate all strategies**: Run `src/update_all.py` or `scripts/update_all.bat`
- **Test individual strategies**: See examples in `src/test.py`
