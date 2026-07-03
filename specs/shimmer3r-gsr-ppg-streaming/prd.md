# PRD: Shimmer3R GSR+PPG Streaming Module

**Status:** Draft
**Created:** 2026-07-03
**Slug:** shimmer3r-gsr-ppg-streaming

---

## 1. Problem & Motivation

The lab's existing Shimmer3 acquisition code (`StreamShimmer.m` / `ShimmerHandleClass.m`) relies on
Realterm, a Windows ActiveX COM server, to mediate all Bluetooth serial communication. The new
Shimmer3R platform (STM32U5A5 MCU, Infineon CYW20820 BLE radio) is not supported by this driver, and
the Realterm dependency is fragile and no longer maintained. A replacement module is needed that
connects programmatically to the Shimmer3R, streams EDA and PPG in real time over LSL, and saves
time-stamped raw and filtered data to CSV — using the current official SDK and without the Realterm
dependency.

---

## 2. Goals

- Connect programmatically to a Shimmer3R + SR48 (GSR+) daughter card from a Windows PC without
  requiring Realterm or Consensys.
- Stream EDA (GSR, kohm) and PPG (optical, mV) at 64 Hz over Lab Streaming Layer (LSL) in real time.
- Write calibrated EDA and filtered PPG data to a timestamped CSV file during acquisition.
- Apply a 2nd-order Chebyshev low-pass filter (corner 5 Hz) to the PPG channel before output.
- Report packet reception rate at the end of each session.
- Deliver three independent implementation variants in sequence:
  - **Phase 1 (primary):** MATLAB using the official `ShimmerDeviceHandler` + Java JARs
    (`Shimmer-MATLAB-ID` v3.0.1).
  - **Phase 2:** Python using `pyshimmer` over Classic Bluetooth (RFCOMM).
  - **Phase 3:** Python using `bleak` over BLE (CYSPP protocol).

---

## 3. Non-Goals

- ECG, EMG, IMU, magnetometer, pressure, or any sensor other than EDA and PPG.
- Real-time signal quality visualization beyond a packet loss percentage printed at session end.
- Post-hoc analysis, artifact rejection, or heart-rate derivation from PPG.
- A graphical user interface or participant-facing display.
- On-device SD card logging (the device may log independently, but the module does not manage it).
- Support for more than one Shimmer3R device simultaneously.
- Cross-platform support for Phase 1 (MATLAB on Linux is out of scope).
- Support for the original Shimmer3 platform (the new module targets Shimmer3R only).

---

## 4. User Stories / Use Cases

- As a lab researcher, I want to run a single script that connects to the Shimmer3R, streams EDA and
  PPG via LSL, and writes a CSV, so that I can start a recording session without configuring any
  middleware or GUI.
- As a researcher integrating Shimmer data with other biosignal streams (EEG, audio), I want an
  active LSL outlet so that I can time-lock Shimmer data to other streams using a shared LSL clock.
- As a lab coordinator, I want all acquisition parameters (COM port, sampling rate, subject ID,
  output directory, LSL path) in a single params file, so that per-session configuration requires
  editing one file rather than modifying script code.
- As a developer, I want Phase 2 and Phase 3 to provide equivalent functionality to Phase 1 (same
  channels, same LSL metadata, same CSV format) so that the downstream analysis pipeline is
  transport-agnostic.

---

## 5. Functional Requirements

### Phase 1 — MATLAB + ShimmerDeviceHandler (Java)

1. The script must load all acquisition parameters from `matlab/params/params_shimmer3r.m`; no
   parameter values may be hardcoded in the main script.
2. The script must instantiate `ShimmerDeviceHandler` and connect to the device via
   `bluetoothManager.connectShimmerThroughCommPort(comPort)` using the COM port specified in params.
3. The script must configure the device in the `onConnected` callback using the deep-clone pattern:
   set sampling rate, disable all sensors, then enable only EDA (GSR) and PPG sensor IDs.
4. The script must detect hardware version via `getHardwareVersionParsed()` and select the correct
   PPG channel name: `'PPG_A1'` for Shimmer3R, `'PPG_A13'` for Shimmer3 (fallback).
5. The script must wait for configuration to complete before starting the streaming loop; a `pause`
   of sufficient duration (minimum 20 seconds, configurable in params) must follow `configureFromClone`.
6. The script must poll `deviceHandler.obj.receiveData(comPort)` at a fixed interval
   (`DELAY_PERIOD`, default 0.2 s) and extract EDA and PPG columns by signal name.
7. The PPG signal must be filtered online using `FilterClass` (Chebyshev LPF, corner frequency 5 Hz,
   2nd order, passband ripple 0.5%) before being written to file and pushed to LSL.
8. The script must create an LSL outlet (`cf_float32`) with 2 channels (EDA, PPG) prior to
   streaming. Channel metadata must include label, unit, and device name.
9. The LSL outlet must push calibrated EDA and filtered PPG as a chunk on each polling iteration.
10. The script must write a CSV file to `matlab/data/` with a filename incorporating subject ID and
    ISO-8601 datetime. The file must have a 3-line header (channel names / formats / units) followed
    by tab-delimited data rows containing: Unix timestamp, raw EDA, calibrated EDA (kohm), raw PPG,
    filtered PPG (mV).
11. The script must print the packet reception rate (%) to the console at session end.
12. The script must disconnect cleanly on normal termination and on error/interrupt via `onCleanup`.
13. The `onConnected` callback must use an integer counter (not a boolean flag) to distinguish the
    initial connection event from the post-configuration reconnection event.

### Phase 2 — Python + pyshimmer (Classic Bluetooth)

14. The script must load all acquisition parameters from `python/params_shimmer3r.py`; no parameter
    values may be hardcoded in the main script.
15. The script must connect to the device via RFCOMM using the Bluetooth MAC address specified in
    params (not a COM port).
16. The script must enable only EDA and PPG channels using `pyshimmer` channel type constants.
17. The script must apply the same PPG LPF (5 Hz, 2nd-order Chebyshev) as Phase 1 before output.
18. The script must create an LSL outlet with identical channel metadata (labels, units, device name)
    to Phase 1.
19. The script must write a CSV with the same column structure and header format as Phase 1.
20. The script must print packet reception rate at session end.

### Phase 3 — Python + bleak (BLE / CYSPP)

21. The script must connect to the device via BLE using the device MAC address or device name
    specified in params, using `bleak`.
22. The CYSPP BLE protocol implementation must be based on the GATT characteristic UUIDs and command
    encoding documented in `github.com/ShimmerResearch/shimmer-web-sdk` (`src/devices/shimmer3r/`).
23. Requirements 17–20 apply identically to Phase 3 (same filter, same LSL metadata, same CSV
    format, same packet rate reporting).

---

## 6. Non-Functional Requirements

- **Reliability:** Packet loss must be reported; if `getdata` / `receiveData` returns empty on a
  polling cycle, the loop must continue without crashing.
- **Reproducibility:** All configurable values (sampling rate, filter parameters, file paths, device
  identifiers) must be in the params file; magic numbers are not permitted in any script.
- **Compatibility:** Phase 1 requires MATLAB R2013a or later (gated in params comment), Java 8+, and
  the five JARs from `Shimmer-MATLAB-ID` v3.0.1. Phase 2 requires `pyshimmer >= 1.0.0`, `pylsl`,
  and `pybluez`. Phase 3 requires `bleak >= 0.21` and `pylsl`.
- **Code comments:** All non-trivial logic must be commented; protocol-level code (CYSPP byte
  encoding, sensor ID mapping) must cite the relevant Shimmer Research source.

---

## 7. Constraints & Dependencies

- **Phase 1:** Windows PC required (Bluetooth Classic pairing creates a COM port, which the Java
  driver uses). MATLAB Instrument Driver v3.0.1 JARs must be present in `matlab/Resources/`.
  `FilterClass.m` is carried over from the old codebase.
- **Phase 2:** `pyshimmer` (v1.0.0, seemoo-lab) uses RFCOMM sockets; Bluetooth Classic pairing on
  Windows required. `pybluez` must be compatible with the host OS Bluetooth stack.
- **Phase 3:** `bleak` communicates via the OS BLE stack. On Windows, this requires Bluetooth
  adapter support for BLE v4.0+. The CYSPP characteristic UUIDs are sourced from
  `shimmer-web-sdk`; any firmware update to the device may change these.
- **GSR sensor constant (unresolved at time of writing):** The exact Java sensor ID constant for GSR
  in `deviceHandler.sensorClass` is not documented in any available example. It must be verified by
  inspecting `fieldnames(deviceHandler.sensorClass)` in MATLAB before Phase 1 implementation.
  See Assumptions §9.
- **GSR channel name (unresolved):** The signal name string returned by `receiveData` for the EDA
  channel on Shimmer3R has not been confirmed. Expected values are `'GSR_Skin_Conductance'` or
  `'GSR'`; verify on first connection.
- **pyshimmer Shimmer3R compatibility (unresolved):** `pyshimmer` was written for original Shimmer3
  over Classic BT. Channel names and sensor IDs in responses may differ on Shimmer3R. Compatibility
  must be tested against the device before Phase 2 implementation proceeds.

---

## 8. Acceptance Criteria

### Phase 1

- [ ] Running `StreamShimmer3R(params)` on the Windows PC connects to the Shimmer3R within the
  configured timeout, with no Realterm or Consensys dependency.
- [ ] After connection, the device streams EDA and PPG at 64 Hz; `receiveData` returns non-empty
  data within 30 seconds of script start.
- [ ] An LSL outlet named per `params.lslStreamName` is visible to other applications on the local
  network during streaming (verifiable with `pylsl` or LabRecorder).
- [ ] At session end, a CSV file exists in `matlab/data/` containing 5 data columns with correct
  3-line header; EDA values are in the range 1–2000 kohm; PPG values are non-zero mV.
- [ ] The filtered PPG column is visually smooth relative to the raw PPG column when plotted
  (low-frequency envelope preserved, high-frequency noise attenuated), confirming the LPF is applied.
  Save a representative plot to `matlab/data/ppg_filter_verification.png`.
- [ ] Packet reception rate is printed to console at session end; value must be > 80% under normal
  operating conditions (device within 2 m of the PC).
- [ ] Interrupting the script (Ctrl+C) disconnects the device cleanly (no hung COM port or Java
  thread requiring MATLAB restart).
- [ ] No parameter values are hardcoded in `StreamShimmer3R.m`; all values are read from
  `params_shimmer3r.m`.

### Phase 2

- [ ] `python/shimmer3r_gsr_bt.py` connects to the device via RFCOMM (MAC address from params) and
  streams EDA + PPG at 64 Hz.
- [ ] LSL outlet channel metadata (labels, units, device name) matches Phase 1 exactly.
- [ ] CSV column structure and header format matches Phase 1 exactly.
- [ ] EDA and PPG values are numerically consistent with Phase 1 values collected simultaneously or
  in the same session (±5% for EDA, same order of magnitude for PPG).

### Phase 3

- [ ] `python/shimmer3r_gsr_ble.py` connects to the device via BLE (no COM port, no RFCOMM pairing)
  and streams EDA + PPG at 64 Hz.
- [ ] LSL outlet and CSV requirements are identical to Phase 2.
- [ ] EDA and PPG values are numerically consistent with Phase 1.

---

## 9. Assumptions

- The device being used is a Shimmer3R with the SR48 (GSR+) daughter card pre-installed. No other
  expansion boards are present.
- The GSR sensor constant in `deviceHandler.sensorClass` follows the naming convention already
  visible in the Java driver (e.g., `SHIMMER_GSR` or `HOST_GSR`). If the constant does not exist or
  requires a different configuration call (e.g., setting a daughter board type), this is a blocking
  issue for Phase 1 and must be resolved before implementation begins.
- The Java driver (`ShimmerJavaClass.jar`) automatically enables internal expansion power for the
  SR48 optical sensor when the GSR/PPG sensors are configured, without an explicit call equivalent
  to the old `setinternalexppower(1)`.
- The `onConnected` event fires exactly twice per session: once on initial Bluetooth connection, and
  once after `configureFromClone` completes. The `configured` integer counter pattern from
  `ppgtoheartrateexample.m` is the correct handling approach.
- 64 Hz is an acceptable sampling rate for both EDA and PPG on the Shimmer3R SR48 hardware (carried
  over from the old setup, citing Bent & Dunn 2021 for PPG).
- The Windows PC has a working Bluetooth Classic adapter capable of pairing the Shimmer3R.
- `pyshimmer` is backward-compatible with Shimmer3R over Classic Bluetooth (same LogAndStream
  protocol bytes). If this assumption fails, Phase 2 will require manual LogAndStream command
  implementation.

---

## 10. Out-of-Scope Follow-ups

- **ECG streaming:** The Shimmer3R supports ECG via the SR47 (ExG) daughter card. A separate module
  for ECG acquisition could follow the same architecture once this module is stable.
- **Multi-device synchronization:** Streaming from two Shimmer3R devices simultaneously (e.g.,
  bilateral EDA) would require extension of the connection and LSL outlet logic.
- **LSL inlet / trigger marking:** Receiving LSL markers (e.g., stimulus onset) and embedding them
  in the CSV is a common need but is not part of this module.
- **SD card log parsing:** The Shimmer3R logs data to microSD independently. A utility to read and
  parse those binary log files into the same CSV format as the streaming output would be useful for
  session recovery.
- **pyshimmer upstream contribution:** If compatibility fixes for Shimmer3R are needed in Phase 2,
  those fixes should be contributed back to `seemoo-lab/pyshimmer`.
