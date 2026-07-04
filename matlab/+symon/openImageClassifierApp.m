function openImageClassifierApp()
% openImageClassifierApp Open the migrated MATLAB Image Classifier app.
%
% This app is for MATLAB-based image classification training/explainability.
% It does not replace the SyMoNeuRaL image-generation engine.

symon.addPaths();

root = fileparts(fileparts(mfilename("fullpath")));
appPath = fullfile(root, "vendor", "mathworks-image-classifier-app", "ImageClassifier.mlapp");

if ~isfile(appPath)
    error("SyMoNeuRaL:MissingImageClassifierApp", "Missing app: %s", appPath);
end

open(appPath);
end
