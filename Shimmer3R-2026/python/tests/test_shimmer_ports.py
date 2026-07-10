"""
test_shimmer_ports.py — Find and test Shimmer3R COM ports with timeout.

This script:
1. Finds all Bluetooth COM ports
2. Tests each one with a hard timeout (won't hang)
3. Identifies which port is the Shimmer streaming port

Usage:
    python test_shimmer_ports.py

Requirements:
    - pyserial installed
    - subprocess (stdlib)
"""

import sys
import serial
import serial.tools.list_ports
import time
import subprocess
import os


def find_bluetooth_com_ports():
    """Find all Bluetooth COM ports."""
    ports = list(serial.tools.list_ports.comports())
    bt_ports = []
    
    for port in ports:
        # Check if it's a Bluetooth port
        if 'Bluetooth' in port.description or 'Standard Serial' in port.description:
            bt_ports.append(port.device)
    
    return sorted(bt_ports, key=lambda x: int(x.replace('COM', '')))


def test_port_with_timeout(com_port: str, timeout_seconds: float = 3.0) -> dict:
    """Test a COM port using a subprocess with hard timeout.
    
    This avoids hanging by running the serial test in a separate process
    that gets killed if it takes too long.
    """
    
    # Create a minimal test script to run in subprocess
    test_script = f'''
import serial
import sys
import time

com_port = "{com_port}"
timeout = {timeout_seconds}

try:
    # Open port
    ser = serial.Serial(com_port, 115200, timeout=0.5)
    print(f"OPEN_OK", flush=True)
    
    # Clear buffers
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    time.sleep(0.1)
    
    # Send a byte
    ser.write(b'\\x00')
    time.sleep(0.1)
    
    # Try to read (with timeout)
    start = time.time()
    while time.time() - start < {timeout_seconds - 0.5}:
        if ser.in_waiting > 0:
            data = ser.read(ser.in_waiting)
            print(f"READ_OK:{{len(data)}}:{{data[:20].hex()}}", flush=True)
            break
    else:
        print(f"READ_TIMEOUT", flush=True)
    
    # Close
    ser.close()
    print(f"CLOSE_OK", flush=True)
    print("SUCCESS", flush=True)
    
except serial.SerialException as e:
    print(f"SERIAL_ERROR:{{e}}", flush=True)
    sys.exit(1)
except Exception as e:
    print(f"ERROR:{{type(e).__name__}}:{{e}}", flush=True)
    sys.exit(1)
'''
    
    # Run in subprocess with timeout
    try:
        result = subprocess.run(
            [sys.executable, '-c', test_script],
            capture_output=True,
            text=True,
            timeout=timeout_seconds + 2,  # Give 2s extra for process startup
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        
        output = result.stdout.strip().split('\n')
        
        return {
            'port': com_port,
            'success': result.returncode == 0,
            'output': output,
            'stderr': result.stderr.strip(),
        }
        
    except subprocess.TimeoutExpired:
        return {
            'port': com_port,
            'success': False,
            'output': ['TIMEOUT: Process killed after timeout'],
            'stderr': 'Test process hung and was killed',
        }


def main():
    """Main test routine."""
    print("\n" + "="*70)
    print("Shimmer3R COM Port Discovery Test")
    print("="*70)
    print("\nThis test finds Bluetooth COM ports and tests each one.")
    print("Each port gets 3 seconds max (won't hang).\n")
    
    # Find Bluetooth COM ports
    bt_ports = find_bluetooth_com_ports()
    
    if not bt_ports:
        print("✗ No Bluetooth COM ports found!")
        print("\nTroubleshooting:")
        print("  1. Ensure Bluetooth adapter is enabled")
        print("  2. Pair the Shimmer3R via Windows Settings")
        print("  3. Check Device Manager → Ports (COM & LPT)")
        sys.exit(1)
    
    print(f"Found {len(bt_ports)} Bluetooth COM port(s): {', '.join(bt_ports)}\n")
    
    # Test each port
    print("-"*70)
    print("TESTING PORTS")
    print("-"*70 + "\n")
    
    results = []
    for port in bt_ports:
        print(f"Testing {port}...")
        result = test_port_with_timeout(port, timeout_seconds=3.0)
        results.append(result)
        
        if result['success']:
            print(f"  ✓ {port} PASSED\n")
            for line in result['output']:
                print(f"    {line}")
            print()
        else:
            print(f"  ✗ {port} FAILED")
            for line in result['output']:
                print(f"    {line}")
            if result['stderr']:
                print(f"    stderr: {result['stderr']}")
            print()
    
    # Summary
    print("="*70)
    print("SUMMARY")
    print("="*70 + "\n")
    
    passed = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]
    
    if passed:
        print(f"✓ {len(passed)} port(s) passed:\n")
        for r in passed:
            print(f"  - {r['port']}")
        
        if len(passed) >= 2:
            print(f"\nNOTE: Shimmer3R creates TWO COM ports:")
            print(f"  - Lower number ({passed[0]['port']}): Bootloader")
            print(f"  - Higher number ({passed[-1]['port']}): Streaming ← USE THIS ONE")
        
        print(f"\n✓ SUCCESS: Use COM port '{passed[-1]['port']}' in params_shimmer3r.py")
        print(f"\nNext steps:")
        print(f"  1. Note the working COM port: {passed[-1]['port']}")
        print(f"  2. We'll create params_shimmer3r.py with this port")
        print(f"  3. Then test the full pyshimmer connection")
        
    else:
        print("✗ All ports failed")
        print("\nThis suggests:")
        print("  1. Shimmer3R is not powered on (LED should blink)")
        print("  2. Another application is using the COM port")
        print("     - Close MATLAB, Consensys, or other Shimmer software")
        print("     - Check Task Manager for background processes")
        print("  3. Shimmer3R needs to be power-cycled")
        print("     - Hold power button for 5 seconds")
        print("     - Wait for LED to blink")
        print("  4. Try unpairing and re-pairing the device")
        
        print("\nDetailed failure info:")
        for r in failed:
            print(f"\n  {r['port']}:")
            for line in r['output']:
                print(f"    {line}")
    
    print()


if __name__ == '__main__':
    main()
