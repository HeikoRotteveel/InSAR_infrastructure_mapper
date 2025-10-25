InSAR Mapper
---
This small Python tool is designed to **filter and visualize InSAR target data** on an interactive map. It runs completely from the terminal and produces:

- An **HTML map** you can open in a browser.
- A **GeoJSON file** containing all filtered points that can be used for further analysis in GIS tools.

---

## Installation

1. Clone the repository:

```bash
git clone https://github.com/HeikoRottebeel/InSAR_infrastructure_mapper
cd InSAR_infrastructure_mapper
```

2. Create a virtual environment (recommended):
```
python -m venv venv
source venv/bin/activate      # Linux/Mac
venv\Scripts\activate         # Windows
```

3. Install dependencies:
```
pip install -r requirements.txt
```

## Usage
You can run the script entirely from the terminal. At a minimum, you must provide the Excel file with your InSAR target data.

Basic usage (with default filters):

```
python insar_mapper.py --file InSAR_designated_Target_Database.xlsx
```
This will:

- Filter only active, valid InSAR targets
- Filter for countries NLD and BEL
- Filter for instrument classes CR, IGRS, TR
- Save an HTML map (insar_map.html) and GeoJSON (insar_points.geojson)

Different arguments that can be used:

| Argument           | Description                                                         | Default |
|-------------------|---------------------------------------------------------------------|---------|
| `--file`          | Path to the InSAR Excel database file (required)                    | None    |
| `--countries`     | Country codes to filter (multiple allowed)                          | NLD BEL |
| `--owners`        | Owners to filter (multiple allowed)                                 | None    |
| `--instrClass`    | Instrument classes to filter (multiple allowed)                     | CR IGRS TR |
| `--strict`        | Strict filtering for instrument classes (`True` or `False`)         | False   |
| `--active`        | Only include active targets                                         | True    |
| `--valid`         | Only include valid entries (`valid == True`)                        | True    |
| `--background`    | Map tiles from: https://leaflet-extras.github.io/leaflet-providers/preview/) | Cartodb Positron |
| `--map-title`     | Title displayed at the top of the map                               | InSAR Target Locations |
| `--save-html`     | Output HTML filename for the interactive map                        | insar_map.html |
| `--save-geojson`  | Output GeoJSON filename for points                                  | insar_points.geojson |
---

## Examples

Filter only one owner and one site:
```
python insar_mapper.py --file InSAR_designated_Target_Database.xlsx --owners TUD --siteId Delft
```

Use strict instrument class filtering:

```
python insar_mapper.py --file InSAR_designated_Target_Database.xlsx --instrClass CR IGRS --strict True
```

Change the map background and title:

```
python insar_mapper.py --file InSAR_designated_Target_Database.xlsx --background "Stamen Terrain" --map-title "My Custom InSAR Map"
```

