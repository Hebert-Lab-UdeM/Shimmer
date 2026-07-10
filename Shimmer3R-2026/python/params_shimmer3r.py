"""
params_shimmer3r.py — Acquisition parameters for Shimmer3R GSR/PPG streaming.

This module provides all configurable parameters for shimmer3r_gsr_bt.py.
Edit this file to change session-level settings; no values should be
hardcoded in the main acquisition script.

Usage:
    from params_shimmer3r import PARAMS
    print(PARAMS.COM_PORT)  # Access parameters

See also:
    shimmer3r_gsr_bt.py — Main streaming script
    ../matlab/params/params_shimmer3r.m — Phase 1 MATLAB equivalent
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Shimmer3RParams:
    """Acquisition parameters for Shimmer3R GSR+PPG streaming."""
    
    # =========================================================================
    # DEVICE CONFIGURATION
    # =========================================================================
    
    #: Windows COM port for Shimmer3R streaming (found via Device Manager)
    #: After pairing, Shimmer3R creates two COM ports:
    #:   - Lower number (e.g., COM4): Bootloader (firmware updates)
    #:   - Higher number (e.g., COM5): Streaming (LogAndStream protocol) ← USE THIS
    COM_PORT: str = 'COM5'
    
    #: Shimmer3R device identifier (4 characters printed on back of unit)
    #: Used in LSL device metadata and log file naming
    DEVICE_LABEL: str = 'BE7E'
    
    #: Bluetooth MAC address (optional, for pyshimmer direct connection)
    #: Format: "00:06:66:AB:CD:EF" (leave empty to use COM port)
    DEVICE_MAC_ADDRESS: Optional[str] = None
    
    # =========================================================================
    # ACQUISITION PARAMETERS
    # =========================================================================
    
    #: Sampling rate in Hz
    #: Reference: Bent, B. & Dunn, J.P. (2021). Optimizing sampling rate of
    #: wrist-worn optical sensors for physiologic monitoring. Journal of Clinical
    #: and Translational Science, 5, e34, 1–8. doi: 10.1017/cts.2020.526
    #: Recommendation: 64 Hz for wrist-worn PPG
    SAMPLING_RATE_HZ: int = 64
    
    #: Total recording duration in seconds
    #: Set to float('inf') for indefinite recording (stop manually)
    CAPTURE_DURATION_S: float = 300.0
    
    # =========================================================================
    # SUBJECT IDENTIFICATION
    # =========================================================================
    
    #: Subject identifier string. Embedded in output CSV filename.
    SUBJECT_ID: str = 'subj01'
    
    # =========================================================================
    # FILE PATHS
    # =========================================================================
    
    #: Directory where CSV data files and verification plots are saved.
    #: Relative paths are resolved from the directory containing this file.
    OUTPUT_DIR: str = './data/'
    
    # =========================================================================
    # LSL STREAMING
    # =========================================================================
    
    #: LSL stream name (inlet clients resolve streams by this name)
    #: Must match Phase 1 for compatibility
    LSL_STREAM_NAME: str = 'Shimmer3R_GSR_PPG'
    
    #: LSL source ID string. Must be unique per device on the network.
    LSL_SOURCE_ID: str = 'shimmer3r_001'
    
    #: LSL device name for metadata (matches Phase 1)
    LSL_DEVICE_NAME: str = 'Shimmer3-GSR+'
    
    # =========================================================================
    # PPG FILTER PARAMETERS
    # =========================================================================
    
    #: PPG low-pass filter corner frequency in Hz.
    #: 5 Hz is standard for photoplethysmography: preserves heart-rate band
    #: (~0.5–3 Hz) while attenuating high-frequency noise and motion artifacts.
    #: Reference: Bent & Dunn (2021)
    FCLP_PPG_HZ: float = 5.0
    
    #: Chebyshev filter order (number of poles) for PPG LPF.
    #: Must be even. 2 poles = gentle roll-off, minimal phase distortion.
    N_POLES_PPG: int = 2
    
    #: Passband ripple for Chebyshev filter design, in percent.
    PB_RIPPLE_PCT: float = 0.5
    
    # =========================================================================
    # TIMING PARAMETERS
    # =========================================================================
    
    #: Maximum wait time for Bluetooth connection to establish, in seconds.
    CONNECTION_TIMEOUT_S: int = 60
    
    #: Polling interval between data-read operations, in seconds.
    #: Must be >= 0.2 to allow data to accumulate in buffer and prevent
    #: serial port hanging.
    DELAY_PERIOD_S: float = 0.2
    
    #: Pause duration after device configuration, in seconds.
    #: The device requires time to process sensor configuration.
    #: Minimum 20 s based on Shimmer-MATLAB-ID examples.
    CONFIG_PAUSE_S: float = 20.0
    
    # =========================================================================
    # HARDWARE CONFIGURATION
    # =========================================================================
    
    #: Hardware version string for channel name mapping
    #: Shimmer3R: PPG on 'PPG_A1'
    #: Shimmer3:  PPG on 'PPG_A13' (fallback)
    HARDWARE_VERSION: str = 'Shimmer3R'
    
    #: GSR sensor range (kohm)
    #: SR48 GSR+ board supports multiple ranges:
    #:   10kΩ, 22kΩ, 47kΩ, 100kΩ, 220kΩ, 470kΩ, 1MΩ, 4.7MΩ
    #: Default: 47kΩ (covers typical skin resistance 47kΩ–1MΩ)
    GSR_RANGE_KOHM: int = 47
    
    # =========================================================================
    # VERBOSITY & DEBUG
    # =========================================================================
    
    #: Enable verbose console output during acquisition
    VERBOSE: bool = True
    
    #: Enable debug logging to file
    DEBUG_LOG: bool = False
    
    #: Log file path (if DEBUG_LOG is True)
    DEBUG_LOG_PATH: Optional[str] = None


# Create singleton instance for easy import
PARAMS = Shimmer3RParams()


# =============================================================================
# MAIN (for testing)
# =============================================================================

if __name__ == '__main__':
    """Print all parameters for verification."""
    print("\n" + "="*70)
    print("Shimmer3R Acquisition Parameters")
    print("="*70 + "\n")
    
    for field_name, field_value in vars(PARAMS).items():
        if not field_name.startswith('_'):
            print(f"{field_name:<30} = {field_value}")
    
    print("\n" + "="*70)
    print(f"Total: {len([f for f in vars(PARAMS) if not f.startswith('_')])} parameters")
    print("="*70 + "\n")
