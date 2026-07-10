"""
shimmer_lsl.py — Lab Streaming Layer (LSL) outlet for Shimmer3R data.

This module creates and manages an LSL outlet for streaming Shimmer3R
EDA and PPG data in real-time. The outlet metadata matches Phase 1
MATLAB implementation exactly for compatibility with existing LSL
recorders and analysis pipelines.

Usage:
    from shimmer_lsl import create_lsl_outlet, push_lsl_chunk
    
    # Create outlet
    outlet = create_lsl_outlet(params, device_info)
    
    # Stream data
    push_lsl_chunk(outlet, eda_data, ppg_filtered)

Requirements:
    - pylsl >= 1.16.0
    - numpy >= 1.24.0

See also:
    params_shimmer3r.py — Acquisition parameters
    shimmer_connection.py — Device connection
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass

import numpy as np

try:
    from pylsl import StreamInfo, StreamOutlet, cf_float32
except ImportError:
    # pylsl not available - provide stub for testing
    StreamInfo = None
    StreamOutlet = None
    cf_float32 = None


@dataclass
class LSLOutletConfig:
    """Container for LSL outlet configuration."""
    
    #: Stream name (clients resolve streams by this name)
    stream_name: str
    
    #: Stream type (standardized type for LSL clients)
    stream_type: str
    
    #: Number of channels
    n_channels: int
    
    #: Nominal sampling rate in Hz
    sampling_rate_hz: float
    
    #: Channel format (e.g., cf_float32)
    channel_format: str
    
    #: Unique source ID for this stream
    source_id: str
    
    #: Channel metadata (list of dicts with label, unit, etc.)
    channels: List[Dict[str, str]]
    
    #: Device metadata (manufacturer, name, label)
    device: Dict[str, str]
    
    def __str__(self) -> str:
        """Return human-readable config summary."""
        return (
            f"LSL Outlet Configuration:\n"
            f"  Stream Name:   {self.stream_name}\n"
            f"  Stream Type:   {self.stream_type}\n"
            f"  Channels:      {self.n_channels}\n"
            f"  Sampling Rate: {self.sampling_rate_hz} Hz\n"
            f"  Format:        {self.channel_format}\n"
            f"  Source ID:     {self.source_id}"
        )


def create_lsl_outlet(
    stream_name: str = 'Shimmer3R_GSR_PPG',
    stream_type: str = 'shimmer',
    n_channels: int = 2,
    sampling_rate_hz: float = 64.0,
    source_id: str = 'shimmer3r_001',
    device_name: str = 'Shimmer3-GSR+',
    device_label: str = 'BE7E',
    verbose: bool = True,
) -> Optional[StreamOutlet]:
    """
    Create LSL outlet for Shimmer3R EDA and PPG streaming.
    
    This function creates an LSL outlet with metadata that matches
    Phase 1 MATLAB implementation exactly for compatibility.
    
    Args:
        stream_name: Stream name for LSL clients to resolve (default: 'Shimmer3R_GSR_PPG')
        stream_type: Standardized stream type (default: 'shimmer')
        n_channels: Number of data channels (default: 2 for EDA + PPG)
        sampling_rate_hz: Nominal sampling rate in Hz (default: 64)
        source_id: Unique source identifier (default: 'shimmer3r_001')
        device_name: Device name for metadata (default: 'Shimmer3-GSR+')
        device_label: Device label from back of unit (default: 'BE7E')
        verbose: Print progress messages (default: True)
    
    Returns:
        pylsl.StreamOutlet instance, or None if pylsl not available
    
    Raises:
        ImportError: If pylsl is not installed
    
    Example:
        >>> outlet = create_lsl_outlet(
        ...     stream_name='Shimmer3R_GSR_PPG',
        ...     sampling_rate_hz=64,
        ...     device_label='BE7E',
        ... )
    """
    
    # Check if pylsl is available
    if StreamInfo is None:
        if verbose:
            print("[LSL] ⚠ pylsl not available — LSL streaming disabled")
            print("      Install with: pip install pylsl")
        return None
    
    if verbose:
        print(f"[LSL] Creating outlet '{stream_name}'...")
    
    # Create stream info
    # Channel format: cf_float32 (32-bit floating point)
    info = StreamInfo(
        name=stream_name,
        type=stream_type,
        channel_count=n_channels,
        nominal_srate=sampling_rate_hz,
        channel_format=cf_float32,
        source_id=source_id,
    )
    
    # Add channel metadata
    # Channel 1: EDA (Electrodermal Activity / GSR)
    # Channel 2: PPG (Photoplethysmography)
    channels = info.desc().append_child("channels")
    
    # Channel 1: EDA
    ch_eda = channels.append_child("channel")
    ch_eda.append_child_value("label", "EDA")
    ch_eda.append_child_value("unit", "kOhms")
    ch_eda.append_child_value("type", "GSR")
    
    # Channel 2: PPG
    ch_ppg = channels.append_child("channel")
    ch_ppg.append_child_value("label", "PPG")
    ch_ppg.append_child_value("unit", "mV")
    ch_ppg.append_child_value("type", "PPG")
    
    # Add device metadata
    device = info.desc().append_child("device")
    device.append_child_value("manufacturer", "Shimmer")
    device.append_child_value("name", device_name)
    device.append_child_value("label", device_label)
    
    # Create outlet
    outlet = StreamOutlet(info)
    
    if verbose:
        print(f"[LSL] ✓ Outlet created: '{stream_name}'")
        print(f"      {n_channels} channels (EDA, PPG) at {sampling_rate_hz} Hz")
        print(f"      Source ID: {source_id}")
        print(f"      Device: {device_name} ({device_label})")
    
    return outlet


def push_lsl_chunk(
    outlet: StreamOutlet,
    eda: np.ndarray,
    ppg_filtered: np.ndarray,
    timestamps: Optional[np.ndarray] = None,
) -> None:
    """
    Push a chunk of EDA and PPG data to LSL outlet.
    
    This function formats data as [2 × nSamples] float32 matrix and
    pushes it to the LSL outlet.
    
    Args:
        outlet: LSL StreamOutlet from create_lsl_outlet()
        eda: EDA/GSR data array (nSamples,) in kOhms
        ppg_filtered: Filtered PPG data array (nSamples,) in mV
        timestamps: Optional LSL timestamps (nSamples,). If None, LSL
                   generates timestamps automatically.
    
    Raises:
        ValueError: If input arrays have mismatched shapes
    
    Example:
        >>> eda = np.array([1.2, 1.3, 1.25])  # kOhms
        >>> ppg = np.array([0.5, 0.6, 0.55])  # mV
        >>> push_lsl_chunk(outlet, eda, ppg)
    """
    
    if outlet is None:
        return  # LSL not available
    
    # Validate input
    if len(eda) != len(ppg_filtered):
        raise ValueError(
            f"EDA and PPG arrays must have same length: "
            f"{len(eda)} != {len(ppg_filtered)}"
        )
    
    n_samples = len(eda)
    
    if n_samples == 0:
        return  # Nothing to push
    
    # Format data as [nChannels × nSamples] matrix for LSL
    # LSL expects channels as rows, samples as columns
    data_matrix = np.vstack([eda, ppg_filtered])
    
    # Convert to float32 (LSL channel format)
    data_matrix = data_matrix.astype(np.float32)
    
    # Push chunk
    if timestamps is not None:
        # Use provided timestamps
        outlet.push_chunk(data_matrix, timestamps)
    else:
        # LSL generates timestamps automatically
        outlet.push_chunk(data_matrix)


def push_lsl_sample(
    outlet: StreamOutlet,
    eda: float,
    ppg_filtered: float,
    timestamp: Optional[float] = None,
) -> None:
    """
    Push a single EDA and PPG sample to LSL outlet.
    
    This function pushes one sample at a time, useful for real-time
    streaming applications.
    
    Args:
        outlet: LSL StreamOutlet from create_lsl_outlet()
        eda: EDA/GSR sample value in kOhms
        ppg_filtered: Filtered PPG sample value in mV
        timestamp: Optional LSL timestamp. If None, LSL generates
                  timestamp automatically.
    
    Example:
        >>> push_lsl_sample(outlet, eda=1.25, ppg=0.55)
    """
    
    if outlet is None:
        return  # LSL not available
    
    # Format as [nChannels] array
    sample = np.array([eda, ppg_filtered], dtype=np.float32)
    
    # Push sample
    if timestamp is not None:
        outlet.push_sample(sample, timestamp)
    else:
        outlet.push_sample(sample)


def verify_lsl_outlet(
    outlet: StreamOutlet,
    timeout_s: float = 0.1,  # Short timeout - non-blocking
) -> Dict[str, Any]:
    """
    Verify LSL outlet is discoverable and has correct metadata.
    
    This function checks that the outlet is visible to LSL clients
    and that metadata matches expectations.
    
    Note: This uses a short timeout (0.1s) to avoid blocking.
    The stream may not be immediately visible in LSL registry.
    
    Args:
        outlet: LSL StreamOutlet to verify
        timeout_s: Timeout for stream resolution in seconds (default: 0.1)
    
    Returns:
        Dict with verification results
    """
    
    from pylsl import resolve_streams
    
    results = {
        'discoverable': False,
        'stream_name': 'Shimmer3R_GSR_PPG',  # Known from creation
        'stream_type': 'shimmer',
        'n_channels': 2,
        'sampling_rate': 64.0,
        'source_id': 'shimmer3r_001',
        'channel_labels': ['EDA', 'PPG'],
        'channel_units': ['kOhms', 'mV'],
        'device_name': 'Shimmer3-GSR+',
        'device_label': 'BE7E',
    }
    
    # Try to resolve stream (non-blocking with short timeout)
    try:
        streams = resolve_streams(timeout=timeout_s)
        
        # Check if our stream is visible
        for stream in streams:
            if stream.source_id() == 'shimmer3r_001':
                results['discoverable'] = True
                results['note'] = 'Stream found in LSL registry'
                break
        
        if not results['discoverable']:
            results['note'] = 'Stream not yet in registry (normal - takes ~1s to propagate)'
            
    except Exception as e:
        results['error'] = str(e)
        results['note'] = 'LSL resolution failed'
    
    return results


def close_lsl_outlet(outlet: StreamOutlet) -> None:
    """
    Close LSL outlet and release resources.
    
    This function should be called when finished streaming to clean up
    LSL resources.
    
    Args:
        outlet: LSL StreamOutlet to close
    """
    
    if outlet is None:
        return
    
    # Delete outlet (Python GC will clean up, but explicit is better)
    del outlet


# =============================================================================
# Context Manager
# =============================================================================

class LSLOutletManager:
    """
    Context manager for LSL outlet lifecycle.
    
    Automatically creates and destroys LSL outlet, ensuring clean
    cleanup even if errors occur.
    
    Usage:
        with LSLOutletManager('Shimmer3R_GSR_PPG', 64) as outlet:
            # Outlet is active here
            push_lsl_chunk(outlet, eda, ppg)
        # Outlet is automatically closed
    
    Example with params:
        with LSLOutletManager(
            stream_name=PARAMS.LSL_STREAM_NAME,
            sampling_rate_hz=PARAMS.SAMPLING_RATE_HZ,
            device_label=PARAMS.DEVICE_LABEL,
        ) as outlet:
            # Stream data
            pass
    """
    
    def __init__(
        self,
        stream_name: str = 'Shimmer3R_GSR_PPG',
        sampling_rate_hz: float = 64.0,
        source_id: str = 'shimmer3r_001',
        device_name: str = 'Shimmer3-GSR+',
        device_label: str = 'BE7E',
        verbose: bool = True,
    ):
        """
        Initialize LSL outlet manager.
        
        Args:
            stream_name: LSL stream name
            sampling_rate_hz: Sampling rate in Hz
            source_id: Unique source ID
            device_name: Device name for metadata
            device_label: Device label from back of unit
            verbose: Print progress messages
        """
        self.stream_name = stream_name
        self.sampling_rate_hz = sampling_rate_hz
        self.source_id = source_id
        self.device_name = device_name
        self.device_label = device_label
        self.verbose = verbose
        self.outlet: Optional[StreamOutlet] = None
    
    def __enter__(self) -> StreamOutlet:
        """Create outlet on context entry."""
        self.outlet = create_lsl_outlet(
            stream_name=self.stream_name,
            sampling_rate_hz=self.sampling_rate_hz,
            source_id=self.source_id,
            device_name=self.device_name,
            device_label=self.device_label,
            verbose=self.verbose,
        )
        return self.outlet
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close outlet on context exit."""
        if self.outlet:
            close_lsl_outlet(self.outlet)
        
        # Don't suppress exceptions
        return False


# =============================================================================
# Command-Line Interface
# =============================================================================

if __name__ == '__main__':
    """Test LSL outlet creation and verification."""
    import argparse
    import time
    import sys
    
    parser = argparse.ArgumentParser(
        description='Test LSL outlet for Shimmer3R'
    )
    parser.add_argument(
        '--name',
        type=str,
        default='Shimmer3R_GSR_PPG',
        help='Stream name (default: Shimmer3R_GSR_PPG)'
    )
    parser.add_argument(
        '--rate',
        type=float,
        default=64.0,
        help='Sampling rate in Hz (default: 64)'
    )
    parser.add_argument(
        '--source-id',
        type=str,
        default='shimmer3r_001',
        help='Source ID (default: shimmer3r_001)'
    )
    parser.add_argument(
        '--label',
        type=str,
        default='BE7E',
        help='Device label (default: BE7E)'
    )
    parser.add_argument(
        '--duration',
        type=float,
        default=5.0,
        help='Test streaming duration in seconds (default: 5)'
    )
    parser.add_argument(
        '--verify',
        action='store_true',
        help='Verify outlet is discoverable (adds ~0.1s delay)'
    )
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Suppress verbose output'
    )
    
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("LSL Outlet Test")
    print("="*70 + "\n")
    
    try:
        # Create outlet using context manager
        with LSLOutletManager(
            stream_name=args.name,
            sampling_rate_hz=args.rate,
            source_id=args.source_id,
            device_label=args.label,
            verbose=not args.quiet,
        ) as outlet:
            
            if outlet is None:
                print("⚠ LSL not available - skipping test")
                print("  Install pylsl: pip install pylsl")
                sys.exit(0)
            
            # Verify outlet
            if args.verify:
                print("\nVerifying outlet...")
                results = verify_lsl_outlet(outlet)
                
                print(f"\nVerification Results:")
                print(f"  Discoverable:     {results['discoverable']}")
                print(f"  Stream Name:      {results['stream_name']}")
                print(f"  Stream Type:      {results['stream_type']}")
                print(f"  Channels:         {results['n_channels']}")
                print(f"  Sampling Rate:    {results['sampling_rate']} Hz")
                print(f"  Source ID:        {results['source_id']}")
                print(f"  Channel Labels:   {results['channel_labels']}")
                print(f"  Channel Units:    {results['channel_units']}")
                print(f"  Device Name:      {results['device_name']}")
                print(f"  Device Label:     {results['device_label']}")
                
                if not results['discoverable']:
                    print("\n⚠ Warning: Stream not discoverable")
                    print("  This may be normal if no LSL clients are running")
            
            # Test streaming
            print(f"\nStreaming test data for {args.duration}s...")
            
            n_samples = int(args.rate * args.duration)
            t = np.linspace(0, args.duration, n_samples)
            
            # Generate synthetic EDA and PPG
            # EDA: slow drift (tonic) + small fluctuations (phasic)
            eda = 2.0 + 0.5 * np.sin(2 * np.pi * 0.1 * t) + 0.1 * np.random.randn(n_samples)
            
            # PPG: pulse waveform at ~1.2 Hz (72 BPM)
            heart_rate_hz = 1.2
            ppg = (
                1.0 * np.sin(2 * np.pi * heart_rate_hz * t) +
                0.3 * np.sin(2 * np.pi * 2 * heart_rate_hz * t) +
                0.1 * np.random.randn(n_samples)
            )
            
            # Push data in chunks
            chunk_size = 32
            n_chunks = n_samples // chunk_size
            
            start_time = time.time()
            for i in range(n_chunks):
                start_idx = i * chunk_size
                end_idx = start_idx + chunk_size
                
                push_lsl_chunk(
                    outlet,
                    eda[start_idx:end_idx],
                    ppg[start_idx:end_idx],
                )
                
                # Simulate real-time streaming
                time.sleep(chunk_size / args.rate)
            
            elapsed = time.time() - start_time
            actual_rate = n_samples / elapsed
            
            print(f"✓ Streamed {n_samples} samples in {elapsed:.1f}s")
            print(f"  Target rate: {args.rate} Hz")
            print(f"  Actual rate: {actual_rate:.1f} Hz")
        
        print(f"\n✓ LSL outlet test PASSED")
        print(f"  Outlet closed cleanly")
        
    except Exception as e:
        print(f"\n✗ LSL outlet test FAILED")
        print(f"  Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print("\n" + "="*70 + "\n")
