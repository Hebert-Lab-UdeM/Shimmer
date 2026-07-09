function shimmer_bridge(comPort, outputFile, duration, shimmerID)
%SHIMMER_BRIDGE - Wrapper for StreamShimmer.m that provides timestamp synchronization with Python
%
% SYNOPSIS: shimmer_bridge(comPort, outputFile, duration, shimmerID)
%
% INPUTS:
%   comPort    - String value defining the COM port (e.g., 'COM4')
%   outputFile - String path to output CSV file
%   duration   - Recording duration in seconds (numeric)
%   shimmerID  - Shimmer 4-character identifier (e.g., 'D284')
%
% OUTPUTS:
%   - Creates flag files for Python synchronization:
%       shimmer_ready.flag       - Contains PID and launch timestamp
%       shimmer_connected.flag   - Created after successful Shimmer connection
%       shimmer_first_sample.flag - Created when first data sample received
%   - Calls StreamShimmer.m to perform actual data acquisition
%
% PURPOSE:
%   This wrapper enables precise timestamp synchronization between Python GUI
%   and MATLAB Shimmer recording by writing UTC timestamps to flag files at
%   critical moments during the connection and recording process.
%
% TIMING SYNCHRONIZATION:
%   1. Python launches this script via subprocess and records launch time
%   2. This script writes PID and timestamp to shimmer_ready.flag
%   3. StreamShimmer.m is called (Bluetooth connection takes 10-30s)
%   4. After StreamShimmer returns/connects, shimmer_connected.flag is created
%   5. Python can calculate exact connection latency from flag file timestamps
%
% CRITICAL TEST NEEDED:
%   We need to verify if StreamShimmer.m blocks until connection succeeds
%   or returns immediately. Current implementation assumes blocking behavior.
%   If non-blocking, additional polling logic will be needed.
%
% See also: StreamShimmer
%
% Copyright (c) 2025 Hébert Lab
% Created: 2025-10-03
% Author: SDK

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

try
    %% Step 0: Add Resources folder to MATLAB path
    % This ensures all helper functions (f_SaveCommandWindow, etc.) are available
    resources_dir = fullfile(pwd, 'Resources');
    if exist(resources_dir, 'dir')
        addpath(resources_dir);
        fprintf('Added to path: %s\n', resources_dir);
    else
        warning('Resources directory not found: %s', resources_dir);
    end

    %% Step 1: Write process ready flag with PID and launch timestamp
    % This tells Python that MATLAB process started successfully

    % Debug: Print current working directory
    fprintf('MATLAB working directory: %s\n', pwd);

    % Get current process ID
    pid = feature('getpid');

    % Get UTC timestamp (timezone-aware)
    launch_time = datetime('now', 'TimeZone', 'UTC');

    % Write to flag file with atomic operations
    fid = fopen('shimmer_ready.flag', 'w');
    if fid == -1
        error('Failed to create shimmer_ready.flag file');
    end

    % Debug: Print where the flag file was created
    fprintf('Created flag file: %s\\shimmer_ready.flag\n', pwd);

    % Write PID on first line, timestamp on second line (ISO 8601 format)
    fprintf(fid, '%d\n', pid);
    fprintf(fid, '%s\n', char(launch_time, 'yyyy-MM-dd''T''HH:mm:ss.SSSSSSSSS''Z'''));
    fclose(fid);

    fprintf('✓ Shimmer bridge ready (PID: %d)\n', pid);
    fprintf('  Launch time: %s\n', char(launch_time, 'yyyy-MM-dd''T''HH:mm:ss.SSS''Z'''));

    %% Step 2: Call StreamShimmer to connect and record
    % This is where the 10-30 second Bluetooth connection delay occurs

    fprintf('Starting StreamShimmer (COM%s, ID: %s)...\n', comPort, shimmerID);
    fprintf('Connecting to Shimmer (may take 10-30 seconds)...\n');

    % Call the existing StreamShimmer function with required parameters
    % Note: We use liveshow=false and parallel=true to avoid MATLAB GUI windows
    % The parallel flag prevents the stop button figure window from appearing
    % Note: StreamShimmer now writes shimmer_connected.flag and shimmer_first_sample.flag
    % internally during execution, not after it returns
    StreamShimmer(comPort, 'GSR', ...
        'filename', outputFile, ...
        'duration', duration, ...
        'liveshow', false, ...
        'parallel', true, ...
        'unixtime', true, ...
        'id', shimmerID);

    fprintf('✓ Shimmer bridge completed successfully\n');

catch ME
    %% Error handling: Write error to log file for Python to detect

    error_time = datetime('now', 'TimeZone', 'UTC');
    error_log_file = sprintf('shimmer_error_%s.log', ...
        char(error_time, 'yyyyMMdd_HHmmss'));

    fid = fopen(error_log_file, 'w');
    if fid ~= -1
        fprintf(fid, 'Shimmer Bridge Error\n');
        fprintf(fid, 'Time: %s\n', char(error_time, 'yyyy-MM-dd''T''HH:mm:ss.SSS''Z'''));
        fprintf(fid, 'Identifier: %s\n', ME.identifier);
        fprintf(fid, 'Message: %s\n', ME.message);
        fprintf(fid, '\nStack Trace:\n');
        for i = 1:length(ME.stack)
            fprintf(fid, '  File: %s\n', ME.stack(i).file);
            fprintf(fid, '  Function: %s\n', ME.stack(i).name);
            fprintf(fid, '  Line: %d\n\n', ME.stack(i).line);
        end
        fclose(fid);
    end

    % Re-throw error so Python can detect subprocess failure
    rethrow(ME);
end

end
