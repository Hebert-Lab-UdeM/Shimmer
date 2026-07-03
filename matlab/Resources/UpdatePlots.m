function [data, filtData] = UpdatePlots(fHdl, fs, data, filtData, plotLen, shimmerType, chidx, sFormats, sNames, sUnits)
% UPDATEPLOTS - Update data window in the figure of the liveshow
%
% SYNOPSIS: [data, filtData] = UpdatePlots(fHdl, fs, data, filtData, plotLen, shimmerType, chidx, sFormats, sNames, sUnits)
%
% INPUTS:
%          fHdl - handle to the figure to update
%            fs - (int) sampling frequency of the signal
%          data - (matrix) data to plot [n samples x m channels]. Truncate the 
%                 latest samples if more than the window to visualize
%      filtData - same as data, but after filtering
%       plotLen - (int) window length to visualize in seconds
%   shimmerType - type of shimmer wristband
%         chidx - The ordered channel index to fit the name list
%      sFormats - signal format: 'raw' or 'cal'
%        sNames - signal names
%        sUnits - signal units
%
% OUTPUTS:
%          data - the ploted data matrix
%      filtData - the ploted filtered data matrix
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

% Keep only the samples to plot
if size(data, 1) > plotLen
%         t = t(end - plotLen+1: end);
    t = (-plotLen+1:0)/fs;
    data = data(end-plotLen+1:end, :);
    filtData = filtData(end-plotLen+1:end, :);
else
    t = (-size(data, 1)+1:0)/fs;
end
% Convert time to seconds
%     t = t / 1000;

% Plotting
set(0, 'CurrentFigure', fHdl.fig1);
subplot(2, 2, 1);
iCh = chidx(1);
plot(t, data(:, 1));             % Plot the ecg for channel 1 of SENSOR_EXG1
legend([sFormats{iCh} ' ' sNames{iCh} ' (' sUnits{iCh} ')'])
xlim([t(1) t(end)]);
xlabel('Time (sec)')

subplot(2, 2, 2);
iCh = chidx(2);
plot(t, data(:, 2));             % Plot the ecg for channel 2 of SENSOR_EXG1
legend([sFormats{iCh} ' ' sNames{iCh} ' (' sUnits{iCh} ')']);
xlim([t(1) t(end)]);
xlabel('Time (sec)')

subplot(2, 2, 3);
iCh = chidx(1);
plot(t, filtData(:, 1));         % Plot the filtered ecg for channel 1 of SENSOR_EXG1 
legend([sFormats{iCh} ' ' 'filtered' ' ' sNames{iCh} ' (' sUnits{iCh} ')']);
xlim([t(1) t(end)]);
xlabel('Time (sec)')

subplot(2, 2, 4);
iCh = chidx(2);
plot(t, filtData(:, 2));         % Plot the filtered ecg for channel 2 of SENSOR_EXG1
legend([sFormats{iCh} ' ' 'filtered' ' ' sNames{iCh} ' (' sUnits{iCh} ')']);
xlim([t(1) t(end)]);
xlabel('Time (sec)')

if strcmpi(shimmerType, 'ECG')
    % Show ECG data + lead-off
    set(0, 'CurrentFigure', fHdl.figure2);
    subplot(2, 2, 1);
    iCh = chidx(3);
    plot(t, data(:, 3));         % Plot the ecg for channel 1 of SENSOR_EXG1
    legend([sFormats{iCh} ' ' sNames{iCh} ' (' sUnits{iCh} ')'])
    xlim([t(1) t(end)]);
    xlabel('Time (sec)')

    subplot(2, 2, 2);
    iCh = chidx(4);
    plot(t, data(:, 4));         % Plot the ecg for channel 2 of SENSOR_EXG1  
    legend([sFormats{iCh} ' ' sNames{iCh} ' (' sUnits{iCh} ')']);
    xlim([t(1) t(end)]);
    xlabel('Time (sec)')

    subplot(2, 2, 3);
    iCh = chidx(3);
    plot(t, filtData(:, 3));     % Plot the filtered ecg for channel 1 of SENSOR_EXG1  
    legend([sFormats{iCh} ' ' 'filtered' ' ' sNames{iCh} ' (' sUnits{iCh} ')']);
    xlim([t(1) t(end)]);
    xlabel('Time (sec)')

    subplot(2,2,4);
    iCh = chidx(4);
    plot(t,filtData(:,4));       % Plot the filtered ecg for channel 2 of SENSOR_EXG1
    legend([sFormats{iCh} ' ' 'filtered' ' ' sNames{iCh} ' (' sUnits{iCh} ')']);
    xlim([t(1) t(end)]);
    xlabel('Time (sec)')

    
    set(0,'CurrentFigure',fHdl.figure3);   
                    
    subplot(5,1,1);
    iCh = chidx(10);
    plot(t,data(:,10));          % Plot 'EXG1 STA'
    legend([sFormats{iCh} ' ' sNames{iCh} ' (' sUnits{iCh} ')'], 'Location','West');
    xlim([t(1) t(end)]);
    xlabel('Time (sec)')
    
    subplot(5,1,2);
    iCh = chidx(5);
    plot(t,data(:,5));           % Plot 'Lead-off ECG LL'
    legend([sFormats{iCh} ' ' sNames{iCh} ' (' sUnits{iCh} ')'], 'Location','West');
    xlim([t(1) t(end)]);
    ylim([-1 1]);
    xlabel('Time (sec)')
    
    subplot(5,1,3);
    iCh = chidx(6);
    plot(t,data(:,6));           % Plot 'Lead-off ECG LA'
    legend([sFormats{iCh} ' ' sNames{iCh} ' (' sUnits{iCh} ')'], 'Location','West');
    xlim([t(1) t(end)]);
    ylim([-1 1]);
    xlabel('Time (sec)')

    subplot(5,1,4);
    iCh = chidx(7);
    plot(t,data(:,7));           % Plot 'Lead-off ECG RA'
    legend([sFormats{iCh} ' ' sNames{iCh} ' (' sUnits{iCh} ')'], 'Location', 'West');
    xlim([t(1) t(end)]);
    ylim([-1 1]);
    xlabel('Time (sec)')

    subplot(5,1,5);
    iCh = chidx(8);
    plot(t,data(:,8));           % Plot 'Lead-off ECG RLD'
    legend([sFormats{iCh} ' ' sNames{iCh} ' (' sUnits{iCh} ')'], 'Location','West');
    xlim([t(1) t(end)]);
    ylim([-1 1]);
    xlabel('Time (sec)')
    
    set(0,'CurrentFigure',fHdl.figure4);
    
    subplot(2,1,1);
    iCh = chidx(11);
    plot(t,data(:,11));          % Plot 'EXG2 STA'
    legend([sFormats{iCh} ' ' sNames{iCh} ' (' sUnits{iCh} ')'], 'Location','West');
    xlim([t(1) t(end)]);
    xlabel('Time (sec)')
    
    subplot(2,1,2);
    iCh = chidx(9);
    plot(t,data(:,9));           % Plot 'Lead-off ECG Vx'
    legend([sFormats{iCh} ' ' sNames{iCh} ' (' sUnits{iCh} ')'], 'Location','West');
    xlim([t(1) t(end)]);
    ylim([-1 1]);
    xlabel('Time (sec)')
end

