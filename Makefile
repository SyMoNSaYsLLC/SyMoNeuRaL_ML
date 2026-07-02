SHELL := /usr/bin/env bash

.PHONY: install path build build-llama build-sd server web vram doctor clean

install:
	./scripts/install.sh

path:
	./scripts/install_path_tools.sh

build:
	./scripts/build_all_cuda.sh

build-llama:
	./scripts/build_llama_cuda.sh

build-sd:
	./scripts/build_stable_diffusion_cuda.sh

server:
	./scripts/start_exclusive_16gb.sh

web:
	python3 -m symon_tools.web

vram:
	./scripts/vram_watch.sh

doctor:
	./scripts/doctor.sh

clean:
	sudo rm -rf engines/llama.cpp/build engines/stable-diffusion.cpp/build build
