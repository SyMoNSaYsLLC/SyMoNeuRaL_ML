function root = projectRoot()
%PROJECTROOT Return the SyMoNeuRaL_ML repository root from the MATLAB package path.
thisFile = mfilename("fullpath");
% matlab/+symon/projectRoot.m -> repo root is two levels above matlab.
root = fileparts(fileparts(fileparts(thisFile)));
end
