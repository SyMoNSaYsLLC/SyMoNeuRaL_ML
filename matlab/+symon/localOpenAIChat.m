function chat = localOpenAIChat(systemPrompt, opts)
% localOpenAIChat Create an openAIChat object pointing at the local LLM engine.
%
% This uses the migrated llms-with-matlab OpenAI-compatible client and talks
% directly to the local llama.cpp-compatible engine on port 8080.
%
% For full SyMoNeuRaL routing, use symon.managerSubmit instead.
%
% Example:
%   symon.addPaths
%   chat = symon.localOpenAIChat("You are SyMoNeuRaL.")
%   response = generate(chat, "say hello")

arguments
    systemPrompt (1,1) string = "You are SyMoNeuRaL."
    opts.BaseURL (1,1) string = "http://127.0.0.1:8080/v1"
    opts.ModelName (1,1) string = "symon-local"
    opts.APIKey (1,1) string = "sk-local"
end

symon.addPaths();

if exist("openAIChat", "class") ~= 8
    error("SyMoNeuRaL:MissingOpenAIChat", ...
        "openAIChat class was not found. Run symon.addPaths and verify matlab/vendor/mathworks-llms-with-matlab exists.");
end

chat = openAIChat(systemPrompt, ...
    "BaseURL", opts.BaseURL, ...
    "ModelName", opts.ModelName, ...
    "APIKey", opts.APIKey);
end
