# Tasks: Shimmer3R GSR+PPG Streaming Module (Phase 1: MATLAB + Java)

**PRD:** specs/shimmer3r-gsr-ppg-streaming/prd.md
**Generated:** 2026-07-03
**Status:** Not started

---

## Task 1: Verify GSR sensor constant and channel names
**Covers PRD:** §7 (Constraints), §9 (Assumptions), AC Phase 1 #1

- [ ] **1.1 [research]** Inspect `deviceHandler.sensorClass` in MATLAB to identify the GSR sensor ID constant name (expected: `SHIMMER_GSR`, `HOST_GSR`, or similar). Document the exact constant name and verify it exists. Also inspect the PPG constant to confirm `HOST_PPG_A13` is present.
- [ ] **1.2 [review]** Verify the discovered constant names are documented in a notes file at `specs/shimmer3r-gsr-ppg-streaming/sensor_constants.md` for reference during implementation.

## Task 2: Create params_shimmer3r.m configuration file
**Covers PRD:** §5 FR 1, §6 (Reproducibility), AC Phase 1 #8

- [ ] **2.1 [implementation]** Create `matlab/params/params_shimmer3r.m` with all configurable parameters: `comPort`, `samplingRate_Hz` (64), `captureDuration_s`, `outputDir`, `subjectID`, `lslStreamName`, `lslSourceID`, `lslLibPath`, `fclpPPG_Hz` (5), `nPolesPPG` (2), `pbRipple_pct` (0.5), `connectionTimeout_s` (60), `delayPeriod_s` (0.2), `configPause_s` (20), and MATLAB version requirement comment. No magic numbers in main script.
- [ ] **2.2 [review]** Verify all parameters from PRD §5 FR 1 are present, all values have comments explaining their purpose, and no hardcoded values remain in the task description.

## Task 3: Build ShimmerDeviceHandler connection and configuration layer
**Covers PRD:** §5 FR 2–5, 13, AC Phase 1 #1

- [ ] **3.1 [research]** Review `ppgtoheartrateexample.m` and `plotandwriteexample.m` from `Shimmer-MATLAB-ID` repo to understand the `onConnected` callback pattern, deep-clone configuration workflow, and the `configured` integer counter mechanism.
- [ ] **3.2 [implementation]** Copy required JARs and `ShimmerDeviceHandler.m` from `Shimmer-MATLAB-ID` v3.0.1 to `matlab/Resources/`: `ShimmerJavaClass.jar`, `jssc-2.9.6.jar`, `vecmath-1.3.1.jar`, `commons-lang3-3.8.1.jar`, `ShimmerBiophysicalProcessingLibrary_Rev_0_10.jar`, `ShimmerDeviceHandler.m`, `ComPortEventData.m`, `newWriteHeadersToFile.m`.
- [ ] **3.3 [implementation]** Create connection skeleton: instantiate `ShimmerDeviceHandler`, call `bluetoothManager.connectShimmerThroughCommPort(comPort)`, register `addlistener` callbacks for `DeviceConnected`, `DeviceDisconnected`, `DeviceConnectionLost`.
- [ ] **3.4 [implementation]** Implement `onConnected` callback with `configured` integer counter: on first fire (`configured==0`), deep-clone device, set sampling rate, disable all sensors, build sensorIds Java array with GSR and PPG constants, call `setSensorIdsEnabled`, generate config via `generateSingleShimmerConfig`, apply via `configureFromClone`, pause for `configPause_s`, increment `configured`. On second fire (`configured==1`), call `startStreaming`.
- [ ] **3.5 [implementation]** Implement hardware version detection: after `configureFromClone`, call `getHardwareVersionParsed().equals('Shimmer3R')` and set `ppgChannelName = 'PPG_A1'` for Shimmer3R or `'PPG_A13'` for fallback.
- [ ] **3.6 [review]** Verify connection establishes within `connectionTimeout_s`, `onConnected` fires exactly twice per session, and hardware detection correctly identifies Shimmer3R.

## Task 4: Build data acquisition polling loop
**Covers PRD:** §5 FR 6, §6 (Reliability), AC Phase 1 #2

- [ ] **4.1 [implementation]** Implement main polling loop: `while elapsedTime < captureDuration`, `pause(delayPeriod_s)`, call `deviceHandler.obj.receiveData(comPort)`, handle empty data by continuing without error.
- [ ] **4.2 [implementation]** Implement data extraction: parse `data` cell array into `newData`, `signalNameArray`, `signalFormatArray`, `signalUnitArray`; convert Java strings to MATLAB cell arrays; find channel indices via `ismember` for timestamp, EDA/GSR, and PPG channels using discovered channel names.
- [ ] **4.3 [implementation]** Implement elapsed time tracking: `tic` before loop, `elapsedTime = elapsedTime + toc` at end of each iteration, `tic` to reset timer.
- [ ] **4.4 [review]** Verify loop polls at correct interval, handles empty data gracefully, and extracts all three channels (timestamp, EDA, PPG) correctly.

## Task 5: Create LSL outlet and stream data
**Covers PRD:** §5 FR 8–9, AC Phase 1 #3

- [ ] **5.1 [implementation]** Create LSL outlet before streaming loop: `lsl_outlet = lsl.StreamOutlet(info)` with `lsl.StreamInfo` containing `lslStreamName`, 2 channels, `cf_float32`, `lslSourceID`, and metadata (channel labels: `'EDA_kohm'`, `'PPG_mV'`; units: `'kohm'`, `'mV'`; device name from params).
- [ ] **5.2 [implementation]** Integrate `push_chunk` into polling loop: transpose extracted EDA and filtered PPG data into `[2 × nSamples]` matrix, call `lsl_outlet.push_chunk(data')` each iteration.
- [ ] **5.3 [review]** Verify LSL outlet is visible to `pylsl.resolve_streams()` or LabRecorder during streaming, and channel metadata matches PRD specification.

## Task 6: Create CSV file output
**Covers PRD:** §5 FR 10, AC Phase 1 #4

- [ ] **6.1 [implementation]** Generate CSV filename before streaming: incorporate `subjectID` and ISO-8601 datetime (e.g., `subj01_2026-07-03T14-30-00.csv`), save to `matlab/data/`.
- [ ] **6.2 [implementation]** Write 3-line CSV header on first data arrival: line 1 = channel names (`Timestamp`, `EDA_Raw`, `EDA_Cal_kohm`, `PPG_Raw_mV`, `PPG_Filtered_mV`), line 2 = formats (`CAL`), line 3 = units (`ms`, `adc`, `kohm`, `mV`, `mV`), tab-delimited.
- [ ] **6.3 [implementation]** Append data rows each iteration: use `dlmwrite` with `-append`, delimiter `'\t'`, precision 16, writing 5 columns (timestamp, raw EDA, calibrated EDA, raw PPG, filtered PPG).
- [ ] **6.4 [review]** Verify CSV file exists at session end with correct 3-line header, 5 data columns, EDA values in 1–2000 kohm range, PPG values non-zero mV.

## Task 7: Integrate PPG low-pass filter
**Covers PRD:** §5 FR 7, AC Phase 1 #5

- [ ] **7.1 [implementation]** Copy `FilterClass.m` from old `matlab/Resources/` to new `matlab/Resources/` (preserved from legacy codebase).
- [ ] **7.2 [implementation]** Initialize filter before streaming loop: `ppgFilter = FilterClass(FilterClass.LPF, fs, fclpPPG_Hz, nPolesPPG, pbRipple_pct)`.
- [ ] **7.3 [implementation]** Apply filter in polling loop: for each PPG sample, call `ppgFilter.filterData(sample)` to get filtered value; store both raw and filtered PPG for output.
- [ ] **7.4 [implementation]** Generate filter verification plot: create figure with two subplots (raw PPG, filtered PPG) from a representative session, save to `matlab/data/ppg_filter_verification.png` showing noise attenuation.
- [ ] **7.5 [review]** Verify filtered PPG is visually smooth relative to raw PPG (high-frequency noise attenuated, low-frequency envelope preserved), and verification plot exists at specified path.

## Task 8: Implement session teardown and error handling
**Covers PRD:** §5 FR 11–12, §6 (Reliability), AC Phase 1 #6–7

- [ ] **8.1 [implementation]** Add `onCleanup` handler: `cleaner = onCleanup(@() cleanup_function)` that calls `stopStreaming()`, `disconnect()`, and closes CSV file handle if open.
- [ ] **8.2 [implementation]** Implement packet reception rate reporting: at session end, call `getPacketReceptionRateOverall()` or `getPacketReceptionRateCurrent()` and print to console with `fprintf`.
- [ ] **8.3 [implementation]** Implement Ctrl+C interrupt handling: ensure `onCleanup` fires on interrupt, device disconnects cleanly, no hung COM port or Java thread requiring MATLAB restart.
- [ ] **8.4 [review]** Verify interrupting script (Ctrl+C) disconnects device cleanly, packet rate > 80% is printed to console, and no MATLAB restart is required after interruption.

---

## Cross-Parent Dependencies

| Task | Blocked by | Justification |
|------|------------|---------------|
| 2 | 1 | Params file needs the verified GSR sensor constant name to include as a comment/reference. |
| 3 | 2 | Connection code references `params.comPort` and other config values from params file. |
| 4 | 3 | Polling loop calls `deviceHandler.obj.receiveData()` which requires connection layer to be functional. |
| 5 | 4 | LSL `push_chunk` is called inside the polling loop with extracted data. |
| 6 | 4 | CSV data append is called inside the polling loop with extracted data. |
| 7 | 4 | Filter is applied to PPG data extracted in the polling loop. |
| 8 | 3, 4, 5, 6, 7 | Cleanup must stop streaming (Task 3), close data loop (Task 4), close LSL outlet (Task 5), close CSV file (Task 6), and dispose filter (Task 7). |
