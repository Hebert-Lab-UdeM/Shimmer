# Shimmer3R Sensor Constants — Phase 1 Reference

**Generated:** 2026-07-03
**Source:** ShimmerResearch GitHub org (shimmer-web-sdk, Shimmer-C-API, ShimmerAndroidAPI, Shimmer-MATLAB-ID)

---

## 1. Java Sensor Class

The MATLAB driver accesses sensor IDs through the Java constant class:

```matlab
deviceHandler.sensorClass = javaObjectEDT('com.shimmerresearch.driver.Configuration$Shimmer3$SENSOR_ID');
```

### Confirmed Constants

These constants were found in existing MATLAB example code from `Shimmer-MATLAB-ID` v3.0.1:

| Java Constant Name | Sensor | MATLAB Example Source |
|---|---|---|
| `SHIMMER_ANALOG_ACCEL` | Low-noise accelerometer (Shimmer3 original) | `plotandwriteexample.m` |
| `SHIMMER_MPU9X50_GYRO` | Gyroscope (Shimmer3 original) | `plotandwriteexample.m` |
| `SHIMMER_LSM303_MAG` | Magnetometer (Shimmer3 original) | `plotandwriteexample.m` |
| `SHIMMER_LSM6DSV_ACCEL_LN` | LSM6DSV accelerometer (Shimmer3R) | `plotandwriteexample.m` |
| `SHIMMER_LSM6DSV_GYRO` | LSM6DSV gyroscope (Shimmer3R) | `plotandwriteexample.m` |
| `SHIMMER_LIS2MDL_MAG` | LIS2MDL magnetometer (Shimmer3R) | `plotandwriteexample.m` |
| `HOST_PPG_A13` | PPG via internal ADC A13 (Shimmer3 & Shimmer3R) | `ppgtoheartrateexample.m` |

### GSR Sensor Constant (Best Estimate, Unconfirmed)

**Expected name:** `SHIMMER_GSR`

**Evidence:**
- The Android API uses `Shimmer.SENSOR_GSR` (bitmask `0x04`)
- The C# API uses `SENSOR_GSR` in `SensorBitmapShimmer3`
- The MATLAB examples consistently use `SHIMMER_*` prefix for Shimmer-specific sensors
- The web SDK constants.ts uses `GSR_NAME = 'GSR'` as the signal name

**HOW TO VERIFY:** Run this in MATLAB after loading `ShimmerDeviceHandler`:

```matlab
deviceHandler = ShimmerDeviceHandler();
fieldnames(deviceHandler.sensorClass)  % list all sensor ID constants
```

Look for an entry matching `GSR` or similar. Record the exact name here.

### PPG Sensor Constant (Confirmed)

**Name:** `deviceHandler.sensorClass.HOST_PPG_A13`

**Note:** This constant is used for BOTH Shimmer3 and Shimmer3R in the Java driver.
The underlying channel name changes based on hardware version:
- Shimmer3: `'PPG_A13'` (internal ADC pin A13)
- Shimmer3R: `'PPG_A1'` (mapped to internal ADC A1 — per C# API Shimmer3R Integration Notes)

The hardware detection pattern from `ppgtoheartrateexample.m`:

```matlab
hwid = shimmerClone.getHardwareVersionParsed();
if hwid.equals('Shimmer3R')
    ppgChannelName = 'PPG_A1';
else
    ppgChannelName = 'PPG_A13';  % Shimmer3 fallback
end
```

---

## 2. Signal (Channel) Names

These are the string names returned by `deviceHandler.obj.receiveData(comPort)` in the
`signalNameArray` list. They must be matched via `ismember()` to extract the correct data columns.

| Channel Name (Shimmer3R) | Channel Name (Shimmer3) | Unit | Format | Source |
|---|---|---|---|---|
| `'Timestamp'` | `'Timestamp'` | ms | u24 | `plotandwriteexample.m` |
| `'GSR'` | `'GSR'` | kohm | u16 | `shimmer-web-sdk/channelFormats.ts` (channel ID 0x1c) |
| `'PPG_A1'` | `'PPG_A13'` | mV | i16 | `ppgtoheartrateexample.m` + C# API Wiki |

---

## 3. Protocol-Level Channel IDs

From `shimmer-web-sdk/src/devices/shimmer3r/channelFormats.ts`:

| Channel ID (hex) | Name | Format | Bytes | Endianness |
|---|---|---|---|---|
| `0x1c` | GSR | u16 | 2 | LE |
| `0x12` | PPG | i16 | 2 | LE |
| `0x00-0x02` | LN_ACCEL_X/Y/Z | i16 | 2 | LE |
| `0x04-0x06` | WR_ACCEL_X/Y/Z | i16 | 2 | LE |
| `0x0a-0x0c` | GYRO_X/Y/Z | i16 | 2 | LE |
| `0x07-0x09` | MAG_X/Y/Z | i16 | 2 | LE |

---

## 4. Internal Expansion Power

**Protocol opcode:** `0x5e` (SET_INTERNAL_EXP_POWER_ENABLE_COMMAND)

The old driver called `shimmer.setinternalexppower(1)` to enable power to the GSR+ board's
optical sensor. In the new Java driver:

- The Android API code checks `getInternalExpPower()==1` before enabling PPG processing,
  suggesting it is managed separately from sensor enablement.
- The `ppgtoheartrateexample.m` does NOT call any explicit power enable — it only enables
  the `HOST_PPG_A13` sensor ID.

**Recommendation for Phase 1:** Attempt streaming without an explicit power-enable call first.
If the PPG signal returns all zeros or noise, add an explicit call if available on the Java
device object (e.g., `shimmerClone.setInternalExpPower(true)` — exact method name TBD).

---

## 5. Shimmer3R Bluetooth Pairing

Per the C# API Wiki (May 2025):

> Pairing via 1234 key is no longer required for the Shimmer3R. As part of the connection
> process you will be prompted to pair, but you won't require a pairing key.

---

## 6. Open Questions

1. **[CRITICAL]** Exact GSR sensor ID constant name in `Configuration$Shimmer3$SENSOR_ID` —
   verify via `fieldnames(deviceHandler.sensorClass)` in MATLAB on Windows PC with the JARs loaded.
2. **[MINOR]** Whether internal expansion power is auto-enabled when GSR sensor is configured,
   or requires an explicit call. Test by streaming and checking if PPG signal is non-zero.
3. **[MINOR]** Exact GSR channel name string returned by `receiveData` on Shimmer3R. Expected
   `'GSR'` per web SDK; verify on first connection.
