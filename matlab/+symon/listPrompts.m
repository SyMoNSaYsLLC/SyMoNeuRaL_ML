function prompts = listPrompts()
%LISTPROMPTS List vendored MathWorks AI coding prompts by category.
root = symon.projectRoot();
promptRoot = fullfile(root, "matlab", "vendor", "mathworks-ai-coding-prompts", "prompts");
files = dir(fullfile(promptRoot, "*", "*.md"));
prompts = strings(numel(files), 1);
for k = 1:numel(files)
    prompts(k) = fullfile(files(k).folder, files(k).name);
end
end
