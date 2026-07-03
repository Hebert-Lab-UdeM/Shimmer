function [channelNames, channelUnits] = GetShimmerChannels(shimmertype)
%GETSHIMMERCHANNELS - Given a supported type of shimmer wristband, return the name of all the 
%                     recorder channels.
%
% SYNOPSIS: [channelNames, channelUnits] = GetShimmerChannels(shimmertype)
%
% INPUTS:
%    shimmertype - (string) Type of shimmer wristband.
%
% OUTPUTS:
%   channelNames - (cell array) The channel names
%   channelUnits - (cell array) The channel units
%
% Required files:
%
%
% EXAMPLES:
%
%
% REMARKS:
%
% See also 
%
% Copyright Tomy Aumont

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%
% Created with:
%   MATLAB ver.: 9.11.0.1873467 (R2021b) Update 3 on
%    Microsoft Windows 10 Home Version 10.0 (Build 19044)
%
% Author:     Tomy Aumont
% Work:       
% Email:      tomy.aumont@umontreal.ca
% Website:    
% Created on: 27-Oct-2022
% Revised on:
%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%


[channelNames, channelUnits] = deal({});

switch lower(shimmertype)
    
    case 'gsr'
        channelNames = {'GSR', 'Internal ADC A13'};
        channelUnits = {'kohms', 'millivolts'};

    case 'ecg'
        channelNames = {'ECG LL-RA', 'ECG LA-RA', 'ECG Vx-RL', 'ECG RESP', 'Lead-off ECG LL', ...
                        'Lead-off ECG LA', 'Lead-off ECG RA', 'Lead-off ECG RLD', ...
                        'Lead-off ECG Vx', 'EXG1 STA', 'EXG2 STA'};
        channelUnits = {'millivolts', 'millivolts', 'millivolts', 'millivolts', 'bool', 'bool', ...
                        'bool', 'bool', 'bool', 'bool', 'bool'};
end

