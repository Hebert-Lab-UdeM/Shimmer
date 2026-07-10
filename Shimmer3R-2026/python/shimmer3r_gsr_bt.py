"""
shimmer3r_gsr_bt.py — Main acquisition script for Shimmer3R GSR+PPG streaming.

This script streams EDA (GSR) and PPG from a Shimmer3R device over
Classic Bluetooth RFCOMM, applies online filtering to PPG, and outputs
data to both LSL and CSV simultaneously.

This is the Phase 2 Python implementation, providing equivalent
functionality to the Phase 1 MATLAB StreamShimmer3R.m script.

Usage:
    python shimmer3r_gsr_bt.py
    
    # Or with custom parameters:
    python shimmer3r_gsr_bt.py --com-port COM5 --subject subj01 --duration 300

Requirements:
    - pyshimmer >= 1.0.0
    - pylsl >= 1.16.0
    - scipy >= 1.11.0
    - numpy >= 1.24.0

See also:
    params_shimmer3r.py — Acquisition parameters
    shimmer_connection.py — Device connection
    shimmer_sensors.py — Sensor configuration
    shimmer_filter.py — PPG filtering
    shimmer_lsl.py — LSL streaming
    shimmer_csv.py — CSV output
"""

import sys
import time
import argparse
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

# Import Phase 2 modules
from params_shimmer3r import PARAMS
from shimmer_connection import ShimmerConnectionManager, ShimmerConnection
from shimmer_sensors import configure_sensors, poll_data_chunk, SensorConfig
from shimmer_filter import create_ppg_filter, PPGFilter
from shimmer_lsl import create_lsl_outlet, push_lsl_chunk, LSLOutletManager
from shimmer_csv import ShimmerCSVWriter


def parse_args():
    """Parse command-line arguments."""
    
    parser = argparse.ArgumentParser(
        description='Stream EDA and PPG from Shimmer3R over Bluetooth',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    
    parser.add_argument(
        '--com-port',
        type=str,
        default=PARAMS.COM_PORT,
        help=f'COM port for Shimmer3R (default: {PARAMS.COM_PORT})'
    )
    parser.add_argument(
        '--subject',
        type=str,
        default=PARAMS.SUBJECT_ID,
        help=f'Subject ID (default: {PARAMS.SUBJECT_ID})'
    )
    parser.add_argument(
        '--duration',
        type=float,
        default=PARAMS.CAPTURE_DURATION_S,
        help=f'Recording duration in seconds (default: {PARAMS.CAPTURE_DURATION_S})'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default=PARAMS.OUTPUT_DIR,
        help=f'Output directory (default: {PARAMS.OUTPUT_DIR})'
    )
    parser.add_argument(
        '--rate',
        type=float,
        default=PARAMS.SAMPLING_RATE_HZ,
        help=f'Sampling rate in Hz (default: {PARAMS.SAMPLING_RATE_HZ})'
    )
    parser.add_argument(
        '--no-lsl',
        action='store_true',
        help='Disable LSL streaming'
    )
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Suppress verbose output'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    return parser.parse_args()


def print_header():
    """Print acquisition header."""
    
    print("\n" + "="*70)
    print("Shimmer3R GSR+PPG Acquisition (Phase 2 - Python)")
    print("="*70 + "\n")


def print_configuration(args):
    """Print acquisition configuration."""
    
    print("Configuration:")
    print(f"  COM Port:        {args.com_port}")
    print(f"  Subject ID:      {args.subject}")
    print(f"  Duration:        {args.duration}s{' (infinite)' if args.duration == float('inf') else ''}")
    print(f"  Sampling Rate:   {args.rate} Hz")
    print(f"  Output Dir:      {args.output_dir}")
    print(f"  LSL Streaming:   {'Disabled' if args.no_lsl else 'Enabled'}")
    print()


class AcquisitionSession:
    """
    Manages a complete Shimmer3R acquisition session.
    
    This class integrates all components (connection, sensors, filter,
    LSL, CSV) into a coherent acquisition workflow.
    
    Attributes:
        connection: ShimmerConnection object
        sensor_config: SensorConfig object
        ppg_filter: PPGFilter object
        lsl_outlet: LSL StreamOutlet (or None)
        csv_writer: ShimmerCSVWriter object
        n_samples: Total samples collected
        n_packets: Total data packets received
        start_time: Session start timestamp
    """
    
    def __init__(self, args):
        """
        Initialize acquisition session.
        
        Args:
            args: Command-line arguments from parse_args()
        """
        
        self.args = args
        self.verbose = not args.quiet
        self.debug = args.debug
        
        # Connection state
        self.connection: ShimmerConnection = None
        self.sensor_config: SensorConfig = None
        self.ppg_filter: PPGFilter = None
        self.lsl_outlet = None
        self.csv_writer: ShimmerCSVWriter = None
        
        # Acquisition state
        self.n_samples = 0
        self.n_packets = 0
        self.start_time = None
        self.expected_packets = 0
        
        # Packet tracking for reception rate
        self.packet_timestamps = []
    
    def connect(self) -> None:
        """Connect to Shimmer3R device."""
        
        if self.verbose:
            print("[Session] Connecting to device...")
        
        # Use context manager for connection
        # We'll keep it open by not exiting the context
        self.connection_manager = ShimmerConnectionManager(
            com_port=self.args.com_port,
            timeout_s=60,
            device_label=PARAMS.DEVICE_LABEL,
            verbose=self.verbose,
        )
        
        # Enter context (connects to device)
        self.connection = self.connection_manager.__enter__()
        
        if self.verbose:
            print(f"[Session] ✓ Connected to {self.connection.device_info.hardware_version}")
    
    def configure_sensors(self) -> None:
        """Configure EDA and PPG sensors."""
        
        if self.verbose:
            print("\n[Session] Configuring sensors...")
        
        self.sensor_config = configure_sensors(
            self.connection.shimmer,
            sampling_rate_hz=self.args.rate,
            verbose=self.verbose,
        )
        
        if self.verbose:
            print(f"[Session] ✓ Sensors configured: {self.sensor_config.sampling_rate_hz} Hz")
    
    def create_filter(self) -> None:
        """Create PPG low-pass filter."""
        
        if self.verbose:
            print("\n[Session] Creating PPG filter...")
        
        self.ppg_filter = create_ppg_filter(
            sampling_rate_hz=self.args.rate,
            corner_freq_hz=PARAMS.FCLP_PPG_HZ,
            order=PARAMS.N_POLES_PPG,
            ripple_pct=PARAMS.PB_RIPPLE_PCT,
        )
        
        if self.verbose:
            print(f"[Session] ✓ Filter created: {PARAMS.FCLP_PPG_HZ} Hz LPF, {PARAMS.N_POLES_PPG} poles")
    
    def create_lsl_outlet(self) -> None:
        """Create LSL outlet for streaming."""
        
        if self.args.no_lsl:
            if self.verbose:
                print("\n[Session] LSL streaming disabled")
            return
        
        if self.verbose:
            print("\n[Session] Creating LSL outlet...")
        
        self.lsl_outlet = create_lsl_outlet(
            stream_name=PARAMS.LSL_STREAM_NAME,
            sampling_rate_hz=self.args.rate,
            source_id=PARAMS.LSL_SOURCE_ID,
            device_name=PARAMS.LSL_DEVICE_NAME,
            device_label=PARAMS.DEVICE_LABEL,
            verbose=self.verbose,
        )
        
        if self.lsl_outlet:
            if self.verbose:
                print(f"[Session] ✓ LSL outlet created: {PARAMS.LSL_STREAM_NAME}")
        else:
            if self.verbose:
                print("[Session] ⚠ LSL not available — streaming disabled")
    
    def create_csv_writer(self) -> None:
        """Create CSV writer for data logging."""
        
        if self.verbose:
            print("\n[Session] Creating CSV writer...")
        
        self.csv_writer = ShimmerCSVWriter(
            output_dir=self.args.output_dir,
            subject_id=self.args.subject,
            verbose=self.verbose,
        )
        
        if self.verbose:
            print(f"[Session] ✓ CSV writer ready: {self.csv_writer.filename}")
    
    def run_acquisition(self) -> None:
        """
        Run the main acquisition loop.
        
        This method polls data from the device, filters PPG, writes to
        CSV, and streams to LSL until the duration is reached.
        """
        
        if self.verbose:
            print("\n" + "="*70)
            print("ACQUISITION")
            print("="*70 + "\n")
            print(f"Recording for {self.args.duration}s... (Ctrl+C to stop)\n")
        
        self.start_time = time.time()
        self.n_samples = 0
        self.n_packets = 0
        self.expected_packets = 0
        
        # Chunk size for polling (balance between latency and efficiency)
        chunk_duration_s = 0.5  # 500ms chunks
        chunk_samples = int(self.args.rate * chunk_duration_s)
        
        try:
            while True:
                # Check duration
                elapsed = time.time() - self.start_time
                if elapsed >= self.args.duration:
                    break
                
                # Calculate remaining time
                remaining = self.args.duration - elapsed
                chunk_dur = min(chunk_duration_s, remaining)
                
                # Poll data chunk from device
                # This blocks for chunk_dur seconds
                data = poll_data_chunk(
                    self.connection.shimmer,
                    duration_s=chunk_dur,
                    max_samples=int(self.args.rate * chunk_dur * 1.5),
                )
                
                n_samples = len(data['timestamps'])
                if n_samples == 0:
                    continue  # No data received
                
                self.n_packets += 1
                self.n_samples += n_samples
                self.expected_packets += int(self.args.rate * chunk_dur)
                
                # Extract data
                timestamps = np.array(data['timestamps'])
                eda = np.array(data['eda'])
                ppg_raw = np.array(data['ppg'])
                
                # Filter PPG
                ppg_filtered = self.ppg_filter.filter(ppg_raw)
                
                # Write to CSV
                self.csv_writer.write_chunk(timestamps, eda, ppg_raw, ppg_filtered)
                
                # Stream to LSL
                if self.lsl_outlet:
                    push_lsl_chunk(self.lsl_outlet, eda, ppg_filtered)
                
                # Progress update (every 5 seconds)
                if self.verbose and int(elapsed) % 5 == 0 and int(elapsed) > 0:
                    print(f"[Acquisition] {int(elapsed)}s / {int(self.args.duration)}s "
                          f"({self.n_samples} samples, {self.n_packets} packets)")
                
        except KeyboardInterrupt:
            if self.verbose:
                print("\n\n[Acquisition] Interrupted by user")
        
        # Final statistics
        total_duration = time.time() - self.start_time
        
        if self.verbose:
            print("\n" + "="*70)
            print("ACQUISITION COMPLETE")
            print("="*70 + "\n")
            print(f"Duration:        {total_duration:.1f}s")
            print(f"Samples:         {self.n_samples}")
            print(f"Packets:         {self.n_packets}")
            print(f"Expected:        {self.expected_packets}")
            
            # Packet reception rate
            if self.expected_packets > 0:
                reception_rate = (self.n_packets / self.expected_packets) * 100
                print(f"Reception Rate:  {reception_rate:.1f}%")
                
                if reception_rate < 80:
                    print(f"⚠ Warning: Low packet reception rate (<80%)")
                    print(f"  Check device proximity and Bluetooth interference")
    
    def close(self) -> None:
        """Clean up all resources."""
        
        if self.verbose:
            print("\n[Session] Closing resources...")
        
        # Close CSV writer
        if self.csv_writer:
            self.csv_writer.close()
        
        # Close LSL outlet
        # (handled by context manager if we used it)
        
        # Disconnect from device
        if self.connection_manager:
            self.connection_manager.__exit__(None, None, None)
        
        if self.verbose:
            print("[Session] ✓ All resources closed")
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        self.configure_sensors()
        self.create_filter()
        self.create_lsl_outlet()
        self.create_csv_writer()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False  # Don't suppress exceptions


def main():
    """Main entry point."""
    
    # Parse arguments
    args = parse_args()
    
    # Print header
    print_header()
    
    # Print configuration
    print_configuration(args)
    
    # Run acquisition session
    try:
        with AcquisitionSession(args) as session:
            session.run_acquisition()
        
        print("\n" + "="*70)
        print("✓ Acquisition completed successfully")
        print("="*70 + "\n")
        
    except Exception as e:
        print("\n" + "="*70)
        print("✗ Acquisition FAILED")
        print("="*70 + "\n")
        print(f"Error: {e}\n")
        
        if args.debug:
            import traceback
            traceback.print_exc()
        else:
            print("Run with --debug for stack trace")
            print("\nTroubleshooting:")
            print("  1. Ensure Shimmer3R is powered on (blue LED blinking)")
            print("  2. Verify COM port is correct (check Device Manager)")
            print("  3. Close other Shimmer software (MATLAB, Consensys)")
            print("  4. Try power cycling the device (hold 5s off, 2s on)")
            print("  5. Run with --debug for detailed error info")
        
        sys.exit(1)


if __name__ == '__main__':
    main()
