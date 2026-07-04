function job = managerSubmit(prompt, opts)
% managerSubmit Submit a prompt to the SyMoNeuRaL manager API and optionally poll.
%
% This uses the Python/FastAPI manager layer, so backend routing still decides
% whether the request is writer/chat, code, image, or another worker.
%
% Example:
%   symon.addPaths
%   job = symon.managerSubmit("write a haiku about CUDA")
%
% Name-value options:
%   BaseURL       default "http://127.0.0.1:8000"
%   Poll          default true
%   Timeout       default 600 seconds
%   PollInterval  default 1.5 seconds

arguments
    prompt (1,1) string
    opts.BaseURL (1,1) string = "http://127.0.0.1:8000"
    opts.Poll (1,1) logical = true
    opts.Timeout (1,1) double = 600
    opts.PollInterval (1,1) double = 1.5
end

baseURL = strip(opts.BaseURL, "right", "/");
submitURL = baseURL + "/api/v1/manager/submit";

request = struct("prompt", prompt);
webOpts = weboptions( ...
    "MediaType", "application/json", ...
    "ContentType", "json", ...
    "Timeout", max(10, opts.Timeout));

job = webwrite(submitURL, request, webOpts);

if ~opts.Poll
    return
end

if isfield(job, "id")
    jobID = string(job.id);
elseif isfield(job, "job_id")
    jobID = string(job.job_id);
else
    warning("SyMoNeuRaL:NoJobID", "Manager response did not include id/job_id.");
    return
end

started = tic;
while toc(started) < opts.Timeout
    statusURL = baseURL + "/api/v1/manager/jobs/" + jobID + "?include_image=false";
    job = webread(statusURL, webOpts);

    if isfield(job, "status")
        status = string(job.status);
        if status == "done" || status == "failed"
            return
        end
    end

    pause(opts.PollInterval);
end

warning("SyMoNeuRaL:Timeout", "Timed out waiting for job %s.", jobID);
end
