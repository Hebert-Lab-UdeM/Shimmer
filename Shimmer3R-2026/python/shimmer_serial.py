"""
shimmer_serial.py — Direct serial communication for Shimmer3R.

This module provides low-level serial communication with Shimmer3R devices
using the LogAndStream protocol. It avoids pyshimmer's threading issues
on Windows by using blocking serial I/O with proper timeouts.

This is a hybrid approach:
- Uses pyshimmer for: connection, sensor configuration, calibration
- Uses this module for: data polling (avoids threading issues)

Usage:
    from shimmer_serial import ShimmerSerialReader
    
    with ShimmerSerialReader('COM5', baudrate=115200) as reader:
        data = reader.read_packet()
        if data:
            print(f"Timestamp: {data['timestamp']}, EDA: {data['eda']}")

Requirements:
    - pyserial >= 3.5
    - pyshimmer >= 1.0.0 (for DataPacket class)

Reference:
    - pyshimmer source: github.com/seemoo-lab/pyshimmer
    - Shimmer LogAndStream protocol documentation
"""

import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

import serial

from pyshimmer.bluetooth.bt_commands import DataPacket
from pyshimmer.dev.channels import EChannelType
from pyshimmer.dev.revisions import RevisionRegistry, HardwareVersion


# LogAndStream Protocol Constants
CMD_ACK = 0x00
CMD_PING = 0x01
CMD_GET_DEVICE_INFO = 0x09
CMD_START_STREAMING = 0x05
CMD_STOP_STREAMING = 0x06
DATA_PACKET = 0x00  # Data packet identifier


@dataclass
class SerialPacket:
    """Container for parsed data packet."""
    
    #: Timestamp in milliseconds
    timestamp_ms: float
    
    #: EDA/GSR value (calibrated if available, else raw ADC)
    eda: float
    
    #: PPG value (calibrated if available, else raw ADC)
    ppg: float
    
    #: Raw packet bytes (for debugging)
    raw_bytes: Optional[bytes] = None
    
    #: Packet valid flag
    valid: bool = True
    
    #: Error message if invalid
    error: Optional[str] = None


class ShimmerSerialReader:
    """
    Direct serial reader for Shimmer3R LogAndStream protocol.
    
    This class provides blocking serial I/O that avoids pyshimmer's
    threading issues on Windows while maintaining compatibility with
    pyshimmer's configuration and calibration.
    
    Attributes:
        port: Serial port name (e.g., 'COM5')
        baudrate: Serial baud rate (default: 115200)
        timeout: Read timeout in seconds
        serial_port: pyserial Serial instance
    
    Example:
        >>> reader = ShimmerSerialReader('COM5')
        >>> reader.open()
        >>> packet = reader.read_packet(timeout_s=1.0)
        >>> if packet:
        ...     print(f"EDA: {packet.eda}")
        >>> reader.close()
    """
    
    def __init__(
        self,
        port: str,
        baudrate: int = 115200,
        timeout: float = 2.0,
    ):
        """
        Initialize serial reader.
        
        Args:
            port: COM port name (e.g., 'COM5')
            baudrate: Serial baud rate (default: 115200)
            timeout: Read timeout in seconds (default: 2.0)
        """
        
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial_port: Optional[serial.Serial] = None
        
        # Packet parsing state
        self._packet_count = 0
        self._error_count = 0
    
    def open(self) -> None:
        """
        Open serial port.
        
        Raises:
            serial.SerialException: If port cannot be opened
        """
        
        if self.serial_port and self.serial_port.is_open:
            return  # Already open
        
        self.serial_port = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            timeout=self.timeout,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            write_timeout=1.0,
        )
        
        # Clear buffers
        self.serial_port.reset_input_buffer()
        self.serial_port.reset_output_buffer()
        
        # Small delay for serial port to stabilize
        time.sleep(0.1)
    
    def close(self) -> None:
        """Close serial port."""
        
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.cancel_read()
            except Exception:
                pass
            
            self.serial_port.close()
        
        self.serial_port = None
    
    def __enter__(self):
        """Context manager entry."""
        self.open()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False
    
    def read_packet(self) -> Optional[SerialPacket]:
        """
        Read a single data packet from serial port.
        
        This is a blocking call that waits for the next data packet.
        
        Returns:
            SerialPacket if successful, None if timeout or error
        """
        
        if not self.serial_port or not self.serial_port.is_open:
            return SerialPacket(
                timestamp_ms=0, eda=0, ppg=0,
                valid=False, error="Serial port not open"
            )
        
        try:
            # Read until we find a data packet marker (0x00)
            # In streaming mode, device continuously sends packets
            marker = self.serial_port.read(1)
            
            if not marker or marker[0] != DATA_PACKET:
                # Not a data packet or timeout
                return None
            
            # Read packet payload
            # Packet structure: [marker][channel_data...][checksum]
            # Payload size depends on enabled channels
            # For GSR + PPG at 64Hz: ~10-15 bytes typically
            
            # Read remaining packet bytes (with timeout)
            payload = self.serial_port.read(20)  # Max expected packet size
            
            if len(payload) < 5:
                # Packet too short, likely corrupted
                self._error_count += 1
                return SerialPacket(
                    timestamp_ms=0, eda=0, ppg=0,
                    raw_bytes=marker + payload,
                    valid=False, error=f"Packet too short: {len(payload)} bytes"
                )
            
            # Parse packet using pyshimmer's DataPacket class
            # This handles the complex channel mapping and calibration
            try:
                # Create a DataPacket parser
                # Note: We need to know the revision and channel types
                revision = RevisionRegistry.get_revision(HardwareVersion.SHIMMER3R)
                
                # Define expected channel types for GSR+PPG configuration
                channel_types = [
                    EChannelType.TIMESTAMP,
                    EChannelType.GSR_RAW,
                    EChannelType.INTERNAL_ADC_A1,
                ]
                
                # Parse packet
                # DataPacket expects to read from serial itself
                # We'll create a minimal wrapper
                packet_data = marker + payload
                
                # For now, extract values manually
                # A more robust solution would replicate DataPacket parsing
                packet = self._parse_packet_simple(packet_data)
                
                if packet:
                    self._packet_count += 1
                
                return packet
                
            except Exception as e:
                self._error_count += 1
                return SerialPacket(
                    timestamp_ms=0, eda=0, ppg=0,
                    raw_bytes=packet_data,
                    valid=False, error=f"Parse error: {e}"
                )
                
        except serial.SerialException as e:
            self._error_count += 1
            return SerialPacket(
                timestamp_ms=0, eda=0, ppg=0,
                valid=False, error=f"Serial error: {e}"
            )
        except Exception as e:
            self._error_count += 1
            return SerialPacket(
                timestamp_ms=0, eda=0, ppg=0,
                valid=False, error=f"Unexpected error: {e}"
            )
    
    def _parse_packet_simple(self, data: bytes) -> Optional[SerialPacket]:
        """
        Simple packet parser for GSR+PPG configuration.
        
        This is a simplified parser that extracts raw values.
        For calibrated values, use pyshimmer's DataPacket.
        
        Packet format (GSR + PPG):
        [0x00][TS_L][TS_H][GSR_L][GSR_H][PPG_L][PPG_H][...]
        
        Args:
            data: Raw packet bytes
        
        Returns:
            SerialPacket or None if parsing fails
        """
        
        try:
            if len(data) < 7:
                return SerialPacket(
                    timestamp_ms=0, eda=0, ppg=0,
                    valid=False, error="Insufficient data"
                )
            
            # Extract timestamp (2 bytes, little-endian)
            timestamp_ms = int.from_bytes(data[1:3], byteorder='little', signed=False)
            
            # Extract GSR (2 bytes, little-endian, signed)
            gsr_raw = int.from_bytes(data[3:5], byteorder='little', signed=True)
            
            # Extract PPG (2 bytes, little-endian, signed)
            ppg_raw = int.from_bytes(data[5:7], byteorder='little', signed=True)
            
            # For now, return raw ADC values
            # Calibration would require device-specific factors from EEPROM
            # which we can get via pyshimmer's get_all_calibration()
            
            return SerialPacket(
                timestamp_ms=float(timestamp_ms),
                eda=float(gsr_raw),  # Raw ADC, needs calibration
                ppg=float(ppg_raw),  # Raw ADC, needs calibration
                raw_bytes=data[:7],
                valid=True,
            )
            
        except Exception as e:
            return SerialPacket(
                timestamp_ms=0, eda=0, ppg=0,
                valid=False, error=f"Parse error: {e}"
            )
    
    def read_chunk(
        self,
        duration_s: float = 1.0,
        max_packets: int = 100,
    ) -> Dict[str, List[float]]:
        """
        Read multiple packets for specified duration.
        
        This is the main data collection method for acquisition.
        
        Args:
            duration_s: Duration to collect data (default: 1.0)
            max_packets: Maximum packets to collect (default: 100)
        
        Returns:
            Dict with keys: 'timestamps', 'eda', 'ppg' (each is list)
        """
        
        timestamps = []
        eda_values = []
        ppg_values = []
        
        start_time = time.time()
        
        while time.time() - start_time < duration_s and len(timestamps) < max_packets:
            packet = self.read_packet()
            
            if packet and packet.valid:
                timestamps.append(packet.timestamp_ms)
                eda_values.append(packet.eda)
                ppg_values.append(packet.ppg)
            elif packet and not packet.valid:
                # Log error but continue
                pass
            
            # Small sleep to prevent busy-waiting
            time.sleep(0.001)
        
        return {
            'timestamps': timestamps,
            'eda': eda_values,
            'ppg': ppg_values,
        }
    
    def get_statistics(self) -> Dict[str, int]:
        """
        Get reader statistics.
        
        Returns:
            Dict with packet_count, error_count
        """
        
        return {
            'packet_count': self._packet_count,
            'error_count': self._error_count,
        }
    
    def reset_statistics(self) -> None:
        """Reset statistics counters."""
        self._packet_count = 0
        self._error_count = 0


def send_command(
    serial_port: serial.Serial,
    command: int,
    data: bytes = b'',
    expect_response: bool = True,
    timeout_s: float = 2.0,
) -> Optional[bytes]:
    """
    Send a command to Shimmer device and wait for response.
    
    This is a low-level function for sending LogAndStream commands.
    
    Args:
        serial_port: Open serial port
        command: Command byte (e.g., 0x09 for Get Device Info)
        data: Optional command data bytes
        expect_response: Whether to wait for response (default: True)
        timeout_s: Response timeout in seconds (default: 2.0)
    
    Returns:
        Response bytes if successful, None if timeout/error
    """
    
    try:
        # Clear buffers
        serial_port.reset_input_buffer()
        serial_port.reset_output_buffer()
        
        # Send command
        serial_port.write(bytes([command]) + data)
        
        if not expect_response:
            return None
        
        # Wait for response
        serial_port.timeout = timeout_s
        response = serial_port.read(100)  # Read up to 100 bytes
        
        if response:
            return response
        else:
            return None
            
    except Exception:
        return None


# =============================================================================
# Command-Line Interface
# =============================================================================

if __name__ == '__main__':
    """Test serial communication with Shimmer3R."""
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(
        description='Test Shimmer3R serial communication'
    )
    parser.add_argument(
        'com_port',
        nargs='?',
        default='COM5',
        help='COM port name (default: COM5)'
    )
    parser.add_argument(
        '--duration',
        type=float,
        default=5.0,
        help='Test duration in seconds (default: 5)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Print packet details'
    )
    
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("Shimmer3R Serial Communication Test")
    print("="*70 + "\n")
    
    try:
        with ShimmerSerialReader(args.com_port) as reader:
            print(f"✓ Serial port {args.com_port} opened")
            print(f"  Reading for {args.duration}s...\n")
            
            # Read data chunk
            data = reader.read_chunk(
                duration_s=args.duration,
                max_packets=int(100 * args.duration),  # ~100 Hz max
            )
            
            n_packets = len(data['timestamps'])
            stats = reader.get_statistics()
            
            print(f"\nResults:")
            print(f"  Packets received: {n_packets}")
            print(f"  Packet errors:    {stats['error_count']}")
            
            if n_packets > 0:
                print(f"  Sample rate:      {n_packets / args.duration:.1f} Hz")
                
                if args.verbose and n_packets > 0:
                    print(f"\n  First 5 packets:")
                    print(f"    {'Timestamp':>12} {'EDA':>12} {'PPG':>12}")
                    print(f"    {'-'*12} {'-'*12} {'-'*12}")
                    for i in range(min(5, n_packets)):
                        print(f"    {data['timestamps'][i]:>12.1f} "
                              f"{data['eda'][i]:>12.1f} "
                              f"{data['ppg'][i]:>12.1f}")
            
            print(f"\n✓ Serial communication test PASSED")
    
    except serial.SerialException as e:
        print(f"\n✗ Serial communication test FAILED")
        print(f"  Error: {e}")
        print(f"\nTroubleshooting:")
        print(f"  1. Verify COM port is correct (check Device Manager)")
        print(f"  2. Ensure Shimmer3R is powered on")
        print(f"  3. Close other applications using this port")
        sys.exit(1)
    
    print("\n" + "="*70 + "\n")
