function p = mcpServerPath()
%MCPSERVERPATH Return the project-local MATLAB MCP Server binary path.
root = symon.projectRoot();
p = fullfile(root, "bin", "matlab-mcp-server");
end
