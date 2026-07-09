function f_SaveCommandWindow(fname_prefix, withDate)
%F_SAVECOMMANDWINDOW - Start recording the command window output to <fname_prefix>_date_time file.
%   in the "log_files" directory.
%
% SYNOPSIS: f_SaveCommandWindow(fname_prefix)
%
% Required files:
%
% EXAMPLES:
%
% REMARKS:
%
% See also 
%
% Copyright Tomy Aumont

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%
% Created with:
%   MATLAB ver.: 9.6.0.1214997 (R2019a) Update 6 on
%    Microsoft Windows 10 Home Version 10.0 (Build 17763)
%
% Author:     Tomy Aumont
% Work:       Center for Advance Research in Sleep Medicine
% Email:      tomy.aumont@umontreal.ca
% Website:    
% Created on: 08-May-2020
% Revised on:
%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% ===== BUILD OUTPUT FILENAME =====
if nargin >= 1
    if ischar(fname_prefix)
        fname = fname_prefix;
    else
        fname = 'default';
        fprintf('WARNING: Input must be a character array. Saving log file to ''default''\n')
    end
end

if nargin < 2
    withDate = true;
end

if withDate
    fname = [fname, '_', datestr(now, 'yyyy_mmmm_dd_HH-MM-SS')];
end

fname = fullfile('log_files', [fname, '.log']);

if ~isfolder('log_files')
    mkdir('log_files')
end

% ===== START RECORDING COMMAND WINDOW =====
% eval(['diary ' diary_filename]);
diary(fname)


callstack = dbstack(1);
fprintf('\nSCRIPT: %s on %s\n\n', callstack(1).file, date)
