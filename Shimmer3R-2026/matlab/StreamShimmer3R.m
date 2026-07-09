function StreamShimmer3R()
%STREAMSHIMMER3R — Stream EDA (GSR) and PPG from a Shimmer3R over LSL and CSV.
%
%   StreamShimmer3R() loads all acquisition parameters from
%   matlab/params/params_shimmer3r.m, connects to the Shimmer3R via the
%   official MATLAB Instrument Driver (ShimmerDeviceHandler + Java JARs),
%   and streams calibrated EDA and filtered PPG data over LSL while logging
%   to a timestamped CSV file.
%
%   The connection and sensor configuration are handled in the event-driven
%   onConnected callback using the deep-clone configuration pattern from
%   ppgtoheartrateexample.m and plotandwriteexample.m.
%
%   Hardware platform:
%       Shimmer3R + SR48 (GSR+) daughter card — EDA and PPG.
%
%   Required files (in matlab/Resources/):
%       ShimmerDeviceHandler.m, ComPortEventData.m, FilterClass.m,
%       newWriteHeadersToFile.m, ShimmerBiophysicalProcessingLibrary_Rev_0_10.jar,
%       libs/ShimmerJavaClass.jar, libs/jssc-2.9.6.jar, libs/vecmath-1.3.1.jar,
%       libs/commons-lang3-3.8.1.jar, libs/commons-math-2.2.jar,
%       libs/commons-math3-3.6.jar, libs/guava-19.0.jar
%
%   Requires MATLAB R2013a (v8.1) or later.
%   Java 8+ runtime required (bundled with MATLAB ≥ R2017b).
%
%   See also ShimmerDeviceHandler, params_shimmer3r, FilterClass

%% ── Load Parameters ───────────────────────────────────────────────────────

% Ensure the script directory and its subdirectories are on the MATLAB path.
scriptDir = fileparts(mfilename('fullpath'));
addpath(fullfile(scriptDir, 'Resources'));
addpath(fullfile(scriptDir, 'params'));

PARAMS = params_shimmer3r();

% Extract frequently accessed parameters into local variables to avoid
% repeated struct field access in the inner loop.
comPort                 = PARAMS.comPort;
samplingRate_Hz         = PARAMS.samplingRate_Hz;
captureDuration_s       = PARAMS.captureDuration_s;
subjectID               = PARAMS.subjectID;
outputDir               = PARAMS.outputDir;
lslStreamName           = PARAMS.lslStreamName;
lslSourceID             = PARAMS.lslSourceID;
lslLibPath              = PARAMS.lslLibPath;
fclpPPG_Hz              = PARAMS.fclpPPG_Hz;
nPolesPPG               = PARAMS.nPolesPPG;
pbRipple_pct            = PARAMS.pbRipple_pct;
connectionTimeout_s     = PARAMS.connectionTimeout_s;
delayPeriod_s           = PARAMS.delayPeriod_s;
configPause_s           = PARAMS.configPause_s;
deviceLabel             = PARAMS.deviceLabel;

%% ── Path Setup ────────────────────────────────────────────────────────────

% Add LSL library to MATLAB path.
if exist(lslLibPath, 'dir')
    addpath(genpath(lslLibPath));
else
    warning('StreamShimmer3R:lslPathMissing', ...
            'LSL library path not found: %s\nLSL streaming disabled.', lslLibPath);
end

% Ensure data output directory exists.
if ~exist(outputDir, 'dir')
    mkdir(outputDir);
end

%% ── Shared State (accessed by onConnected nested callback) ────────────────

% Integer counter — not a boolean — to distinguish the initial connection
% event (0 → configure) from the post-configuration reconnection event (1 → stream).
configured = 0;

% PPG channel name varies by hardware version.
% Default to Shimmer3R name; overwritten in onConnected if hardware
% detection returns Shimmer3 instead.
ppgChannelName = 'PPG_A1';    % Shimmer3R default (Shimmer3 uses 'PPG_A13')

% Device hardware ID string, populated after configureFromClone completes.
hardwareVersionID = '';

%% ── Device Handler ────────────────────────────────────────────────────────

fprintf('[Shimmer3R] Initializing ShimmerDeviceHandler ...\n');
deviceHandler = ShimmerDeviceHandler();

% Ensure disconnection happens on normal termination, error, or Ctrl-C.
cleanupHandle = onCleanup(@() disconnectDevice(deviceHandler, comPort));

% Register event listeners.
addlistener(deviceHandler, 'DeviceConnected',    @(src, evt) onConnected(src, evt));
addlistener(deviceHandler, 'DeviceDisconnected', @(src, evt) disp('[Shimmer3R] Disconnected'));
addlistener(deviceHandler, 'DeviceConnectionLost', @(src, evt) disp('[Shimmer3R] Connection lost'));

%% ── Connect ───────────────────────────────────────────────────────────────

fprintf('[Shimmer3R] Connecting to device on COM %s ...\n', comPort);
deviceHandler.bluetoothManager.setVerbose(false);
deviceHandler.bluetoothManager.connectShimmerThroughCommPort(comPort);

%% ── Wait for Streaming to Begin ──────────────────────────────────────────

connectionTimer = tic;
fprintf('[Shimmer3R] Waiting for data stream to start (configuring sensors) ...\n');

while isempty(deviceHandler.obj.receiveData(comPort))
    pause(delayPeriod_s);
    if toc(connectionTimer) > connectionTimeout_s
        error('StreamShimmer3R:connectionTimeout', ...
              'No data received from device within %d s.', connectionTimeout_s);
    end
end

fprintf('[Shimmer3R] Data stream active. Hardware: %s\n', hardwareVersionID);

%% ── Main Data Loop ────────────────────────────────────────────────────────

% Target channel names — confirmed from live Shimmer3R device 2026-07-03.
%   GSR_Skin_Resistance  → calibrated EDA in kOhms
%   PPG_A1               → calibrated photoplethysmography in mV
%   Timestamp             → device-local timestamp in ms
CHANNEL_TIMESTAMP = 'Timestamp';
CHANNEL_GSR       = 'GSR_Skin_Resistance';
CHANNEL_PPG       = 'PPG_A1';

% ── PPG Low-Pass Filter ─────────────────────────────────────────────────
%
% 2nd-order Chebyshev LPF at fclpPPG_Hz (default 5 Hz per Bent & Dunn 2021).
% Filter parameters sourced from params_shimmer3r.m — no magic numbers.
%
% FilterClass is carried over from the original Shimmer3 codebase.  Its
% Chebyshev IIR implementation maintains a state buffer across calls for
% continuous online filtering of streamed data chunks.
% Reference: Smith, S.W. (1997). The Scientist and Engineer's Guide to
%            Digital Signal Processing, Ch. 20.
ppgLpf = FilterClass(FilterClass.LPF, samplingRate_Hz, fclpPPG_Hz, ...
                     nPolesPPG, pbRipple_pct);

% ── LSL Outlet ──────────────────────────────────────────────────────────

% Initialize Lab Streaming Layer outlet.
%   Stream name and source ID from params.
%   2 channels: EDA (kOhms), PPG (mV), both cf_float32.
lslOutlet = [];
if exist('lsl_loadlib', 'file')
    try
        lslLib = lsl_loadlib();
        fprintf('[LSL] Library version: %d\n', lsl_library_version(lslLib));

        lslInfo = lsl_streaminfo(lslLib, lslStreamName, 'shimmer', 2, ...
                                 samplingRate_Hz, 'cf_float32', lslSourceID);

        % Channel metadata
        lslChannels = lslInfo.desc().append_child('channels');

        chEda = lslChannels.append_child('channel');
        chEda.append_child_value('label', 'EDA');
        chEda.append_child_value('unit', 'kOhms');

        chPpg = lslChannels.append_child('channel');
        chPpg.append_child_value('label', 'PPG');
        chPpg.append_child_value('unit', 'mV');

        % Device metadata
        lslDevice = lslInfo.desc().append_child('device');
        lslDevice.append_child_value('manufacturer', 'Shimmer');
        lslDevice.append_child_value('name', hardwareVersionID);
        lslDevice.append_child_value('label', deviceLabel);

        lslOutlet = lsl_outlet(lslInfo);
        fprintf('[LSL] Outlet created: "%s" (%d ch, %.1f Hz)\n', ...
                lslStreamName, 2, samplingRate_Hz);
    catch lslError
        warning('StreamShimmer3R:lslInitFailed', ...
                'LSL outlet creation failed: %s\nLSL streaming disabled.', ...
                lslError.message);
    end
else
    fprintf('[LSL] liblsl not found on path — LSL streaming disabled.\n');
end

% ── CSV Output ──────────────────────────────────────────────────────────

% Generate ISO-8601 timestamped filename.
sessionTimestamp = datetime('now', 'TimeZone', 'UTC');
sessionTimestamp.Format = 'yyyy-MM-dd''T''HH-mm-ss';
csvFilename = sprintf('%s_%s.csv', subjectID, char(sessionTimestamp));
csvFilePath = fullfile(outputDir, csvFilename);

% Column definitions for the 3-line CSV header.
csvChannelNames = {'Timestamp', 'EDA_kOhms', 'PPG_mV', 'PPG_Filtered_mV'};
csvChannelFormats = {'CAL', 'CAL', 'CAL', 'CAL'};
csvChannelUnits = {'ms', 'kOhms', 'mV', 'mV'};

fprintf('[Shimmer3R] CSV output: %s\n', csvFilePath);

% ── Polling Loop ────────────────────────────────────────────────────────

firstPacket = true;
elapsedTime = 0;
tic;

while elapsedTime < captureDuration_s

    pause(delayPeriod_s);

    data = deviceHandler.obj.receiveData(comPort);
    if isempty(data)
        elapsedTime = elapsedTime + toc;
        tic;
        continue;
    end

    elapsedTime = elapsedTime + toc;
    tic;

    % Parse the cell array returned by receiveData.
    %   data{1} → newData    [nSamples × nSignals] double matrix
    %   data{2} → signalNameArray   Java String array
    %   data{3} → signalFormatArray Java String array
    %   data{4} → signalUnitArray   Java String array
    newData         = data(1);
    signalNameArray = data(2);
    signalFormatArray = data(3);
    signalUnitArray   = data(4);

    % Convert Java string arrays to MATLAB cell arrays on first packet
    % so we can match channel names with ismember().
    if firstPacket
        nSignals = numel(signalNameArray);
        signalNames = cell(nSignals, 1);
        signalFormats = cell(nSignals, 1);
        signalUnits = cell(nSignals, 1);
        for i = 1:nSignals
            signalNames{i}  = char(signalNameArray(i));
            signalFormats{i} = char(signalFormatArray(i));
            signalUnits{i}   = char(signalUnitArray(i));
        end

        fprintf('[Shimmer3R] Stream active — %d channels:\n', nSignals);
        for i = 1:nSignals
            fprintf('  %2d: %-28s  %-6s  [%s]\n', i, signalNames{i}, signalFormats{i}, signalUnits{i});
        end

        % Find column indices for our target channels.
        idxTimestamp = find(ismember(signalNames, CHANNEL_TIMESTAMP), 1);
        idxGSR       = find(ismember(signalNames, CHANNEL_GSR), 1);
        idxPPG       = find(ismember(signalNames, CHANNEL_PPG), 1);

        if isempty(idxTimestamp) || isempty(idxGSR) || isempty(idxPPG)
            error('StreamShimmer3R:missingChannel', ...
                  'Required channels not found in signal list.\n' + ...
                  '  Expected: %s, %s, %s', ...
                  CHANNEL_TIMESTAMP, CHANNEL_GSR, CHANNEL_PPG);
        end

        fprintf('[Shimmer3R] Column indices — Timestamp:%d  GSR:%d  PPG:%d\n', ...
                idxTimestamp, idxGSR, idxPPG);

        % ── CSV Header ─────────────────────────────────────────────
        %
        % Write 3-line header on first data packet using the standard
        % Shimmer CSV header format (newWriteHeadersToFile from
        % Shimmer-MATLAB-ID v3.0.1).
        newWriteHeadersToFile(csvFilePath, csvChannelNames, ...
                              csvChannelFormats, csvChannelUnits);

        firstPacket = false;
    end

    % Extract our target channels.
    timestamps       = newData(:, idxTimestamp);
    edaCalibrated    = newData(:, idxGSR);
    ppgCalibrated    = newData(:, idxPPG);
    nSamples         = numel(ppgCalibrated);

    % ── PPG Filter ────────────────────────────────────────────────────
    %
    % Apply 2nd-order Chebyshev LPF online.  FilterClass maintains an
    % internal state buffer across calls, enabling continuous filtering
    % of chunked stream data without edge artefacts between iterations.
    ppgFiltered = zeros(nSamples, 1);
    for iSample = 1:nSamples
        ppgFiltered(iSample) = ppgLpf.filterData(ppgCalibrated(iSample));
    end

    % Append data columns: Timestamp | EDA | PPG_Raw | PPG_Filtered
    dlmwrite(csvFilePath, ...
             [timestamps, edaCalibrated, ppgCalibrated, ppgFiltered], ...
             '-append', 'delimiter', '\t', 'precision', 16);

    % ── LSL Streaming ─────────────────────────────────────────────────
    %
    % Push calibrated EDA and filtered PPG as a [2 × nSamples] float32
    % chunk to the LSL outlet.
    if ~isempty(lslOutlet)
        lslOutMatrix = single([edaCalibrated'; ppgFiltered']);
        lslOutlet.push_chunk(lslOutMatrix);
    end

end  % main data loop

fprintf('[Shimmer3R] Streaming loop ended. Elapsed time: %.1f s\n', elapsedTime);

%% ── Packet Rate ───────────────────────────────────────────────────────────

try
    packetRate = deviceHandler.bluetoothManager.getShimmerDeviceBtConnected(comPort).getPacketReceptionRateOverall();
    fprintf('[Shimmer3R] Packet reception rate: %.1f %%\n', packetRate);
catch
    fprintf('[Shimmer3R] Packet reception rate: unavailable\n');
end

%% ── Teardown ──────────────────────────────────────────────────────────────

fprintf('[Shimmer3R] Stopping stream and disconnecting ...\n');
clear cleanupHandle;  % triggers onCleanup → disconnectDevice

fprintf('[Shimmer3R] Session complete.\n');

%% ═══════════════════════════════════════════════════════════════════════════
%  NESTED CALLBACKS AND CLEANUP
%  These functions are defined inside StreamShimmer3R and share its workspace.
% ═══════════════════════════════════════════════════════════════════════════

    function onConnected(~, ~)
%onConnected — ShimmerDeviceHandler 'DeviceConnected' event callback.
%
%   This callback fires twice per session:
%     1. After initial Bluetooth connection (configured == 0):
%        Deep-clone device, configure sensors, generate and apply config.
%     2. After configureFromClone() completes (configured == 1):
%        Start streaming.
%
%   The configured integer counter (not boolean) is required because
%   both the initial connection and the post-configuration reconnection
%   fire the same 'DeviceConnected' event.
%
%   The deep-clone configuration pattern follows Shimmer-MATLAB-ID v3.0.1
%   examples: ppgtoheartrateexample.m, plotandwriteexample.m.

    fprintf('[Shimmer3R] onConnected: configured = %d\n', configured);

    if configured == 1
        % Second fire: sensor configuration applied — start streaming.
        fprintf('[Shimmer3R] Configuration complete. Starting data stream ...\n');
        deviceHandler.bluetoothManager.getShimmerDeviceBtConnected(comPort).startStreaming();
        return;
    end

    % First fire: configure the device.
    fprintf('[Shimmer3R] Configuring sensors (sampling rate = %d Hz) ...\n', samplingRate_Hz);

    % Deep-clone the connected device for configuration.
    % The clone is configured, then applied back to the live device via
    % configureFromClone().
    shimmerClone = deviceHandler.bluetoothManager.getShimmerDeviceBtConnected(comPort).deepClone();

    % ── Sampling Rate ──────────────────────────────────────────────────

    shimmerClone.setSamplingRateShimmer(samplingRate_Hz);

    % ── Sensor Selection ───────────────────────────────────────────────

    shimmerClone.disableAllSensors();
    shimmerClone.setEnabledAndDerivedSensorsAndUpdateMaps(0, 0);

    % Enable GSR (EDA) and PPG sensors only.
    %   deviceHandler.sensorClass.SHIMMER_GSR         → galvanic skin response
    %   deviceHandler.sensorClass.HOST_PPG_A13        → photoplethysmography
    %     (channel name maps to 'PPG_A1' on Shimmer3R, 'PPG_A13' on Shimmer3)
    %
    % Sensor constants confirmed via fieldnames(deviceHandler.sensorClass)
    % on 2026-07-03. See specs/shimmer3r-gsr-ppg-streaming/sensor_constants.md
    sensorIds = javaArray('java.lang.Integer', 2);
    sensorIds(1) = java.lang.Integer(deviceHandler.sensorClass.SHIMMER_GSR);
    sensorIds(2) = java.lang.Integer(deviceHandler.sensorClass.HOST_PPG_A13);
    shimmerClone.setSensorIdsEnabled(sensorIds);

    % ── Communication Type ─────────────────────────────────────────────

    commType = javaMethod('valueOf', ...
        'com.shimmerresearch.driver.Configuration$COMMUNICATION_TYPE', ...
        'BLUETOOTH');

    % ── Generate and Apply Configuration ───────────────────────────────

    com.shimmerresearch.driverUtilities.AssembleShimmerConfig.generateSingleShimmerConfig(...
        shimmerClone, commType);

    deviceHandler.bluetoothManager.getShimmerDeviceBtConnected(comPort).configureFromClone(shimmerClone);

    % ── Wait for Configuration to Settle ───────────────────────────────
    % The device requires time to process the configuration payload.
    % Minimum 20 s per ppgtoheartrateexample.m Shimmer-MATLAB-ID v3.0.1.
    fprintf('[Shimmer3R] Waiting %d s for configuration to settle ...\n', configPause_s);
    pause(configPause_s);

    % ── Hardware Version Detection ─────────────────────────────────────

    hardwareVersionID = char(shimmerClone.getHardwareVersionParsed());
    fprintf('[Shimmer3R] Detected hardware version: %s\n', hardwareVersionID);

    if strcmp(hardwareVersionID, 'Shimmer3R')
        % Shimmer3R maps the internal PPG ADC to channel A1 instead of A13.
        % Reference: Shimmer-C-API Wiki, "Shimmer3R Integration Notes" (May 2025).
        ppgChannelName = 'PPG_A1';
    else
        % Shimmer3 (fallback) — PPG on internal ADC A13.
        ppgChannelName = 'PPG_A13';
    end
    fprintf('[Shimmer3R] PPG channel name: %s\n', ppgChannelName);

    % Increment the counter so the next 'DeviceConnected' event triggers
    % the streaming-start branch.
    configured = configured + 1;

    end  % onConnected


    function disconnectDevice(handler, port)
%disconnectDevice — Clean up Shimmer3R connection on exit, error, or Ctrl-C.
%
%   Stops streaming if active, then disconnects the Bluetooth session.
%   Called automatically by onCleanup.

    try
        handler.bluetoothManager.getShimmerDeviceBtConnected(port).stopStreaming();
    catch
        % Device may already be stopped or never started — safe to ignore.
    end

    try
        handler.bluetoothManager.getShimmerDeviceBtConnected(port).disconnect();
    catch
        % Device may already be disconnected — safe to ignore.
    end

    fprintf('[Shimmer3R] Device disconnected.\n');

    end  % disconnectDevice

end  % StreamShimmer3R
