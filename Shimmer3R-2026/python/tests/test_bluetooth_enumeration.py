"""
test_bluetooth_enumeration.py — Verify Bluetooth RFCOMM device enumeration for Shimmer3R.

This script tests that the Windows Bluetooth stack correctly exposes paired Shimmer3R
devices as COM ports accessible via pyserial.

Usage:
    python test_bluetooth_enumeration.py

Expected output:
    List of available COM ports with device names
    Identification of which COM port corresponds to Shimmer3R

Requirements:
    - Windows 10/11 with Bluetooth adapter
    - Shimmer3R paired via Windows Settings → Bluetooth & devices
    - pyserial installed (pip install -r requirements.txt)

Note:
    On Windows, pyserial handles RFCOMM natively; pybluez is NOT required.
    On Linux, rfcomm must bind the device before enumeration (see pyshimmer docs).
"""

import sys
import serial
import serial.tools.list_ports


def enumerate_com_ports():
    """List all available COM ports with metadata.
    
    Returns:
        tuple: (all_bluetooth_ports, shimmer_candidate_ports)
    """
    print("=" * 70)
    print("BLUETOOTH RFCOMM PORT ENUMERATION")
    print("=" * 70)
    
    ports = list(serial.tools.list_ports.comports())
    
    if not ports:
        print("\nNo COM ports found.")
        print("Ensure Bluetooth adapter is enabled and devices are paired.")
        return [], []
    
    print(f"\nFound {len(ports)} COM port(s):\n")
    
    bluetooth_ports = []
    shimmer_candidates = []
    
    for i, port in enumerate(ports, 1):
        # port.device: COM port name (e.g., 'COM7')
        # port.name: human-readable name
        # port.description: device description
        # port.hwid: hardware ID
        # port.location: physical location
        # port.vid: USB vendor ID (if applicable)
        # port.pid: USB product ID (if applicable)
        
        print(f"{i}. {port.device}")
        print(f"   Name:        {port.name}")
        print(f"   Description: {port.description}")
        print(f"   HWID:        {port.hwid}")
        
        # Check if this looks like a Bluetooth device
        is_bluetooth = False
        bluetooth_keywords = ['Bluetooth', 'BT', 'RFCOMM', 'Wireless']
        for kw in bluetooth_keywords:
            if kw in port.description or kw in port.hwid.upper():
                is_bluetooth = True
                break
        
        if is_bluetooth:
            print(f"   [BLUETOOTH PORT]")
            bluetooth_ports.append(port)
        
        # Check if this looks like a Shimmer device
        is_shimmer = False
        shimmer_keywords = ['SHIMMER', 'Shimmer', 'GSR', 'PPG', 'ExG']
        for keyword in shimmer_keywords:
            if keyword in port.name or keyword in port.description or keyword in port.hwid:
                is_shimmer = True
                print(f"   [SHIMMER LIKELY: matched '{keyword}']")
                break
        
        # Shimmer3R creates TWO COM ports: one for bootloader, one for streaming
        # If we see consecutive COM ports (e.g., COM4, COM5), both are likely Shimmer
        if is_bluetooth:
            shimmer_candidates.append(port)
            if not is_shimmer:
                print(f"   [POSSIBLE SHIMMER: Bluetooth port without explicit name]")
        
        print()
    
    return bluetooth_ports, shimmer_candidates


def test_shimmer_handshake(port_name: str, timeout: float = 2.0) -> tuple[bool, dict]:
    """Attempt to communicate with a Shimmer device on the given COM port.
    
    This sends Shimmer LogAndStream protocol commands and checks for valid responses.
    
    Args:
        port_name: COM port name (e.g., 'COM4')
        timeout: Serial timeout in seconds
        
    Returns:
        tuple: (success: bool, info: dict with device info if successful)
    """
    print(f"Testing {port_name} for Shimmer device...")
    
    try:
        # Standard baud rate for Shimmer LogAndStream firmware
        BAUD_RATE = 115200
        
        ser = serial.Serial(
            port=port_name,
            baudrate=BAUD_RATE,
            timeout=timeout,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
        )
        
        # Clear buffers
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        
        # Shimmer LogAndStream protocol: send CMD_GET_DEVICE_INFO (0x09)
        # This should return device information if it's a Shimmer
        # Command format: [command_byte]
        ser.write(b'\x09')
        
        # Wait for response
        # Shimmer should respond with: [ACK, command_id, data_length, data..., checksum]
        response = ser.read(100)  # Read up to 100 bytes
        
        ser.close()
        
        if len(response) >= 3:
            # Check if response starts with ACK (0x00 or 0x01 depending on firmware)
            if response[0] in [0x00, 0x01, 0x09]:
                print(f"  ✓ {port_name} responded with valid Shimmer protocol")
                print(f"    Response: {len(response)} bytes, first bytes: {response[:10].hex()}")
                
                # Try to extract hardware version from response
                # This is a simplified check; full parsing would require protocol knowledge
                info = {
                    'port': port_name,
                    'response_length': len(response),
                    'response_hex': response[:20].hex(),
                }
                return True, info
            else:
                print(f"  ⚠ {port_name} responded but not with Shimmer protocol (first byte: 0x{response[0]:02x})")
                return False, {}
        else:
            print(f"  ⚠ {port_name} opened but did not respond to Shimmer handshake")
            print(f"    (Device may be asleep, out of range, already connected, or not a Shimmer)")
            return False, {}
            
    except serial.SerialException as e:
        print(f"  ✗ Failed to open {port_name}: {e}")
        return False, {}
    except OSError as e:
        print(f"  ✗ OS error accessing {port_name}: {e}")
        return False, {}


def main():
    """Main test routine."""
    print("\nShimmer3R Phase 2 — Bluetooth Enumeration Test")
    print("=" * 70)
    print("\nNOTE: Windows labels all Bluetooth serial ports generically.")
    print("This test will try Shimmer protocol on each Bluetooth COM port")
    print("to identify which one(s) are Shimmer devices.\n")
    
    # Step 1: Enumerate all COM ports
    bluetooth_ports, shimmer_candidates = enumerate_com_ports()
    
    if not bluetooth_ports:
        print("\n⚠ WARNING: No Bluetooth COM ports detected.")
        print("\nTroubleshooting:")
        print("  1. Ensure Bluetooth adapter is enabled")
        print("  2. Pair the Shimmer3R via Windows Settings → Bluetooth & devices")
        print("  3. Check Device Manager → Ports (COM & LPT) for new entries")
        print("\nRetrying in 5 seconds...")
        import time
        time.sleep(5)
        bluetooth_ports, shimmer_candidates = enumerate_com_ports()
    
    if not bluetooth_ports:
        print("\n✗ No Bluetooth COM ports found after retry. Exiting.")
        sys.exit(1)
    
    print(f"\nFound {len(bluetooth_ports)} Bluetooth COM port(s).")
    print("Testing each for Shimmer LogAndStream protocol...\n")
    
    # Step 2: Test Shimmer handshake on all Bluetooth ports
    print("=" * 70)
    print("SHIMMER PROTOCOL HANDSHAKE TEST")
    print("=" * 70 + "\n")
    
    shimmer_ports = []
    for port in bluetooth_ports:
        success, info = test_shimmer_handshake(port.device)
        if success:
            shimmer_ports.append((port, info))
    
    # Step 3: Report results
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70 + "\n")
    
    if shimmer_ports:
        print(f"✓ Found {len(shimmer_ports)} Shimmer device(s):\n")
        for i, (port, info) in enumerate(shimmer_ports, 1):
            print(f"  {i}. {port.device}")
            print(f"     Description: {port.description}")
            print(f"     Response: {info['response_length']} bytes")
        
        print("\n✓ Bluetooth enumeration test PASSED")
        
        if len(shimmer_ports) >= 2:
            print("\nNOTE: Multiple Shimmer ports detected (typical for Shimmer3R).")
            print("  - Shimmer3R creates TWO COM ports:")
            print("    * Lower number: Bootloader (firmware updates)")
            print("    * Higher number: Streaming (LogAndStream protocol)")
            print("  - Use the HIGHER port number for streaming\n")
            streaming_port = max(shimmer_ports, key=lambda x: int(x[0].device.replace('COM', '')))
            print(f"  >>> RECOMMENDED FOR STREAMING: {streaming_port[0].device} <<<\n")
        
        print("Next steps:")
        print(f"  1. Update params_shimmer3r.py with COM_PORT = '{shimmer_ports[-1][0].device}'")
        print("  2. Run the main streaming script: python shimmer3r_gsr_bt.py")
        
    else:
        print("✗ No Shimmer devices detected on any Bluetooth COM port.")
        print("\nTroubleshooting:")
        print("  1. Ensure Shimmer3R is charged and powered on (LED should blink)")
        print("  2. Check that the device is within Bluetooth range (<10m)")
        print("  3. Verify no other application is using the COM port:")
        print("     - Close Consensys, MATLAB, or other Shimmer software")
        print("     - Check Task Manager for background processes")
        print("  4. Try unpairing and re-pairing the device:")
        print("     - Settings → Bluetooth & devices → Remove device")
        print("     - Power cycle Shimmer3R (hold button 5s)")
        print("     - Pair again")
        print("  5. Restart the Bluetooth service or reboot the PC")
        print("  6. Check Device Manager → Ports (COM & LPT) for error indicators")
        print("\nIf problems persist, try the pyshimmer-compat-notes.md troubleshooting guide.")
        sys.exit(1)
    
    print()


if __name__ == '__main__':
    main()
