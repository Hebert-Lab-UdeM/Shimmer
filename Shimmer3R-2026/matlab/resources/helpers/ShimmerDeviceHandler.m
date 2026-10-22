classdef ShimmerDeviceHandler < handle
    events
        DeviceConnected
        DeviceDisconnected
        DeviceConnectionLost
    end
    properties
        obj
        bluetoothManager
        sensorClass
        orientationObj
        cleanupHandle
    end
    
    methods
        function this = ShimmerDeviceHandler()
            % List of JARs you want to add (all live in resources/libs/)
            jarsToAdd = {
                'ShimmerBiophysicalProcessingLibrary_Rev_0_10.jar'
                'ShimmerJavaClass.jar'
                'jssc-2.9.6.jar'
                'vecmath-1.3.1.jar'
                'commons-lang3-3.8.1.jar'
                'commons-math-2.2.jar'
                'commons-math3-3.6.jar'
                'guava-19.0.jar'
            };
            
            % This classdef lives in resources/helpers/, while the JARs are
            % one level up in resources/libs/. Resolve libsDir explicitly
            % rather than relative to this file's own directory.
            classDefDir = fileparts(mfilename('fullpath'));
            libsDir = fullfile(fileparts(classDefDir), 'libs');
            
            % Get current dynamic classpath
            currentClasspath = javaclasspath('-dynamic');
            
            for i = 1:numel(jarsToAdd)
                jarPath = jarsToAdd{i};
                fullJarPath = fullfile(libsDir, jarPath);  % Resolve relative to resources/libs/
            
                % Check if the jar is already in classpath (case-insensitive)
                isInClasspath = any(strcmpi(currentClasspath, fullJarPath));
            
                if ~isInClasspath
                    try
                        javaaddpath(fullJarPath);
                        fprintf('Added to classpath: %s\n', fullJarPath);
                    catch ME
                        fprintf('Failed to add %s: %s\n', fullJarPath, ME.message);
                    end
                else
                    fprintf('Already in classpath: %s\n', fullJarPath);
                end
            end

            % this.sampleRate = this.shimmer.getSamplingRateShimmer();
            % relies on previous input / takes time to calibrated
            this.orientationObj = javaObjectEDT('com.shimmerresearch.algorithms.orientation.GradDes3DOrientation', 1/51.2);

            this.sensorClass = javaObjectEDT('com.shimmerresearch.driver.Configuration$Shimmer3$SENSOR_ID');
            this.obj = com.shimmerresearch.tools.matlab.ShimmerJavaClass();
            this.obj.setDebugMode(false);
            this.bluetoothManager = this.obj.mBluetoothManager;
            javaHandle = handle(this.obj, 'callbackproperties');
            javaHandle.PropertyChangeCallback = @(src,evt)this.handleJavaEvent(evt);


        end
        
        function quaternions = orientationModule(this, receivedData, dofMode)
            if iscell(receivedData)
                receivedData = receivedData{1};
            end

            receivedData = single(receivedData);
            
            if strcmp(dofMode, '6dof')
                [N, M] = size(receivedData);
            
                acc = receivedData(:, 2:4); % Accelerometer (ax, ay, az)
                gyr = receivedData(:, 5:7); % Gyroscope (gx, gy, gz)

                quaternions = zeros(N, 4, 'single');

                for i = 1:N
                    this.orientationObj.update(acc(i, 1), acc(i, 2), acc(i, 3), ...
                                                             gyr(i, 1) * (pi/180.0), gyr(i, 2) * (pi/180.0), gyr(i, 3) * (pi/180.0));
                    qw = this.orientationObj.getQuaternionW();
                    qx = this.orientationObj.getQuaternionX();
                    qy = this.orientationObj.getQuaternionY();
                    qz = this.orientationObj.getQuaternionZ();

                    quaternions(i, :) = [qw, qx, qy, qz];
                end
            end
            if strcmp(dofMode, '9dof')
                [N, M] = size(receivedData);
            
                acc = receivedData(:, 2:4); % Accelerometer (ax, ay, az)
                gyr = receivedData(:, 5:7); % Gyroscope (gx, gy, gz)
                mag = receivedData(:, 8:10); % Magnetometer (mx, my, mz)
                
                quaternions = zeros(N, 4);
                
                for i = 1:N
             
                    this.orientationObj.update(acc(i, 1), acc(i, 2), acc(i, 3), ...
                                               gyr(i, 1) * (pi/180.0), gyr(i, 2) * (pi/180.0), gyr(i, 3) * (pi/180.0), ...
                                               mag(i, 1), mag(i, 2), mag(i, 3));

                    qw = this.orientationObj.getQ0();
                    qx = this.orientationObj.getQ1();
                    qy = this.orientationObj.getQ2();
                    qz = this.orientationObj.getQ3();

                    quaternions(i, :) = [qw, qx, qy, qz];
                end
            end
        end

        function handleJavaEvent(this, evt)
            try
                eventObj = evt.getNewValue();   % this is MatlabConnectionEvent
                state   = char(eventObj.state);
                comPort = char(eventObj.comPort);
            catch ME
                disp("Error extracting event data:");
                disp(ME.message);
                return;
            end
        
            switch state
                case 'CONNECTED'
                    fprintf("MATLAB: Device connected on %s\n", comPort);
                    notify(this, 'DeviceConnected', ComPortEventData(comPort));
            
                case 'DISCONNECTED'
                    fprintf("MATLAB: Device disconnected on %s\n", comPort);
                    notify(this, 'DeviceDisconnected', ComPortEventData(comPort));
            
                case 'CONNECTION_LOST'
                    fprintf("MATLAB: Connection lost on %s\n", comPort);
                    notify(this, 'DeviceConnectionLost', ComPortEventData(comPort));
            end
        end
    end
end
