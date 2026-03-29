"""
One-time script to download and filter the HYG database (version: v4.2), created by David Nash, CC BY-SA-4.0 license.

It creates a derivative dataset 'sky_sim/HYG_Database/hyg_v42_naked_eye.csv' details on 'sky_sim/HYG_Database/HYG_ATTRIBUTION.md'
This repo already contains the derivative dataset, this script does not have to run again, it is kept for reference on the method of creation.

See more info: sky_sim/HYG_Database/HYG_ATTRIBUTION.md
"""


import pandas as pd
from pathlib import Path

HYG_URL = "https://codeberg.org/astronexus/hyg/media/branch/main/data/hyg/CURRENT/hyg_v42.csv.gz"

OUT_DIR = Path(__file__).parent
OUT_DIR.mkdir(parents=True, exist_ok=True)

OUT_CSV = OUT_DIR / "hyg_v42_naked_eye.csv"
OUT_ATTR = OUT_DIR / "HYG_ATTRIBUTION.md"

print("Downloading HYG v4.2 (~15MB compressed)...")
df = pd.read_csv(HYG_URL, compression="gzip", low_memory=False)
print(f"Full dataset: {len(df):,} stars")

df = df[df["mag"] <= 6.5].copy()
cols = ["proper", "mag", "ra", "dec", "con", "bf"]
df = df[cols]
df.to_csv(OUT_CSV, index=False)

print(f"Filtered: {len(df):,} naked-eye stars → {OUT_CSV} ({OUT_CSV.stat().st_size / 1024:.1f} KB)")

# Write CSV with license comment header
comment = (
    "# Source: HYG Database v4.2 by David Nash https://www.astronexus.com/projects/hyg | "
    "License: CC BY-SA 4.0 | "
    "https://creativecommons.org/licenses/by-sa/4.0/ | "
    "Derivative: filtered mag <= 6.5\n"
)
csv_content = OUT_CSV.read_text()
OUT_CSV.write_text(comment + csv_content)

OUT_ATTR.write_text("""\
## Licensing & Attribution

This project uses data from the **HYG Database v4.2**, created by David Nash.

This directory contains hyg_v42_naked_eye.csv which is a derivative work from **HYG Database v4.2**

* **Original Data Source:** [astronexus.com](https://www.astronexus.com/projects/hyg) / [Codeberg Repository](https://codeberg.org/astronexus/hyg)
* **Original License:** [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)
* **Derivative Work:** The file `hyg_v42_naked_eye.csv` is a filtered subset of the original database.
* **Modifications:** Records were filtered to include only stars with a magnitude ≤ 6.5. Columns were reduced to: `proper`, `mag`, `ra`, `dec`, `con`, and `bf`.

**License for this Derivative:**
This derivative dataset is licensed under the [Creative Commons Attribution-ShareAlike 4.0 International License](https://creativecommons.org/licenses/by-sa/4.0/). You are free to share and adapt this material, provided you give appropriate credit and distribute your contributions under the same license.
""")

print(f"Attribution written → {OUT_ATTR}")
print("\nDone!")