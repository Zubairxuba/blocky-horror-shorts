# Third-party notices

- `skills/blocky-horror-shorts/engine/short_qa.py` and the `push_in` lens-creep helper in `engine/characters.py`
  are adapted from [mromidev/claude-animated-shorts](https://github.com/mromidev/claude-animated-shorts),
  MIT License, Copyright (c) 2026 mromidev. That project's MIT license text applies to those portions.
- 3D models, textures and the HDRI are NOT in this repo. `engine/assets.py` downloads them from
  [Poly Haven](https://polyhaven.com) (CC0 1.0, public domain) and writes `engine/assets/LICENSES.txt` with each source.
- Sound effects are synthesized at run time with ffmpeg (no recorded audio is included).
- Voice: Chatterbox ([resemble-ai/chatterbox](https://github.com/resemble-ai/chatterbox), MIT) is installed by the user;
  no voice reference audio is included. Only clone a voice you own or have permission to use.
