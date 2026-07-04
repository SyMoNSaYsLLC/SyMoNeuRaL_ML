function added = addPaths()
% addPaths Add SyMoNeuRaL MATLAB tool paths.
%
% Adds the project-owned MATLAB wrappers plus migrated MathWorks tools:
% - matlab/vendor/mathworks-llms-with-matlab
% - matlab/vendor/mathworks-image-classifier-app
%
% Example:
%   symon.addPaths

root = fileparts(fileparts(mfilename("fullpath")));
llmsPath = fullfile(root, "vendor", "mathworks-llms-with-matlab");
classifierPath = fullfile(root, "vendor", "mathworks-image-classifier-app");

added = strings(0,1);

if isfolder(llmsPath)
    addpath(llmsPath);
    added(end+1) = string(llmsPath);
end

if isfolder(classifierPath)
    addpath(classifierPath);
    added(end+1) = string(classifierPath);
end

addpath(root);
added(end+1) = string(root);

disp("SyMoNeuRaL MATLAB paths added:");
disp(added);
end
