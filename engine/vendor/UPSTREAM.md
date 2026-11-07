# Upstream source

- Repository: https://github.com/gnipbao/whiteboard-video-engine
- Commit: `86848ea27077c1902950bf4e7e37e02d4bfbd1a3`
- Retrieved: 2026-11-06
- Unmodified files: `__init__.py`, `models.py`, `styles.py`, `preprocess.py`, `whiteboard.py`, `assets/hands/*.png` from `src/whiteboard_skill/`.
- License: MIT, included as LICENSE.whiteboard-video-engine; upstream third-party notices included alongside it.
- Adapter uses stroke/timeline geometry helpers, hand cursors, fill blending and frame streaming helpers. SVG parsing is performed by installed Chrome/Edge rather than upstream's incomplete SVG parser.
- Uses private upstream functions; keep this commit pinned and run integration tests when changing it.
- Sprite files have no separate license notice in the checked source tree; repository MIT license is retained. Review asset rights separately before external redistribution. Current build is for the user's local use.
- No upstream image generation, TTS, cloud providers, sample artwork or model weights are bundled or invoked.
