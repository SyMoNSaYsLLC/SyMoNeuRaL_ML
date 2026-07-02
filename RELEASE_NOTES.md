# Release Notes

## 1.5.1-user-docs-clean

Documentation cleanup for public/user-facing release.

### Changed

- Removed maintainer-specific repository creation/push instructions from user documentation.
- Kept setup, CUDA build, model conversion, VRAM tuning, API, and runtime guidance for future users.
- Kept project metadata, `.gitignore`, license, issue templates, and workflow files for repository maintenance.

## 1.5.0-github-symoneural-ml

Repository identity and NVIDIA server documentation update.

### Changed

- Project root named `SyMoNeuRaL_ML`.
- README focused on NVIDIA server builds and runtime usage.
- Added GPU/server build guidance.
- Added `.gitignore`, `LICENSE`, issue templates, PR template, and workflow scaffold.
- Updated package metadata to `symoneural-ml`.
- Updated CMake project name to `SyMoNeuRaL_ML`.
- Preserved CUDA/model tool shipping architecture from `1.4.0-cuda-model-tools`.
- Preserved exclusive VRAM handoff architecture.
