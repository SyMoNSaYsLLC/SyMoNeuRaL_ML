# MATLAB Tool Migration: Overlaps and Boundaries

This migration brings two MathWorks MATLAB projects into SyMoNeuRaL as MATLAB-layer tools.

## Migrated tools

### `matlab/vendor/mathworks-llms-with-matlab`

Purpose:

- MATLAB client for OpenAI-compatible APIs
- OpenAI/Azure/Ollama chat from MATLAB
- structured output
- tool calling
- embeddings and image API helpers

SyMoNeuRaL use:

- MATLAB can talk to the local SyMoNeuRaL/llama.cpp OpenAI-compatible engine at `http://127.0.0.1:8080/v1`
- MATLAB can also call the SyMoNeuRaL manager API through `symon.managerSubmit`

Overlap:

- Overlaps with Python FastAPI only at the API-client level.
- Does not replace the Python backend.
- Does not replace `app/services/process_manager.py`.
- Does not replace the simple web chat frontend.
- It is best treated as a MATLAB client/research interface.

### `matlab/vendor/mathworks-image-classifier-app`

Purpose:

- MATLAB App Designer image classification training app
- transfer learning workflow
- dataset import/augmentation
- explainability workflows such as Grad-CAM/LIME when toolboxes are available

SyMoNeuRaL use:

- MATLAB-side image classification, labeling, model-training, and explainability experiments.
- Useful for future vision classifier or dataset pipeline planning.

Overlap:

- Does not replace `engines/symon-image.cpp`.
- `symon-image.cpp` is image generation/inference.
- Image Classifier App is classification/training/explainability.
- It complements the image worker rather than replacing it.

## Important license boundary

Both migrated tools preserve their original MathWorks license files.

`llms-with-matlab` includes a license condition stating that the software and derivatives are licensed solely for use in conjunction with MathWorks products and service offerings. Keep it in the MATLAB layer and do not port that code into the Python/Rust/C++ runtime.

## Why vendor instead of rewrite

These tools are not replacing SyMoNeuRaL runtime code. They add a MATLAB research/control/client layer:

- MATLAB planning
- MATLAB local LLM calls
- MATLAB classification experiments
- MATLAB benchmark analysis later

Canonical SyMoNeuRaL runtime remains:

- Python/FastAPI manager API
- `engines/symon-llm.cpp`
- `engines/symon-image.cpp`
- `bin/symon-llm-server`
- `bin/symon-image-server`

## Added wrappers

Project-owned MATLAB wrappers live in `matlab/+symon`:

- `symon.addPaths`
- `symon.managerSubmit`
- `symon.localOpenAIChat`
- `symon.openImageClassifierApp`
