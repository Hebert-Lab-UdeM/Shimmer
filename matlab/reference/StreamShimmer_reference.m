function StreamShimmer(comPort, shimmerType, varargin)
%STREAMSHIMMER - Record data from the Shimmer device on comPort. Optionaly visualise live stream
%                      and/or send data stream over LSL and/or save it to a CSV file.
%
% SYNOPSIS: StreamShimmer(comPort, shimmerType, varargin)
%
% INPUTS:
%       comPort - String value defining the COM port number for Shimmer.(i.e. '7': GSR, '6': ECG)
%   shimmerType - String value defining the type of shimmer connected on COM port. 
%                 Supported values: 'GSR', 'ECG'
%      varargin - {'key', value} pair argument to set other options.
%           'duration', (numeric) defines the recording duration in seconds (default=inf)
%           'filename', (string) defines the path to output_datafile.csv (default='')
%           'lsl',      (logical) enable/disable the data streaming over LSL (default=false)
%           'lsl_data', (string) defines the data to stream over LSL: 'raw' (default) | 'filtered'
%           'lsl_record_timestamps', (logical) add recorded shimmer's timestamp in LSL stream
%           'leadoff_lsl', (logical) enable/disable the lead-off and STA signals in the LSL stream
%           'id', (string) define the Shimmer 4 characters identifier as printed behind the device
%           'liveshow', (logical) enable/disable the data streams' live display (default=false)
%           'plotwindow', (numeric) defines the number of seconds to show in live plot (default=5)
%           'unixtime', (logical) enable/disable shimmer to return Unix timestamps (default=false)
%           'parallel', (TODO)(logical) enable/disable execution in a new dedicated thread (default=false)
%
% OUTPUTS:
%   - if 'filename' defines a *.csv file, the file's columns for <shimmerType> is:
%       row 1      > Time Stamp, Channel Names, ...
%       row 2      > CAL/RAW, ..., CAL/RAW
%       row 3      > channel's units
%       row 4:end  > data samples, ..., data samples
%   - if 'lsl' is true, the same data format as the csv file is sent, without the header lines (2-3)
%
% Required files:
%   - Realterm must be installed using the executable setup in the requirements folder
%   - Resources\ShimmerHandleClass.m
%   - Resources\SetEnabledSensorsMacrosClass.m
%   - Resources\FilterClass.m
%   - Resources\writeHeadersToFile.m (only if 'filename' is correctly set)
%   - LSL matlab library (only if 'lsl' is true)
%
% EXAMPLES:
%   - StreamShimmer('7', 'GSR', 'lsl', true, 'lsl_data', 'raw')
%   - StreamShimmer('6', 'ECG', 'filename', 'some/diretory/testfile.csv', 'liveshow', false)
%
% REMARKS:
%   - LSL demo video: https://www.youtube.com/watch?v=Y1at7yrcFW0
%   - DELAY_PERIOD must be >=0.2 otherwise Matlab raises an errors when the closing figure that
%     display the live streams, hanging for a really long time.
%   - Shimmer IDs as seen behind each device:
%       + GSR: Shimmer3-D284
%       + ECG: Shimmer3-ED47
%   - Shimmer3-ECG channel description:
%       * Bipolar leads:
%           - ECGLL_RA: Lead I   > LeftLeg (red)   - RightArm (white) [ExG1 Ch1]
%           - ECGLA_RA: Lead II  > LeftArm (black) - RightArm (white) [ExG1 Ch2]
%           - ECGLL_LA: Lead III > LeftArm (black) - LeftLeg  (red) = II-I = ECGLA_RA - ECGLL_RA
%       * Unipolar leads (Vx-WCT):
%          ECG vector signal measured from the Wilson's Central Terminal (WCT; ExG2 Ch2)
%           - ECGVx_RL: Position x around the ribs (brown) - RightLeg (green)
%           - ECGRESP: diagonal upper left (BLACK electrode) & lower right(GREEN electrode)
%       * Disconnected lead detection
%           - Lead_offECGLL: (logical) true if left leg's lead is disconnected
%           - Lead_offECGLA: (logical) true if left arm's lead is disconnected
%           - Lead_offECGRA: (logical) true if right arm's lead is disconnected
%           - Lead_offECGRLD: (logical) true if right leg drive is off
%           - Lead_offECGVx: (logical) true if the rib cage's lead is disconnected
%       - EXG1 & 2 STA: status byte as a square wave of 1Hz frequency and an amplitude of ±1mV
%                         + EXG1 bit 1: ECG LL  lead-off
%                         + EXG1 bit 3: ECG LA  lead-off
%                         + EXG1 bit 4: ECG RA  lead-off
%                         + EXG1 bit 5: ECG RLD lead-off
%                         + EXG2 bit 3: ECG Vx  lead-off
%
% See also SetEnabledSensorsMacrosClass, ShimmerHandleClass, LSL_test, ppgtoheartrateexample, 
%           ecgtoheartrateexample, plotandwriteecgleadoffdetectionexample
% 
% TODO:
%   - Support GSR & ECG in the same script
%       + Automatise ploting in a loop or function per shimmerType
%   - Run in background within a dedicated thread and return from the function ?
%   - Check if I should use ? setgsrrange ?
%   - Deploy as an app                                                           
% 
% Copyright Tomy Aumont

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%
% Created with:
%   MATLAB ver.: 9.11.0.1873467 (R2021b) Update 3 on
%    Microsoft Windows 10 Home Version 10.0 (Build 19042)
%
% Author:     Tomy Aumont
% Work:       
% Email:      tomy.aumont@umontreal.ca
% Website:    
% Created on: 14-Mar-2022
% Revised on:
%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% Default parameters
captureDuration = inf;               % time duration to stream the signals, in seconds.
fileName = '';                      % where to save the signals as a csv file
shimmerID = '';                     % 4 characters identifier printed behind the wristband
enable_lsl = false;                 % enable to stream signals over LSL or not
lsl_stream_type = 'raw';            % possible values: 'raw', 'filtered'
enable_unixtimestamps = false;
enable_parallel = false;
enable_liveShow = false;            % Plot the signals or not
visualizationWindowLength_sec = 5;  % Number of seconds to visualize if plotting the signals
connectionTimeOut = 60;             % Timer limit for trying to connect the Shimmer [seconds]
enable_leadoff_lsl_stream = true;   % Allow pushing lead-off signals over LSL
stream_timestamps_over_lsl = true;  % TODO: =false when synchronisation has been figured out


%% PARSE INPUTS
%================================
for iArg = 1:2:numel(varargin)
    switch lower(varargin{iArg})
        case 'duration'
            if isdeployed
                captureDuration = str2double(varargin{iArg+1});
            else
                captureDuration = varargin{iArg+1};
            end
        case 'filename'
            fileName = varargin{iArg+1};
            if ~endsWith(fileName, '.csv', 'IgnoreCase', true)
                fileName = strcat(fileName, '.csv');
            end
        case 'lsl'
            enable_lsl = varargin{iArg+1};
        case 'lsl_data'
            if contains(varargin{iArg+1}, {'filtered', 'raw'}, 'IgnoreCase', true)
                lsl_stream_type = lower(varargin{iArg+1});
            else
                warning('off', 'backtrace')
                warning(['Unrecognized ''lsl_data'' value: ''%s''.\n', ... 
                         '\tChoices are: ''filtered'', ''raw'''], varargin{iArg+1})
                warning('on', 'backtrace')
            end
        case 'lsl_record_timestamps'
            if islogical(varargin{iArg+1})
                stream_timestamps_over_lsl = varargin{iArg+1};
            else
                stream_timestamps_over_lsl = any(logical(varargin{iArg+1}));
            end
        case 'liveshow'
            enable_liveShow = varargin{iArg+1};
        case 'plotwindow'
            visualizationWindowLength_sec = varargin{iArg+1};
        case 'unixtime'
            enable_unixtimestamps = varargin{iArg+1};
        case 'parallel'
            warning('off', 'backtrace')
            warning('Currently not supported. Write/use a batch script instead.')
            warning('on', 'backtrace')
            enable_parallel = varargin{iArg+1};
            if enable_parallel && isempty(ver('parallel'))
                error('Parallel Computing Toolbox is not installed.')
            end
        case 'leadoff_lsl'
            if islogical(varargin{iArg+1})
                enable_leadoff_lsl_stream = varargin{iArg+1};
            else
                enable_leadoff_lsl_stream = any(logical(varargin{iArg+1}));
            end
        case 'id'
            shimmerID = varargin{iArg+1};
    end
end

% FOR COMPILED APP DEBUG
% disp(comPort)
% disp(shimmerType)
% disp(varargin)


%% Discover library folders
%================================
% Supporting Shimmer functions
if ~isdeployed
    if enable_parallel
        addpath('Shimmer/Resources/')
    else
        addpath('./Resources')
    end

    % Supporting LSL functions
    if enable_lsl
        % Define LSL installation directory based on the current PC USER
        [~, hostname] = system('hostname');
        hostname = strtrim(hostname);
        switch hostname
            case 'MSI'
                LSL_PATH = 'D:\labstreaminglayer-1.0.31\labstreaminglayer\';
            case 'I155198-eoa'
                LSL_PATH = 'C:/Users/LARNA/Documents/MATLAB/Acute_Tinnitus/labstreaminglayer';
            otherwise
                LSL_PATH = 'F:\EOA\AUDACE\'; % USB dongle
        end
    
        % Add the LSL installation directory to matlab path
        addpath(genpath(fullfile(LSL_PATH, 'LSL', 'liblsl-Matlab')));
    end
end

f_SaveCommandWindow([shimmerType, '_COM', comPort], false)


%% SHIMMER DEFINITION
%================================

shimmer = ShimmerHandleClass(comPort);
SensorMacros = SetEnabledSensorsMacrosClass;    % Assign friendly macros for setenabledsensors.
if enable_unixtimestamps
    shimmer.enabletimestampunix(true);
end

if strcmpi(shimmerType, 'GSR')
    % REF for fs=64:
    %   Bent, B and Dunn, JP. Optimizing sampling rate of wrist-worn optical sensors for physiologic
    %   monitoring. Journal of Clinical and Translational Science 5: e34, 1–8.
    %   doi: 10.1017/cts.2020.526
    fs = 64;            % Sampling rate in [Hz]. See "Sampling Rate Tabel.txt".
    lslShimmerVersion = 'Shimmer3-GSR+';
    if isempty(shimmerID)
        shimmerID = 'D284';
    end
elseif strcmpi(shimmerType, 'ECG')
    fs = 256;  % Sampling rate in [Hz]. ECG recommend >=500Hz. See "Sampling Rate Tabel.txt"
    lslShimmerVersion = 'Shimmer3-ECG';
    if isempty(shimmerID)
        shimmerID = 'ED47';
    end
end

DELAY_PERIOD = 0.2; % Data read period [seconds] = (1/rate). See REMARKS
numPlotSample = fs * visualizationWindowLength_sec;  % Only used if 'liveshow' is true

[chanNames, chanUnits] = GetShimmerChannels(shimmerType);    % Get channel names and units

if enable_leadoff_lsl_stream
    nChans = numel(chanNames);
    lslChanNames = chanNames;
    lslchanUnits = chanUnits;
else
    nChans = sum(~contains(chanNames, {'lead-off', 'STA'}, 'IgnoreCase', true));
    lslChanNames = chanNames(~contains(chanNames, {'lead-off', 'STA'}, 'IgnoreCase', true));
    lslchanUnits = chanUnits(~contains(chanNames, {'lead-off', 'STA'}, 'IgnoreCase', true));
end

if stream_timestamps_over_lsl
    nChans = nChans + 1; % Number of channels + time stamps.
    lslChanNames = ['timestamps', lslChanNames];
    lslchanUnits = ['miliseconds' lslchanUnits];
end


%% SETTINGS
%================================
% Filter
fm = 60;           % mains (power line) frequency [Hz]
fchp = 0.05;       % corner frequency highpassfilter [Hz]; 0.5 ==> monitoring | 0.05 ==> diagnostic
fclpPPG = 5;       % PPG corner frequency lowpassfilter [Hz];
nPolesEXG = 4;     % number of poles (ECG, EDA)
nPolesPPG = 2;     % number of poles (PPG)
pbRipple = 0.5;    % pass band ripple (%)

% These filters are basic cleaning and should not be skipped.
HPF = true;         % enable (true) or disable (false) highpass filter
LPF = true;         % enable (true) or disable (false) lowpass filter
BSF = fs > 2*fm;    % enable (true) or disable (false) bandstop filter

if HPF  % highpass filters
    hpfilterEXG = FilterClass(FilterClass.HPF, fs, fchp, nPolesEXG, pbRipple);
end
if LPF  % lowpass filters
    lpfilterEXG = FilterClass(FilterClass.LPF, fs, fs/2-1, nPolesEXG, pbRipple); % EDA
    lpfilterPPG = FilterClass(FilterClass.LPF, fs, fclpPPG, nPolesPPG, pbRipple);    % PPG
end
if BSF % bandstop filters : cornerfrequencies at +/-1Hz from mains frequency
    bsfilterEXG = FilterClass(FilterClass.LPF, fs, [fm-1, fm+1], nPolesEXG, pbRipple);
end


% Data streaming (LSL)
if enable_lsl
    lib = lsl_loadlib();
    disp(['[LSL] Version: ' num2str(lsl_library_version(lib))])

    disp('[LSL] Creating a new streaminfo...');
%     stream_name = ['shimmer-' shimmerType];
    info = lsl_streaminfo(lib, shimmerType, 'shimmer', nChans, fs, 'cf_float32', 'sdfwerr32432');

    disp('[LSL] Defining stream''s metadata...')
    chns = info.desc().append_child('channels');
    for i = 1:length(lslChanNames)
        ch = chns.append_child('channel');
        ch.append_child_value('label', lslChanNames{i});
        ch.append_child_value('unit', lslchanUnits{i});
    end
    wristband = info.desc().append_child('device');
    wristband.append_child_value('manufacturer', 'Shimmer');
    wristband.append_child_value('name', lslShimmerVersion);
    wristband.append_child_value('label', shimmerID);

    disp('[LSL] Opening an outlet...');
    outlet = lsl_outlet(info);
end

%---------------------------------


%% Connect to Shimmer device
%================================
fprintf('[Shimmer] Connecting to COM%s (%s) ...\n', comPort, shimmerType)
tic;
while ~strcmp(shimmer.State, 'Connected') && (toc < connectionTimeOut)
    shimmer.connect;
    pause(2)
end

if strcmp(shimmer.State, 'Connected')

    fprintf('[Shimmer] Connection to COM%s (%s) succeeded.\n', comPort, shimmerType)

    %% Write connection timestamp flag for Python synchronization
    connection_time = datetime('now', 'TimeZone', 'UTC');
    fid = fopen('shimmer_connected.flag', 'w');
    if fid ~= -1
        fprintf(fid, '%s\n', char(connection_time, 'yyyy-MM-dd''T''HH:mm:ss.SSSSSSSSS''Z'''));
        fclose(fid);
        fprintf('[Shimmer] Written shimmer_connected.flag\n');
    end

    %% Define shimmer board and sampling rate.
    shimmer.setinternalboard(shimmerType);
    shimmer.disableallsensors;
    fs = shimmer.setsamplingrate(fs);


    %% Enable sensors, see determineenabledsensorsbytes for more details
    % TODO: Adapt the call to setenabledsensors(...) according to with/out lead-off channels
    if verLessThan('matlab', '8.1') % 8.1 == R2013a
        eval(['shimmer.setenabledsensors(SensorMacros.' shimmerType ',1);']);
    else
        shimmer.setenabledsensors(SensorMacros.(shimmerType), 1);
    end
    if strcmpi(shimmerType, 'GSR')
        % Enable PPG sensor
        shimmer.setenabledsensors(SensorMacros.INTA13,1);
        shimmer.setenabledsensors(SensorMacros.ACCEL, 1);  % Enable accelerometer
        shimmer.setinternalexppower(1);
    end

    % Set ExG lead-off detection mode to 'DC Current', no effect if board doesn't support it.
    shimmer.setexgleadoffdetectionmode(1);

    if shimmer.start
        fprintf('[Shimmer] COM%s (%s) streaming...\n', comPort, shimmerType)

        if ~enable_parallel
            % Avoid using a GUIs, figure, etc. when parallel processing
            % Create a STOP button to end the recording session
            [stopButton, stopFigureHdl] = MakeStopButton(shimmerType);
        else
            % In parallel mode, set dummy values so the loop works
            stopButton = [];
            stopFigureHdl = [];
        end

        % Prepare optional vizualisation figure
        if enable_liveShow
            plotData = [];
            filteredPlotData = [];
            fHdl = InitializeFigures(shimmerType);
        end

        firstrun = true;
        allTimeStamps = []; tic; % Start timer
        % Loop condition: check time AND stop button (if it exists)
        while (toc < captureDuration) && (isempty(stopButton) || ishandle(stopButton))

            if ~isempty(stopFigureHdl) && ishandle(stopFigureHdl)
                figure(stopFigureHdl)
            end

            % Read the latest data from shimmer data buffer.\
            % TODO: Change 'a' for 'u' or 'c' based on lsl_data
            [newData, signalNames, signalFormats, signalUnits] = shimmer.getdata('a');

            if ~isempty(newData)
                % Write first sample flag on first data received
                if firstrun
                    first_sample_time = datetime('now', 'TimeZone', 'UTC');
                    fid = fopen('shimmer_first_sample.flag', 'w');
                    if fid ~= -1
                        fprintf(fid, '%s\n', char(first_sample_time, 'yyyy-MM-dd''T''HH:mm:ss.SSSSSSSSS''Z'''));
                        fclose(fid);
                        fprintf('[Shimmer] Written shimmer_first_sample.flag\n');
                    end
                end 
                %% Set the channels and time stamp in a specific order
                %================================
                if strcmpi(shimmerType, 'GSR')
                    % Select calibrated channels for GSR
                    chanFormatMask = ismember(signalFormats, 'CAL');
                else
                    % Select all channels for ECG
                    chanFormatMask = true(1, length(signalFormats));
                end

                % Combine the channel type mask with the ordered channels indices
                chIndex = cellfun(@(c) find(ismember(signalNames, c) & chanFormatMask), chanNames);
                timeMask = ismember(signalNames, 'Time Stamp') & ismember(signalFormats, 'CAL');
                timeStampIndex = find(timeMask);
                                   
                % Write header to CSV file
                if firstrun && ~isempty(fileName)
                    c = [timeStampIndex, chIndex];
                    hdr = {signalNames(c), signalFormats(c), signalUnits(c)};
                    firstrun = writeHeadersToFile(fileName, hdr{:});
                    clearvars c hdr
                end
                
                chNames = signalNames(chIndex);
                dataRaw = newData(:, chIndex);

                % Keep track of the calibrated time stamps, in miliseconds
                timeStamps = newData(:, timeStampIndex);
                allTimeStamps = [allTimeStamps; timeStamps];
                if ~stream_timestamps_over_lsl
                    timeStamps = [];
                end
                
                
                %% Send raw data into LSL stream
                %================================
                if enable_lsl && strcmpi(lsl_stream_type, 'raw')
                    if strcmpi(shimmerType, 'ECG') && ~enable_leadoff_lsl_stream
                        % Do not push lead-off and STA signals over LSL
                        leadoffMask = contains(chNames, {'lead-off', 'STA'}, 'IgnoreCase', true);
                        outlet.push_chunk([timeStamps, dataRaw(:, ~leadoffMask)]');
                    else
                        outlet.push_chunk([timeStamps, dataRaw]');
                    end
                end


                %% Filter the data
                %================================
                dataFiltered = dataRaw;
                if HPF % highpass filter to remove DC-offset
                    for iCh = 1:size(dataFiltered, 2)
                        if strcmpi(shimmerType, 'GSR') && (iCh == 2)  % strcmpi(chNames{iCh}, 'INTA13')
                            continue % Skip PPG
                        end
                        dataFiltered(:, iCh) = hpfilterEXG.filterData(dataFiltered(:, iCh));
                    end
                end

                if BSF % bandstop filter to suppress mains (power-line) interference
                    for iCh = 1:size(dataFiltered, 2)
                        dataFiltered(:, iCh) = bsfilterEXG.filterData(dataFiltered(:, iCh));
                    end
                end
                
                if LPF % lowpass filter to avoid aliasing
                    for iCh = 1:size(dataFiltered, 2)
                        if strcmpi(shimmerType, 'GSR') && strcmpi(chNames{iCh}, 'Internal ADC A13')
                            % PPG has a different filter than GSR
                            dataFiltered(:, iCh) = lpfilterPPG.filterData(dataFiltered(:, iCh));
                        else
                            dataFiltered(:, iCh) = lpfilterEXG.filterData(dataFiltered(:, iCh));
                        end
                    end
                end
                

                %% Send new filtered data chunk into LSL stream
                %================================
                if enable_lsl && strcmpi(lsl_stream_type, 'filtered')
                    if strcmpi(shimmerType, 'ECG') && ~enable_leadoff_lsl_stream
                        % Do not push lead-off and STA signals over LSL
                        leadoffMask = contains(chNames, {'lead-off', 'STA'}, 'IgnoreCase', true);
                        outlet.push_chunk([timeStamps, dataFiltered(:, ~leadoffMask)]');
                    else
                        outlet.push_chunk([timeStamps, dataFiltered]');
                    end
                    
                end


                %% Append the new data to the file in a comma delimited format
                %================================
                if ~isempty(fileName)
                    writematrix([timeStamps, dataRaw], fileName, 'WriteMode', 'append');
                end


                if enable_liveShow && isvalid(fHdl.fig1)
                    %% Update the plots 
                    %================================
                    plotData = [plotData; dataRaw];
                    filteredPlotData = [filteredPlotData; dataFiltered];
                    [plotData, filteredPlotData] = UpdatePlots(fHdl, fs, plotData, ...
                                                                filteredPlotData, numPlotSample, ...
                                                                shimmerType, chIndex, ...
                                                                signalFormats, signalNames, ...
                                                                signalUnits);
                end
            end
            drawnow
            pause(DELAY_PERIOD);  % Refresh rate. It allows data to arrive in the buffer
        end  
        close(stopFigureHdl)

        fprintf('[Shimmer] %% of received packets: %d \n', ...
            shimmer.getpercentageofpacketsreceived(allTimeStamps));

        fprintf('[Shimmer] COM%s (%s) streaming stopped...\n', comPort, shimmerType)
        shimmer.stop;
    end 

else
    warning('off', 'backtrace')
    warning('[Shimmer] Connection to COM%s failed.\n', comPort)
    warning('on', 'backtrace')
end

fprintf('[Shimmer] COM%s (%s) disconnected.\n', comPort, shimmerType)
shimmer.disconnect;

clear shimmer;

if isempty(enable_parallel) || ~enable_parallel
    close('all')
end

end

function fHdl = InitializeFigures(shimmerType)
    fHdl.fig1 = figure('Name', ['Shimmer (' shimmerType ') signals']);
    set(fHdl.fig1, 'Position', [100, 100, 800, 400]); % Position set from lower-left corner
    
    if strcmpi(shimmerType, 'ECG')
        fHdl.figure2=figure('Name','Shimmer ECG signals');
        set(fHdl.figure2, 'Position', [950, 600, 800, 400]);
        fHdl.figure3=figure('Name','Shimmer Lead-off detection signals');
        set(fHdl.figure3, 'Position', [100, 100, 800, 900]);
        fHdl.figure4=figure('Name','Shimmer Lead-off detection signals');
        set(fHdl.figure4, 'Position', [950, 100, 800, 400]);
    end
end
