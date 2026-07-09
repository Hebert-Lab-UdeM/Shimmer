function PARAMS = params_shimmer3r()
%PARAMS_SHIMMER3R — Acquisition parameters for Shimmer3R GSR/EDA + PPG streaming.
%
%   PARAMS = params_shimmer3r() returns a struct containing all configurable
%   parameters for StreamShimmer3R.m.  Edit this file to change session-level
%   settings; no values should be hardcoded in the main acquisition script.
%
%   See also StreamShimmer3R

%% ── Device ─────────────────────────────────────────────────────────────────

% Windows COM port assigned to the Shimmer3R after Bluetooth pairing.
%   e.g. 'COM7' — check Windows Device Manager → Ports (COM & LPT)
%   after pairing the device via Settings → Bluetooth & devices.
PARAMS.comPort = 'COM7';

% Shimmer3R device identifier (4 characters printed on the back of the unit).
%   e.g. 'D284'.  Used in LSL device metadata and log file naming.
PARAMS.deviceLabel = 'D284';

%% ── Acquisition ───────────────────────────────────────────────────────────

% Sampling rate in Hz.
%   Reference: Bent, B. & Dunn, J.P. (2021). Optimizing sampling rate of
%   wrist-worn optical sensors for physiologic monitoring. Journal of Clinical
%   and Translational Science, 5, e34, 1–8. doi: 10.1017/cts.2020.526
%   Recommendation: 64 Hz for wrist-worn PPG.
PARAMS.samplingRate_Hz = 64;

% Total recording duration in seconds.
%   Set to inf for indefinite recording (stop manually).
PARAMS.captureDuration_s = 300;

%% ── Subject ───────────────────────────────────────────────────────────────

% Subject identifier string.  Embedded in the output CSV filename.
PARAMS.subjectID = 'subj01';

%% ── Directories ───────────────────────────────────────────────────────────

% Directory where CSV data files and verification plots are saved.
%   Relative paths are resolved from the directory containing StreamShimmer3R.m.
PARAMS.outputDir = './data/';

% Full path to the liblsl MATLAB bindings (liblsl-Matlab/ folder).
%   Edit this to match the LSL installation on the acquisition PC.
%   Example for USB-drive install: 'F:\EOA\AUDACE\LSL\liblsl-Matlab\'
PARAMS.lslLibPath = 'F:\EOA\AUDACE\LSL\liblsl-Matlab\';

%% ── LSL Streaming ─────────────────────────────────────────────────────────

% LSL stream name (inlet clients resolve streams by this name).
PARAMS.lslStreamName = 'Shimmer3R_GSR_PPG';

% LSL source ID string.  Must be unique per device on the network.
PARAMS.lslSourceID = 'shimmer3r_001';

%% ── PPG Filter ────────────────────────────────────────────────────────────

% PPG low-pass filter corner frequency in Hz.
%   5 Hz is standard for photoplethysmography: preserves heart-rate band
%   (∼0.5–3 Hz) while attenuating high-frequency noise and motion artefacts.
PARAMS.fclpPPG_Hz = 5;

% Chebyshev filter order (number of poles) for the PPG LPF.
%   Must be even. 2 poles = gentle roll-off, minimal phase distortion.
PARAMS.nPolesPPG = 2;

% Passband ripple for the Chebyshev filter design, in percent.
PARAMS.pbRipple_pct = 0.5;

%% ── Timing ────────────────────────────────────────────────────────────────

% Maximum wait time for the Bluetooth connection to establish, in seconds.
PARAMS.connectionTimeout_s = 60;

% Polling interval between data-read operations, in seconds.
%   Must be >= 0.2 to allow data to accumulate in the buffer and prevent
%   MATLAB from hanging when closing figures.
PARAMS.delayPeriod_s = 0.2;

% Pause duration after calling configureFromClone(), in seconds.
%   The device requires time to process the sensor configuration.
%   Minimum 20 s based on ppgtoheartrateexample.m.
PARAMS.configPause_s = 20;

%% ── MATLAB Compatibility ──────────────────────────────────────────────────

% MATLAB version requirement for this script.
%   Requires MATLAB R2013a (v8.1) or later for dot-notation struct field
%   access used in ShimmerDeviceHandler callbacks.
%   Java 8+ runtime is also required (bundled with MATLAB ≥ R2017b).
PARAMS.matlabMinVersion = '8.1';  % R2013a

end
