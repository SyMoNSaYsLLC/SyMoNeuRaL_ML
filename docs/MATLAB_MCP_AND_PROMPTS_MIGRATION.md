# MATLAB MCP Server and Prompt Library Migration

This update integrates two MATLAB ecosystem projects into SyMoNeuRaL without replacing the production LLM/image engines.

## Added vendor folders

- `matlab/vendor/mathworks-matlab-mcp-server/`
- `matlab/vendor/mathworks-ai-coding-prompts/`

These are intentionally kept under `matlab/vendor/` and marked as vendored for GitHub language statistics.

## Why these do not replace existing engines

`engines/symon-llm.cpp` remains the production local LLM server.

`engines/symon-image.cpp` remains the production local image generation server.

`matlab/vendor/mathworks-matlab-mcp-server` adds a MATLAB tool bridge for MCP-capable assistants. It gives an agent a controlled way to start MATLAB, run MATLAB code, and evaluate MATLAB workflows.

`matlab/vendor/mathworks-ai-coding-prompts` adds a curated prompt library for MATLAB development workflows. It is a research/development accelerator, not a runtime engine.

## Project-owned additions

- `scripts/build_matlab_mcp_server.sh`
- `scripts/write_matlab_mcp_vscode_config.sh`
- `scripts/list_matlab_prompts.sh`
- `matlab/+symon/projectRoot.m`
- `matlab/+symon/mcpServerPath.m`
- `matlab/+symon/listPrompts.m`

## Build MATLAB MCP Server

From the repo root:

```bash
./scripts/build_matlab_mcp_server.sh
```

This requires Go to be installed. The output binary is:

```text
bin/matlab-mcp-server
```

## Write VS Code MCP config

After building the binary:

```bash
./scripts/write_matlab_mcp_vscode_config.sh
```

This writes:

```text
.vscode/mcp.json
```

The config points VS Code/GitHub Copilot MCP support at the project-local MATLAB MCP server binary.

## List MATLAB prompts

```bash
./scripts/list_matlab_prompts.sh
```

Inside MATLAB:

```matlab
symon.addPaths
prompts = symon.listPrompts
server = symon.mcpServerPath
```

## License notes

The MATLAB MCP Server license includes a MathWorks-use condition. Keep it in the MATLAB vendor layer and do not port its code into SyMoNeuRaL's Python/Rust/C++ runtime.

The AI coding prompts are licensed under Creative Commons Attribution 4.0. Keep attribution and license files with the vendored prompt library.
