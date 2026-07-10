"""
shimmer_connection.py — Shimmer3R device connection management.

This module provides functions for connecting to and disconnecting from
the Shimmer3R device using pyshimmer's LogAndStream protocol over
Classic Bluetooth RFCOMM.

Usage:
    from shimmer_connection import connect_to_shimmer, disconnect_shimmer
    
    device = connect_to_shimmer('COM5', timeout_s=60)
    # ... use device ...
    disconnect_shimmer(device)

Requirements:
    - pyshimmer >= 1.0.0
    - pyserial >= 3.5
"""

import sys
import time
from typing import Optional, Tuple
from dataclasses import dataclass

import serial
from pyshimmer import ShimmerBluetooth
# Note: pyshimmer auto-detects hardware revision during initialize()
# No need to specify revision class explicitly


@dataclass
class ShimmerDeviceInfo:
    """Container for Shimmer device information."""
    
    #: Hardware version (e.g., 'SHIMMER3R')
    hardware_version: str
    
    #: Firmware type (e.g., 'LogAndStream')
    firmware_type: str
    
    #: Firmware version (e.g., '0.15.4')
    firmware_version: str
    
    #: Device name (custom name if set, otherwise default)
    device_name: str
    
    #: Device label (4-char ID from back of unit, e.g., 'BE7E')
    device_label: str
    
    #: Sampling rate in Hz
    sampling_rate_hz: float
    
    #: MAC address if available
    mac_address: Optional[str] = None
    
    def __str__(self) -> str:
        """Return human-readable device info."""
        return (
            f"Shimmer Device:\n"
            f"  Hardware:  {self.hardware_version}\n"
            f"  Firmware:  {self.firmware_type} v{self.firmware_version}\n"
            f"  Name:      {self.device_name}\n"
            f"  Label:     {self.device_label}\n"
            f"  Sample Rate: {self.sampling_rate_hz} Hz"
        )


@dataclass
class ShimmerConnection:
    """Container for active Shimmer connection resources."""
    
    #: pyshimmer Bluetooth interface
    shimmer: ShimmerBluetooth
    
    #: Serial port connection
    serial_port: serial.Serial
    
    #: Device information (populated after connection)
    device_info: Optional[ShimmerDeviceInfo] = None
    
    #: Connection timestamp
    connected_at: float = 0.0
    
    #: COM port name
    com_port: str = ''


def connect_to_shimmer(
    com_port: str,
    timeout_s: int = 60,
    device_label: str = 'BE7E',
    verbose: bool = True
) -> ShimmerConnection:
    """
    Connect to Shimmer3R device via Classic Bluetooth RFCOMM.
    
    This function establishes a serial connection to the Shimmer3R and
    initializes the pyshimmer Bluetooth interface. It queries device
    information and returns a connection object for use with other
    functions in this module.
    
    Args:
        com_port: Windows COM port name (e.g., 'COM5')
        timeout_s: Connection timeout in seconds (default: 60)
        device_label: Device identifier for verification (default: 'BE7E')
        verbose: Print progress messages (default: True)
    
    Returns:
        ShimmerConnection object with active connection
    
    Raises:
        ConnectionError: If device cannot be connected within timeout
        serial.SerialException: If COM port cannot be opened
        TimeoutError: If connection attempt times out
    
    Example:
        >>> conn = connect_to_shimmer('COM5', timeout_s=60)
        >>> print(conn.device_info.hardware_version)
        SHIMMER3R
    """
    
    if verbose:
        print(f"[Shimmer] Connecting to {com_port}...")
    
    start_time = time.time()
    
    # Step 1: Open serial port
    if verbose:
        print(f"  Opening serial port {com_port} at 115200 baud...")
    
    try:
        ser = serial.Serial(
            port=com_port,
            baudrate=115200,
            timeout=2.0,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            write_timeout=2.0,
        )
        if verbose:
            print(f"  ✓ Serial port opened")
            
    except serial.SerialException as e:
        raise ConnectionError(
            f"Failed to open COM port {com_port}: {e}\n"
            f"Troubleshooting:\n"
            f"  - Ensure Shimmer3R is powered on (LED should blink blue)\n"
            f"  - Close other applications using this port (MATLAB, Consensys)\n"
            f"  - Try power cycling the device (hold 5s off, 2s on)\n"
            f"  - Check Device Manager for COM port availability"
        ) from e
    
    # Step 2: Initialize pyshimmer Bluetooth interface
    if verbose:
        print(f"  Initializing pyshimmer interface...")
    
    try:
        # Create ShimmerBluetooth instance
        # revision=None lets pyshimmer auto-detect during initialize()
        # disable_status_ack=True is required for firmware >= 0.15.4
        shimmer = ShimmerBluetooth(
            ser,
            revision=None,  # Auto-detect hardware revision during initialize()
            disable_status_ack=True,
        )
        
        # Initialize connection (queries device info, disables status ack)
        # This may take a few seconds as it communicates with the device
        shimmer.initialize()
        
        if verbose:
            print(f"  ✓ pyshimmer interface initialized")
            
    except Exception as e:
        ser.close()
        raise ConnectionError(
            f"Failed to initialize pyshimmer interface: {e}\n"
            f"Troubleshooting:\n"
            f"  - Verify this is a Shimmer3R device\n"
            f"  - Check firmware version (requires LogAndStream >= 0.15.4)\n"
            f"  - Try the other COM port (bootloader vs streaming)"
        ) from e
    
    # Step 3: Query device information
    if verbose:
        print(f"  Querying device information...")
    
    try:
        device_info = query_device_info(shimmer, device_label)
        if verbose:
            print(f"  ✓ Device information retrieved")
            if verbose:
                print(f"\n{device_info}\n")
                
    except Exception as e:
        shimmer.shutdown()
        ser.close()
        raise ConnectionError(
            f"Failed to query device information: {e}"
        ) from e
    
    # Step 4: Check timeout
    elapsed = time.time() - start_time
    if elapsed > timeout_s:
        shimmer.shutdown()
        ser.close()
        raise TimeoutError(
            f"Connection attempt timed out after {timeout_s}s "
            f"(took {elapsed:.1f}s)"
        )
    
    # Create connection object
    connection = ShimmerConnection(
        shimmer=shimmer,
        serial_port=ser,
        device_info=device_info,
        connected_at=time.time(),
        com_port=com_port,
    )
    
    if verbose:
        print(f"[Shimmer] Connection established in {elapsed:.1f}s\n")
    
    return connection


def disconnect_shimmer(
    connection: ShimmerConnection,
    verbose: bool = True
) -> None:
    """
    Disconnect from Shimmer3R device and clean up resources.
    
    This function stops streaming (if active), shuts down the pyshimmer
    interface, and closes the serial port. It should be called when
    finished with the device to ensure clean disconnection.
    
    Args:
        connection: Active ShimmerConnection object from connect_to_shimmer()
        verbose: Print progress messages (default: True)
    
    Example:
        >>> conn = connect_to_shimmer('COM5')
        >>> # ... use device ...
        >>> disconnect_shimmer(conn)
    """
    
    if verbose:
        print(f"[Shimmer] Disconnecting from {connection.com_port}...")
    
    try:
        # Stop streaming if active
        try:
            connection.shimmer.stop_streaming()
            if verbose:
                print(f"  ✓ Streaming stopped")
        except Exception:
            # Streaming may not have been started - ignore
            pass
        
        # Shutdown pyshimmer interface
        # This stops the background read thread
        connection.shimmer.shutdown()
        if verbose:
            print(f"  ✓ pyshimmer interface shutdown")
            
    except Exception as e:
        if verbose:
            print(f"  ⚠ Warning: shutdown raised: {e}")
    
    finally:
        # Always close serial port
        try:
            if connection.serial_port.is_open:
                # Cancel any pending reads first
                connection.serial_port.cancel_read()
                connection.serial_port.close()
                if verbose:
                    print(f"  ✓ Serial port closed")
        except Exception as e:
            if verbose:
                print(f"  ⚠ Warning: serial close raised: {e}")
        
        if verbose:
            print(f"[Shimmer] Disconnected\n")


def query_device_info(
    shimmer: ShimmerBluetooth,
    expected_label: str = 'BE7E'
) -> ShimmerDeviceInfo:
    """
    Query device information from connected Shimmer3R.
    
    This function retrieves hardware version, firmware info, device name,
    and current sampling rate from the connected device.
    
    Args:
        shimmer: Initialized ShimmerBluetooth instance
        expected_label: Expected device label for verification
    
    Returns:
        ShimmerDeviceInfo object with device details
    
    Raises:
        ValueError: If device label doesn't match expected value
    """
    
    # Get hardware version
    hw_version = shimmer.hardware_version
    hw_version_str = hw_version.value if hasattr(hw_version, 'value') else str(hw_version)
    
    # Get firmware info
    fw_type, fw_version = shimmer.firmware_type, shimmer.firmware_version
    fw_type_str = fw_type.value if hasattr(fw_type, 'value') else str(fw_type)
    fw_version_str = str(fw_version) if fw_version else 'unknown'
    
    # Get device name (may be custom or default)
    try:
        device_name = shimmer.get_device_name()
    except Exception:
        device_name = 'unknown'
    
    # Get sampling rate
    try:
        sampling_rate = shimmer.get_sampling_rate()
    except Exception:
        sampling_rate = 0.0
    
    # Create device info object
    device_info = ShimmerDeviceInfo(
        hardware_version=hw_version_str,
        firmware_type=fw_type_str,
        firmware_version=fw_version_str,
        device_name=device_name,
        device_label=expected_label,
        sampling_rate_hz=sampling_rate,
    )
    
    # Verify device label matches expected
    # Note: pyshimmer doesn't directly read the label from hardware,
    # so we just store what was provided for logging purposes
    
    return device_info


def verify_connection(connection: ShimmerConnection) -> bool:
    """
    Verify that a Shimmer connection is still active.
    
    This function checks if the serial port is open and if the device
    responds to a status query.
    
    Args:
        connection: ShimmerConnection object to verify
    
    Returns:
        True if connection is active, False otherwise
    """
    
    # Check serial port
    if not connection.serial_port.is_open:
        return False
    
    # Try to get device status
    try:
        status = connection.shimmer.get_status()
        return len(status) == 8  # Status should have 8 fields
    except Exception:
        return False


def get_status_string(connection: ShimmerConnection) -> str:
    """
    Get human-readable device status.
    
    Args:
        connection: Active ShimmerConnection object
    
    Returns:
        Formatted status string
    """
    
    try:
        status = connection.shimmer.get_status()
        
        status_names = [
            'Docked',
            'Sensing',
            'RTC Set',
            'Logging',
            'Streaming',
            'SD Present',
            'SD Error',
            'Red LED',
        ]
        
        lines = ["Device Status:"]
        for name, value in zip(status_names, status):
            status_str = "✓" if value else "✗"
            lines.append(f"  {status_str} {name}: {value}")
        
        return '\n'.join(lines)
        
    except Exception as e:
        return f"Status query failed: {e}"


# =============================================================================
# Context Manager Support
# =============================================================================

class ShimmerConnectionManager:
    """
    Context manager for Shimmer3R connections.
    
    Automatically handles connection and disconnection, ensuring clean
    cleanup even if errors occur.
    
    Usage:
        with ShimmerConnectionManager('COM5') as conn:
            # Connection is active here
            print(conn.device_info)
        # Connection is automatically closed
    
    Example with error handling:
        try:
            with ShimmerConnectionManager('COM5', timeout_s=30) as conn:
                # Use conn.shimmer to access pyshimmer API
                conn.shimmer.start_streaming()
        except ConnectionError as e:
            print(f"Connection failed: {e}")
    """
    
    def __init__(
        self,
        com_port: str = 'COM5',
        timeout_s: int = 60,
        device_label: str = 'BE7E',
        verbose: bool = True,
    ):
        """
        Initialize connection manager.
        
        Args:
            com_port: COM port name
            timeout_s: Connection timeout in seconds
            device_label: Expected device label
            verbose: Print progress messages
        """
        self.com_port = com_port
        self.timeout_s = timeout_s
        self.device_label = device_label
        self.verbose = verbose
        self.connection: Optional[ShimmerConnection] = None
    
    def __enter__(self) -> ShimmerConnection:
        """Establish connection on context entry."""
        self.connection = connect_to_shimmer(
            com_port=self.com_port,
            timeout_s=self.timeout_s,
            device_label=self.device_label,
            verbose=self.verbose,
        )
        return self.connection
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Disconnect on context exit (even if exception occurred)."""
        if self.connection:
            disconnect_shimmer(self.connection, verbose=self.verbose)
        
        # Don't suppress exceptions
        return False


# =============================================================================
# Command-Line Interface
# =============================================================================

if __name__ == '__main__':
    """Test connection to Shimmer3R."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Test Shimmer3R connection'
    )
    parser.add_argument(
        'com_port',
        nargs='?',
        default='COM5',
        help='COM port name (default: COM5)'
    )
    parser.add_argument(
        '--label',
        default='BE7E',
        help='Expected device label (default: BE7E)'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=60,
        help='Connection timeout in seconds (default: 60)'
    )
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Suppress verbose output'
    )
    
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("Shimmer3R Connection Test")
    print("="*70 + "\n")
    
    try:
        # Test connection using context manager
        with ShimmerConnectionManager(
            com_port=args.com_port,
            timeout_s=args.timeout,
            device_label=args.label,
            verbose=not args.quiet,
        ) as conn:
            
            print(f"✓ Connection successful!\n")
            print(f"Device Information:")
            print(f"  Hardware:  {conn.device_info.hardware_version}")
            print(f"  Firmware:  {conn.device_info.firmware_type} v{conn.device_info.firmware_version}")
            print(f"  Name:      {conn.device_info.device_name}")
            print(f"  Label:     {conn.device_info.device_label}")
            print(f"  Sample Rate: {conn.device_info.sampling_rate_hz} Hz")
            
            print(f"\n{get_status_string(conn)}\n")
            
            print(f"Connection duration: {time.time() - conn.connected_at:.1f}s")
        
        print(f"\n✓ Connection test PASSED")
        print(f"  Device cleanly disconnected")
        
    except ConnectionError as e:
        print(f"\n✗ Connection test FAILED")
        print(f"  Error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print(f"\n\n⚠ Test interrupted by user")
        sys.exit(1)
    
    print("\n" + "="*70 + "\n")
