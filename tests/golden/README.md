# Golden files

Pixel-exact pictures and data the tests compare against:

| Files | What |
|---|---|
| `widget_*` | The widget in every state |
| `draw_*` | Drawing primitives |
| `setup_*` | Every page of the setup window, light and dark |
| `fake_*` | Waveform characterization |

After an intentional visual change, run `UPDATE_GOLDEN=1 .venv/bin/python -m pytest`. Then **open the new images and check them** before committing.
