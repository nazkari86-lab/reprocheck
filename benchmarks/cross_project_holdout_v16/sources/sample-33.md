# Particle Experiments and Validation

This appendix preserves two isolated PoCs. `!pspeed` validates rate-limited numeric HUD updates; `!patlas` validates live sequence selection from one VTEX. Neither shares sessions, commands, configuration, or resources with the production `!pmenu` or `!ptext` paths.

## `!pspeed`: standalone numeric HUD

Enter `!pspeed` while alive to display horizontal velocity in units per second; enter it again or press `R`/`Esc` to close. `config/runtime/dynamic_text_demo.json` independently controls `X`, `Y`, `Scale`, `UpdateIntervalMs` and `MaximumDisplayValue`. `pspeed_layout <x> <y> <scale>` adjusts an open panel; edit JSON then use `pspeed_layout reload` to persist.

The server calculates `sqrt(x²+y²)`, rounds away from zero, clamps to `0–9999`, samples at most every 100ms, and writes only changed values. CP16.x/y/z carry thousands/hundreds/tens, CP33.z carries ones, CP33.x/y and CP34.x carry placement/scale, and CP17.x/y carry lifetime/alpha. Leading blanks use `10`, so a `0–9` selector tree stays transparent. One open demo is one network entity with a panel and `4×10` selectors; updates change four CP components only. `src/DynamicTextDemo.cs` owns its transmit filtering, sampling, buttons and cleanup. Preview: `build/previews/dynamic_text_demo.png`.

## `!patlas`: sequence-atlas PoC

`!patlas` asks whether a live particle can continuously copy networked CP values to `PARTICLE_ATTRIBUTE_SEQUENCE_NUMBER` (attribute 9) and select glyphs from one VTEX. Its topology is one panel, one shared `0–9 + blank(10)` VTEX, one network root and four glyph slots. Each slot uses `C_OP_SetFloat` with `m_nOutputField = 9`: slots 1–3 read CP16.x/y/z and slot 4 reads CP33.z. CP33.xy, CP34.x and CP17.xy remain placement, scale, lifetime and alpha.

`config/runtime/particle_atlas_poc.json` owns `{ "X": 0, "Y": 0, "Scale": 0.45 }`; use `patlas_layout <x> <y> <scale>` live and `patlas_layout reload` after editing. The expected test sequence is `0123`, increments every 750ms through `9012`, one blank step, then repeats without respawning the entity. It is owner-only. A pass proves that a four-digit display can shrink from `1 + 4×10 = 41` to `1 + 4 = 5` particle systems. If it stays at `0123`, inspect live attribute-9 mapping; identical slots indicate CP mapping; invisible digits indicate MKS metadata, dimensions, or renderer animation; flicker indicates sequence duration/animation settings.

Key files: `src/ParticleAtlasPoc.cs`, `src/ParticleAtlasPocConfig.cs`, `config/runtime/particle_atlas_poc.json`, and `tools/templates/particles/particle_ui_atlas_*`. ResourceCompiler validates the 11-sequence DXT5 atlas; in-game testing validates live switching and sampling quality.
