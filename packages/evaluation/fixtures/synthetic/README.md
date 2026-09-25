# Synthetic contract fixtures

Run `python3.12 generate.py` from this directory to regenerate four tiny grayscale PNGs and their manifest. `python3.12 generate.py --check` verifies byte-for-byte reproducibility. The images are simple generated marks, not real sketches or accuracy evidence. `ground_truth.json` supplies expected connectivity, note text, and dimension fields; `transforms.json` supplies coordinate-space examples.
