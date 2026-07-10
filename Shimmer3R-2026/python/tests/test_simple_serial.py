"""
test_simple_serial.py — Minimal serial test for Shimmer3R COM ports.

This script just verifies that a COM port can be opened and closed cleanly.
It doesn't use pyshimmer's API (which has thread issues on Windows).

Usage:
    python test_simple_serial.py COM4
    python test_simple_serial.py COM5

Requirements:
    - pyserial installed (pip install -r requirements.txt)
"""

import sys
import serial
import time


def test_serial_port(com_port: str):
    """Test if a COM port can be opened and closed."""
    
    print(f"\n{'='*70}")
    print(f"TESTING SERIAL PORT: {com_port}")
    print(f"{'='*70}\n")
    
    try:
        # Try to open the port
        print(f"Opening {com_port} at 115200 baud...")
        ser = serial.Serial(
            port=com_port,
            baudrate=115200,
            timeout=1.0,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
        )
        print(f"✓ Port {com_port} opened successfully\n")
        
        # Clear buffers
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        
        # Wait briefly
        time.sleep(0.5)
        
        # Check if any data is available (should be none if device is idle)
        waiting = ser.in_waiting
        if waiting > 0:
            print(f"  Note: {waiting} bytes waiting in input buffer")
            ser.reset_input_buffer()
        
        # Try sending a simple byte (not a full protocol command)
        print(f"Sending test byte...")
        ser.write(b'\x00')
        time.sleep(0.2)
        
        # Try to read response (may be nothing)
        response = ser.read(10)
        if response:
            print(f"  Received {len(response)} bytes: {response.hex()}")
        else:
            print(f"  No response (this is OK)")
        
        # Close the port
        print(f"\nClosing port...")
        ser.close()
        print(f"✓ Port {com_port} closed successfully\n")
        
        print(f"{'='*70}")
        print(f"RESULT: {com_port} is accessible")
        print(f"{'='*70}\n")
        return True
        
    except serial.SerialException as e:
        print(f"\n✗ Serial error on {com_port}: {e}")
        print("\nThis usually means:")
        print("  - Another application is using this COM port")
        print("  - The device is not responding")
        print("  - Try the other COM port (Shimmer3R creates two)")
        return False
        
    except OSError as e:
        print(f"\n✗ OS error on {com_port}: {e}")
        print("  - Port may not exist or is disabled")
        return False
        
    except Exception as e:
        print(f"\n✗ Unexpected error on {com_port}: {e}")
        print(f"  Error type: {type(e).__name__}")
        return False


def main():
    """Main entry point."""
    print("\n" + "="*70)
    print("Simple Serial Port Test for Shimmer3R")
    print("="*70)
    print("\nThis test verifies that a COM port can be opened and closed.")
    print("It does NOT test the Shimmer protocol (use pyshimmer for that).")
    print("\nUsage: python test_simple_serial.py <COM_PORT>")
    print("Example: python test_simple_serial.py COM5\n")
    
    if len(sys.argv) < 2:
        print("⚠ No COM port specified!")
        print("\nAvailable COM ports on this system:")
        
        import serial.tools.list_ports
        ports = list(serial.tools.list_ports.comports())
        bluetooth_ports = []
        
        for i, port in enumerate(ports, 1):
            is_bt = 'Bluetooth' in port.description or 'BT' in port.hwid.upper()
            marker = "[BT]" if is_bt else ""
            print(f"  {i}. {port.device} - {port.description} {marker}")
            if is_bt:
                bluetooth_ports.append(port.device)
        
        if bluetooth_ports:
            print(f"\nBluetooth COM ports found: {', '.join(bluetooth_ports)}")
            print(f"\nTry testing the higher number first (usually the streaming port):")
            print(f"  python test_simple_serial.py {bluetooth_ports[-1]}")
        
        sys.exit(1)
    
    com_port = sys.argv[1].upper()
    
    if not com_port.startswith('COM'):
        print(f"\n⚠ Invalid COM port format: '{com_port}'")
        print("Expected format: COM4, COM5, etc.")
        sys.exit(1)
    
    success = test_serial_port(com_port)
    
    if success:
        print(f"\n✓ {com_port} is available for use")
        print(f"\nNext step: Update params_shimmer3r.py with COM_PORT = '{com_port}'")
    else:
        print(f"\n✗ {com_port} is not available")
        print("Try the other COM port or troubleshoot the connection")
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
