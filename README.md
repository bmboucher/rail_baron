# pyrailbaron

An electronic implementation of the classic board game **Rail Baron**,
spanning a Python game engine, a touchscreen GUI, a CAD-derived map
pipeline, and custom hardware (Teensy firmware + PCB) for a physical
board with LED indicators.

## Components

| Path        | What it is                                                        |
|-------------|-------------------------------------------------------------------|
| `python/`   | The `pyrailbaron` package: game rules, AI, pygame GUI, and CLI.   |
| `python/src/pyrailbaron/game/`  | Core game loop, state model, AI, fees, and per-screen GUI. |
| `python/src/pyrailbaron/map/`   | Map ETL: parses railroad geometry from DXF CAD files, fits/simplifies paths, and renders SVG maps. |
| `python/src/pyrailbaron/teensy/`| Serial protocol used to drive the physical board's LEDs/displays. |
| `teensy/`   | PlatformIO firmware (C++) for the Teensy microcontroller, incl. a TM1637 7-segment driver. |
| `pcb/`      | EAGLE schematic/board files ("tophat") for the custom control PCB. |
| `data/`     | Map data: city labels, region borders, payoff & roll tables, DXF sources, generated `map.json`. |

## Quick start (software game)

```bash
cd python
python -m venv .venv
source .venv/bin/activate      # .\.venv\Scripts\Activate.ps1 on Windows
pip install -e .
railbaron                       # console entry point (pyrailbaron.game.main)
```

Requires Python 3.x with `pygame >= 2.0`. Other dependencies
(`ezdxf`, `svgwrite`, `numpy`, `sklearn`, `dataclasses-json`) are in
`python/requirements.txt` and are used mainly by the map ETL scripts.

## Map pipeline

The board map is built from DXF CAD exports in `data/dxf/`. Scripts in
`python/scripts/` (e.g. `scrape_dxf.py`, `simplify_rr_paths.py`) extract
and simplify each railroad's geometry; the `pyrailbaron.map` package fits
coordinates, draws state/region borders, and emits SVG + `map.json`.

## Hardware

The physical board uses a Teensy microcontroller (firmware in `teensy/`,
built with PlatformIO) on a custom PCB (`pcb/tophat.*`, EAGLE format).
The Python game talks to the board over a simple serial protocol defined
in `pyrailbaron/teensy/serial.py` (active-player LED, region/destination
highlights, bank/ownership displays).

## License

GPL — see [LICENSE](LICENSE).
