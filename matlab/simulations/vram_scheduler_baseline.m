% SyMoNeuRaL VRAM scheduler baseline simulation
% Placeholder for modeling engine load/unload behavior.

clear; clc;

engines = ["writer", "code", "image"];
vramMiB = [14500, 14500, 12000];

disp(table(engines', vramMiB', 'VariableNames', {'Engine','TargetVRAMMiB'}));
