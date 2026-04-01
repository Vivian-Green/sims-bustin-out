# The Sims Bustin' Out
<!--[![Build Status]][actions] [![Code Progress]][progress] [![Data Progress]][progress] [![Discord Badge]][discord]
=============-->





<!--
NOT EDITED YET:


<!--
Replace with your repository's URL.
-->
<!--[Build Status]: https://github.com/zeldaret/tww/actions/workflows/build.yml/badge.svg
[actions]: https://github.com/zeldaret/tww/actions/workflows/build.yml
<!--
decomp.dev progress badges
See https://decomp.dev/api for an API overview.
-->
<!--[Code Progress]: https://decomp.dev/zeldaret/tww.svg?mode=shield&measure=code&label=Code
[Data Progress]: https://decomp.dev/zeldaret/tww.svg?mode=shield&measure=data&label=Data
[progress]: https://decomp.dev/zeldaret/tww

[Discord Badge]: https://img.shields.io/discord/727908905392275526?color=%237289DA&logo=discord&logoColor=%23FFFFFF
[Gamecube decompilation discord]: https://discord.gg/hKx3FJJgrV


/NOT EDITED YET
-->






A work-in-progress decompilation of The Sims Bustin' Out for GameCube

This repository does **not** contain any game assets or assembly whatsoever. An existing copy of the game is required.

Supported versions:

- `G4ME69`: Rev 0 (USA)




WARNING: This thing is in a VERY early state, and splits.txt has yet to be mapped properly. It'll *run* with dtk, but it isn't exactly splitting anything into useful files. See ./custom_tools/ to see what work has happened for mapping thus far (it's almost entirely heuristic comparisons to ttyd, and hasn't been reviewed manually at the time of writing this)





Dependencies
============

Windows
--------

On Windows, it's **highly recommended** to use native tooling. WSL or msys2 are **not** required.  
When running under WSL, [objdiff](#diffing) is unable to get filesystem notifications for automatic rebuilds.

- Install [Python](https://www.python.org/downloads/) and add it to `%PATH%`.
  - Also available from the [Windows Store](https://apps.microsoft.com/store/detail/python-311/9NRWMJP3717K).
- Download [ninja](https://github.com/ninja-build/ninja/releases) and add it to `%PATH%`.
  - Quick install via pip: `pip install ninja`

macOS
------

- Install [ninja](https://github.com/ninja-build/ninja/wiki/Pre-built-Ninja-packages):

  ```sh
  brew install ninja
  ```

[wibo](https://github.com/decompals/wibo), a minimal 32-bit Windows binary wrapper, will be automatically downloaded and used.

Linux
------

- Install [ninja](https://github.com/ninja-build/ninja/wiki/Pre-built-Ninja-packages).

[wibo](https://github.com/decompals/wibo), a minimal 32-bit Windows binary wrapper, will be automatically downloaded and used.

Building
========

- Clone the repository:

  ```sh
  git clone https://github.com/my/repo.git
  ```

- Copy your game's disc image to `orig/G4ME69`.
  - Supported formats: ISO (GCM), RVZ, WIA, WBFS, CISO, NFS, GCZ, TGC
  - After the initial build, the disc image can be deleted to save space.

- Configure:

  ```sh
  python configure.py
  ```

  To use a version other than `G4ME69` (USA), specify it with `--version`.

- Build:

  ```sh
  ninja
  ```

Diffing
=======

Once the initial build succeeds, an `objdiff.json` should exist in the project root.

Download the latest release from [encounter/objdiff](https://github.com/encounter/objdiff). Under project settings, set `Project directory`. The configuration should be loaded automatically.

Select an object from the left sidebar to begin diffing. Changes to the project will rebuild automatically: changes to source files, headers, `configure.py`, `splits.txt` or `symbols.txt`.

![](assets/objdiff.png)


Custom tooling
==============

`./custom_tools` has a few scripts I threw together, `function_mapper.py` being the most relevant. mapping.json (I don't recommend opening it directly) and filtered_mapping.json contain likely matches for symbols in [the thousand year door decompilation project](https://github.com/doldecomp/ttyd)
