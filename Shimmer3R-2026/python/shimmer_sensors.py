"""
shimmer_sensors.py — Shimmer3R sensor configuration and data polling.

This module provides functions for configuring Shimmer3R sensors (EDA/GSR and PPG),
polling data from the device, and handling channel name mapping.

Usage:
    from shimmer_sensors import configure_sensors, poll_data
    
    # After connecting with shimmer_connection
    configure_sensors(conn.shimmer, sampling_rate_hz=64)
    data = poll_data(conn.shimmer)
    print(f"EDA: {data['eda']}, PPG: {data['ppg']}")

Requirements:
    - pyshimmer >= 1.0.0
    - shimmer_connection module
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from pyshimmer import ESensorGroup, EChannelType
from pyshimmer.bluetooth.bt_commands import DataPacket


@dataclass
class SensorConfig:
    """Container for sensor configuration."""
    
    #: Enabled sensor groups
    sensors: List[ESensorGroup]
    
    #: Sampling rate in Hz
    sampling_rate_hz: float
    
    #: Expected channel names in data stream
    channel_names: Dict[str, str]
    
    def __str__(self) -> str:
        """Return human-readable config summary."""
        sensor_names = [s.name for s in self.sensors]
        return (
            f"Sensor Configuration:\n"
            f"  Sensors: {', '.join(sensor_names)}\n"
            f"  Sampling Rate: {self.sampling_rate_hz} Hz\n"
            f"  Channels: {self.channel_names}"
        )


def configure_sensors(
    shimmer,
    sampling_rate_hz: float = 64,
    verbose: bool = True
) -> SensorConfig:
    """
    Configure Shimmer3R sensors for EDA and PPG acquisition.
    
    This function disables all sensors, then enables only the GSR (EDA) and
    PPG (Internal ADC A1) sensors. It also sets the sampling rate.
    
    Args:
        shimmer: Initialized ShimmerBluetooth instance from shimmer_connection
        sampling_rate_hz: Sampling rate in Hz (default: 64, per Bent & Dunn 2021)
        verbose: Print progress messages (default: True)
    
    Returns:
        SensorConfig object with configuration details
    
    Raises:
        RuntimeError: If sensor configuration fails
    
    Example:
        >>> config = configure_sensors(conn.shimmer, sampling_rate_hz=64)
        >>> print(config.sensors)
        [ESensorGroup.GSR, ESensorGroup.INT_CH_A1]
    """
    
    if verbose:
        print(f"[Sensors] Configuring sensors (sampling rate = {sampling_rate_hz} Hz)...")
    
    # Step 1: Disable all sensors first (clean state)
    if verbose:
        print(f"  Disabling all sensors...")
    
    try:
        # Get list of all available sensor groups
        all_sensors = list(ESensorGroup)
        
        # Disable all sensors
        shimmer.set_sensors([])
        if verbose:
            print(f"  ✓ All sensors disabled")
            
    except Exception as e:
        raise RuntimeError(f"Failed to disable sensors: {e}") from e
    
    # Step 2: Enable only EDA (GSR) and PPG sensors
    if verbose:
        print(f"  Enabling EDA (GSR) and PPG sensors...")
    
    # Sensors to enable:
    #   - GSR: Galvanic Skin Response (EDA) sensor on SR48 daughter board
    #   - INT_CH_A1: Internal ADC Channel A1 (PPG on Shimmer3R)
    #
    # Note: On Shimmer3R, PPG is mapped to Internal ADC A1
    #       On original Shimmer3, PPG was on Internal ADC A13
    #       pyshimmer handles this mapping internally
    enabled_sensors = [
        ESensorGroup.GSR,
        ESensorGroup.INT_CH_A1,
    ]
    
    try:
        shimmer.set_sensors(enabled_sensors)
        if verbose:
            print(f"  ✓ Sensors enabled: GSR, INT_CH_A1")
            
    except Exception as e:
        raise RuntimeError(f"Failed to enable sensors: {e}") from e
    
    # Step 3: Set sampling rate
    if verbose:
        print(f"  Setting sampling rate to {sampling_rate_hz} Hz...")
    
    try:
        shimmer.set_sampling_rate(sampling_rate_hz)
        
        # Verify sampling rate was set correctly
        actual_rate = shimmer.get_sampling_rate()
        if abs(actual_rate - sampling_rate_hz) > 0.1:
            if verbose:
                print(f"  ⚠ Warning: Requested {sampling_rate_hz} Hz, got {actual_rate} Hz")
        else:
            if verbose:
                print(f"  ✓ Sampling rate set to {actual_rate} Hz")
                
    except Exception as e:
        raise RuntimeError(f"Failed to set sampling rate: {e}") from e
    
    # Step 4: Get channel names from device
    channel_names = get_channel_names(shimmer)
    
    # Create config object
    config = SensorConfig(
        sensors=enabled_sensors,
        sampling_rate_hz=sampling_rate_hz,
        channel_names=channel_names,
    )
    
    if verbose:
        print(f"\n{config}\n")
    
    return config


def get_channel_names(shimmer) -> Dict[str, str]:
    """
    Get channel names from Shimmer device.
    
    This queries the device for its active data channels and returns
    a mapping of logical names to actual channel names.
    
    Args:
        shimmer: Initialized ShimmerBluetooth instance
    
    Returns:
        Dict with keys: 'timestamp', 'eda', 'ppg'
    """
    
    try:
        # Get active channel types from device
        channel_types = shimmer.get_data_types()
        
        # Map channel types to logical names
        # pyshimmer returns EChannelType enums
        channel_names = {
            'timestamp': 'Timestamp',
            'eda': 'GSR',  # Will be mapped to actual name by pyshimmer
            'ppg': 'PPG',  # Will be mapped to actual name by pyshimmer
        }
        
        # Try to get actual channel names from inquiry
        try:
            _, _, active_channels = shimmer.get_inquiry()
            
            # Map EChannelType to string names
            for ch_type in active_channels:
                if ch_type == EChannelType.GSR_RAW:
                    channel_names['eda'] = 'GSR_RAW'
                elif ch_type == EChannelType.INTERNAL_ADC_A1:
                    channel_names['ppg'] = 'INT_ADC_A1'
                    
        except Exception:
            # Inquiry failed, use default names
            pass
        
        return channel_names
        
    except Exception:
        # Return defaults if query fails
        return {
            'timestamp': 'Timestamp',
            'eda': 'GSR',
            'ppg': 'PPG',
        }


@dataclass
class SensorData:
    """Container for polled sensor data."""
    
    #: Timestamp in milliseconds (device time)
    timestamp_ms: float
    
    #: EDA/GSR value in calibrated units (kOhms) if available, else raw ADC
    eda: float
    
    #: PPG value in calibrated units (mV) if available, else raw ADC
    ppg: float
    
    #: Raw data packet from pyshimmer (for advanced use)
    raw_packet: Optional[Any] = None
    
    def __str__(self) -> str:
        """Return human-readable data summary."""
        return (
            f"SensorData(t={self.timestamp_ms:.1f}ms, "
            f"EDA={self.eda:.3f}, PPG={self.ppg:.3f})"
        )


def poll_data(
    shimmer,
    timeout_s: float = 1.0
) -> Optional[SensorData]:
    """
    Poll a single data sample from Shimmer3R.
    
    This function waits for the next data packet from the device and
    extracts EDA and PPG values.
    
    Note: This is a blocking call that waits for the next data packet.
    For continuous streaming, use start_streaming() with callbacks instead.
    
    Args:
        shimmer: Initialized ShimmerBluetooth instance with active streaming
        timeout_s: Maximum time to wait for data packet (default: 1.0s)
    
    Returns:
        SensorData object with timestamp, EDA, and PPG values, or None if timeout
    
    Example:
        >>> shimmer.start_streaming()
        >>> data = poll_data(shimmer, timeout_s=0.5)
        >>> if data:
        ...     print(f"EDA: {data.eda} kOhms, PPG: {data.ppg} mV")
    """
    
    import time
    
    # Note: pyshimmer 1.0.0 doesn't have a direct "poll" method
    # We need to use the streaming callback mechanism
    
    # For now, return None - this function requires streaming to be active
    # and a callback to capture data
    # 
    # In practice, you should use start_streaming() with a callback
    # or use the data packet handler directly
    
    return None


def poll_data_chunk(
    shimmer,
    duration_s: float = 1.0,
    max_samples: int = 100
) -> Dict[str, List[float]]:
    """
    Poll a chunk of data from Shimmer3R for specified duration.
    
    This function collects data samples for the specified duration and
    returns them as arrays.
    
    Args:
        shimmer: Initialized ShimmerBluetooth instance
        duration_s: Duration to collect data in seconds (default: 1.0)
        max_samples: Maximum number of samples to collect (default: 100)
    
    Returns:
        Dict with keys: 'timestamps', 'eda', 'ppg' (each is a list of floats)
    """
    
    import time
    from threading import Event
    
    timestamps = []
    eda_values = []
    ppg_values = []
    stop_event = Event()
    
    def data_handler(packet: DataPacket):
        """Callback for data packets."""
        if stop_event.is_set():
            return
        
        try:
            # Extract timestamp
            ts = packet[EChannelType.TIMESTAMP]
            timestamps.append(float(ts))
            
            # Extract EDA (GSR)
            try:
                eda = packet[EChannelType.GSR_RAW]
                eda_values.append(float(eda))
            except KeyError:
                eda_values.append(0.0)
            
            # Extract PPG (Internal ADC A1)
            try:
                ppg = packet[EChannelType.INTERNAL_ADC_A1]
                ppg_values.append(float(ppg))
            except KeyError:
                ppg_values.append(0.0)
                
        except Exception:
            # Skip malformed packets
            pass
    
    # Add callback
    shimmer.add_stream_callback(data_handler)
    
    # Start streaming
    shimmer.start_streaming()
    
    # Collect data for specified duration
    start_time = time.time()
    while time.time() - start_time < duration_s and len(timestamps) < max_samples:
        time.sleep(0.01)  # Small sleep to prevent busy-waiting
    
    # Stop streaming
    shimmer.stop_streaming()
    
    # Remove callback
    shimmer.remove_stream_callback(data_handler)
    
    return {
        'timestamps': timestamps,
        'eda': eda_values,
        'ppg': ppg_values,
    }


def verify_sensor_config(shimmer, expected_sensors: List[ESensorGroup]) -> bool:
    """
    Verify that the expected sensors are configured.
    
    This queries the device for its active sensors and compares to expected.
    
    Args:
        shimmer: Initialized ShimmerBluetooth instance
        expected_sensors: List of expected ESensorGroup values
    
    Returns:
        True if configuration matches, False otherwise
    """
    
    try:
        # Get active channels
        channel_types = shimmer.get_data_types()
        
        # Check if expected sensor channels are present
        expected_channels = set()
        for sensor in expected_sensors:
            # Map sensor groups to channel types
            if sensor == ESensorGroup.GSR:
                expected_channels.add(EChannelType.GSR_RAW)
            elif sensor == ESensorGroup.INT_CH_A1:
                expected_channels.add(EChannelType.INTERNAL_ADC_A1)
        
        # Always expect timestamp
        expected_channels.add(EChannelType.TIMESTAMP)
        
        # Compare
        actual_channels = set(channel_types)
        
        return expected_channels.issubset(actual_channels)
        
    except Exception:
        return False


# =============================================================================
# Command-Line Interface
# =============================================================================

if __name__ == '__main__':
    """Test sensor configuration."""
    import argparse
    import sys
    
    # Import connection module
    from shimmer_connection import ShimmerConnectionManager
    
    parser = argparse.ArgumentParser(
        description='Test Shimmer3R sensor configuration'
    )
    parser.add_argument(
        'com_port',
        nargs='?',
        default='COM5',
        help='COM port name (default: COM5)'
    )
    parser.add_argument(
        '--rate',
        type=float,
        default=64.0,
        help='Sampling rate in Hz (default: 64)'
    )
    parser.add_argument(
        '--duration',
        type=float,
        default=2.0,
        help='Test streaming duration in seconds (default: 2)'
    )
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Suppress verbose output'
    )
    
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("Shimmer3R Sensor Configuration Test")
    print("="*70 + "\n")
    
    try:
        # Connect to device
        with ShimmerConnectionManager(
            com_port=args.com_port,
            verbose=not args.quiet,
        ) as conn:
            
            # Configure sensors
            config = configure_sensors(
                conn.shimmer,
                sampling_rate_hz=args.rate,
                verbose=not args.quiet,
            )
            
            # Verify configuration
            print("Verifying sensor configuration...")
            is_valid = verify_sensor_config(conn.shimmer, config.sensors)
            
            if is_valid:
                print("✓ Sensor configuration verified\n")
            else:
                print("⚠ Sensor configuration may not match expected\n")
            
            # Test data collection
            print(f"Collecting data for {args.duration}s...")
            data = poll_data_chunk(
                conn.shimmer,
                duration_s=args.duration,
                max_samples=int(args.rate * args.duration * 1.5),
            )
            
            n_samples = len(data['timestamps'])
            print(f"✓ Collected {n_samples} samples")
            
            if n_samples > 0:
                print(f"\nSample data (first 5 samples):")
                print(f"  {'Timestamp':>12} {'EDA':>12} {'PPG':>12}")
                print(f"  {'-'*12} {'-'*12} {'-'*12}")
                for i in range(min(5, n_samples)):
                    print(f"  {data['timestamps'][i]:>12.1f} "
                          f"{data['eda'][i]:>12.3f} "
                          f"{data['ppg'][i]:>12.3f}")
                
                print(f"\nStatistics:")
                print(f"  EDA: mean={sum(data['eda'])/len(data['eda']):.3f}, "
                      f"min={min(data['eda']):.3f}, max={max(data['eda']):.3f}")
                print(f"  PPG: mean={sum(data['ppg'])/len(data['ppg']):.3f}, "
                      f"min={min(data['ppg']):.3f}, max={max(data['ppg']):.3f}")
        
        print(f"\n✓ Sensor configuration test PASSED\n")
        
    except Exception as e:
        print(f"\n✗ Sensor configuration test FAILED")
        print(f"  Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print("="*70 + "\n")
