# SyMoNeuRaL Language Plan

SyMoNeuRaL is a multi-language system.

Current ownership:

- C/C++: owned local engines
- Python: API, orchestration, AI routing, tools
- Rust: future daemon/runtime/control plane
- MATLAB: modeling, simulation, benchmark analysis
- Swift: future Apple client
- PHP: optional admin/web/plugin integration
- HTML/CSS/JS: simple web chat UI

The C++ engines are intentionally vendored but marked as vendored in `.gitattributes` so GitHub language stats show the application layers more accurately.
