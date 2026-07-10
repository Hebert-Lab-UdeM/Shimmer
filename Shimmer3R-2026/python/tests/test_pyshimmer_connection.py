"""
test_pyshimmer_connection.py — Test pyshimmer connection to Shimmer3R.

This script uses pyshimmer's official API to connect to the Shimmer3R,
which properly handles the LogAndStream protocol.

Usage:
    python test_pyshimmer_connection.py COM4
    python test_pyshimmer_connection.py COM5
    
    (Replace COM4/COM5 with the actual COM port number from Device Manager)

Requirements:
    - pyshimmer installed (pip install -r requirements.txt)
    - Shimmer3R paired and powered on
    - No other application using the COM port (close MATLAB, Consensys, etc.)
"""

import sys
import serial
from pyshimmer import ShimmerBluetooth
from pyshimmer.dev.channels import ESensorGroup


def test_connection(com_port: str):
    """Test pyshimmer connection to Shimmer on the specified COM port."""
    
    print(f"\n{'='*70}")
    print(f"TESTING CONNECTION ON {com_port}")
    print(f"{'='*70}\n")
    
    try:
        # Open serial connection
        # Baud rate 115200 is standard for Shimmer LogAndStream firmware
        ser = serial.Serial(com_port, 115200, timeout=2.0)
        print(f"✓ Serial port {com_port} opened successfully")
        
    except serial.SerialException as e:
        print(f"✗ Failed to open {com_port}: {e}")
        print("\nThis usually means:")
        print("  - Another application is using this COM port")
        print("  - The port doesn't exist or is disabled")
        print("  - Permissions issue (try running as Administrator)")
        return False
    
    try:
        # Create pyshimmer Bluetooth interface
        print(f"Initializing pyshimmer Bluetooth interface...")
        shimmer = ShimmerBluetooth(ser)
        
        # Initialize connection (queries device info)
        print("Connecting to Shimmer device...")
        shimmer.initialize()
        print("✓ Connection established\n")
        
        # Get device information
        print("Device Information:")
        print(f"  Hardware Version: {shimmer.hardware_version}")
        print(f"  Firmware Type:    {shimmer.firmware_type}")
        print(f"  Firmware Version: {shimmer.firmware_version}")
        print(f"  Device Name:      {shimmer.get_device_name()}")
        
        # Get sampling rate
        sr = shimmer.get_sampling_rate()
        print(f"  Sampling Rate:    {sr} Hz")
        
        # Get status
        status = shimmer.get_status()
        print(f"\nDevice Status:")
        print(f"  Docked:      {status[0]}")
        print(f"  Sensing:     {status[1]}")
        print(f"  RTC Set:     {status[2]}")
        print(f"  Logging:     {status[3]}")
        print(f"  Streaming:   {status[4]}")
        print(f"  SD Present:  {status[5]}")
        print(f"  SD Error:    {status[6]}")
        print(f"  Red LED:     {status[7]}")
        
        # Try to configure sensors (GSR + PPG)
        print(f"\nConfiguring sensors (GSR + Internal ADC A1 for PPG)...")
        try:
            shimmer.set_sensors([ESensorGroup.GSR, ESensorGroup.INT_CH_A1])
            print("✓ Sensors configured successfully")
        except Exception as e:
            print(f"⚠ Sensor configuration failed: {e}")
            print("  This may indicate the sensor constants differ for Shimmer3R")
        
        # Try to start streaming (briefly)
        print(f"\nTesting data streaming (3 seconds)...")
        try:
            def data_handler(packet):
                # This callback fires for each data packet
                pass
            
            shimmer.add_stream_callback(data_handler)
            shimmer.start_streaming()
            print("✓ Streaming started")
            
            import time
            time.sleep(3)  # Reduced from 5 to 3 seconds
            
            shimmer.stop_streaming()
            print("✓ Streaming stopped successfully")
            
        except Exception as e:
            print(f"⚠ Streaming test failed: {e}")
            print("  (This is OK - connection test still passed)")
        
        # Clean shutdown
        print("\nShutting down...")
        try:
            shimmer.shutdown()
        except Exception as e:
            print(f"  Warning: shutdown() raised: {e}")
        
        # Force close serial if still open
        try:
            if ser.is_open:
                ser.cancel_read()
                ser.close()
                print("✓ Serial port closed")
        except Exception as e:
            print(f"  Warning: failed to close serial: {e}")
        
        print("\n✓ Test complete")
        
        print(f"\n{'='*70}")
        print(f"RESULT: {com_port} IS A VALID SHIMMER DEVICE")
        print(f"{'='*70}\n")
        return True
        
    except Exception as e:
        print(f"\n✗ Connection test failed: {e}")
        print(f"\nError type: {type(e).__name__}")
        
        # Try to cleanup
        try:
            ser.close()
        except:
            pass
        
        print("\nTroubleshooting:")
        print("  1. Ensure Shimmer3R is powered on (LED should blink)")
        print("  2. Verify this is the correct COM port (check Device Manager)")
        print("  3. Close any other application using this port (MATLAB, Consensys)")
        print("  4. Try the other COM port (Shimmer3R creates two: COM4 and COM5)")
        print("  5. Power cycle the Shimmer3R (hold button 5 seconds)")
        print("  6. Unpair and re-pair the device in Windows Bluetooth settings")
        
        return False


def main():
    """Main entry point."""
    print("\n" + "="*70)
    print("PyShimmer Connection Test for Shimmer3R")
    print("="*70)
    print("\nThis test uses pyshimmer's official API to connect to the Shimmer3R.")
    print("\nUsage: python test_pyshimmer_connection.py <COM_PORT>")
    print("Example: python test_pyshimmer_connection.py COM5")
    
    if len(sys.argv) < 2:
        print("\n⚠ No COM port specified!")
        print("\nAvailable COM ports on this system:")
        
        import serial.tools.list_ports
        ports = list(serial.tools.list_ports.comports())
        for i, port in enumerate(ports, 1):
            print(f"  {i}. {port.device} - {port.description}")
        
        print("\nTry running with one of the Bluetooth COM ports:")
        print("  python test_pyshimmer_connection.py COM4")
        print("  python test_pyshimmer_connection.py COM5")
        sys.exit(1)
    
    com_port = sys.argv[1].upper()
    
    # Validate COM port format
    if not com_port.startswith('COM'):
        print(f"\n⚠ Invalid COM port format: '{com_port}'")
        print("Expected format: COM4, COM5, etc.")
        sys.exit(1)
    
    success = test_connection(com_port)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
