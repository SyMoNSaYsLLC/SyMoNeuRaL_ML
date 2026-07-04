# SyMoNeuRaL MATLAB Layer

This folder contains SyMoNeuRaL MATLAB wrappers plus migrated MathWorks MATLAB tools.

## Project wrappers

- `+symon/addPaths.m`
- `+symon/managerSubmit.m`
- `+symon/localOpenAIChat.m`
- `+symon/openImageClassifierApp.m`

## Migrated tools

- `vendor/mathworks-llms-with-matlab`
- `vendor/mathworks-image-classifier-app`

## Basic use

```matlab
symon.addPaths
job = symon.managerSubmit("write a CUDA haiku")
```

For direct OpenAI-compatible text-engine access:

```matlab
symon.addPaths
chat = symon.localOpenAIChat("You are SyMoNeuRaL.")
response = generate(chat, "hello")
```

For the image classifier app:

```matlab
symon.openImageClassifierApp
```
