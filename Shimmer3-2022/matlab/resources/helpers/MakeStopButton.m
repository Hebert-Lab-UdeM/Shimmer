function [StopButton, fhdl] = MakeStopButton(label)
 if nargin < 1
    figureName = 'Stop Recording';
    buttonLabel = 'Stop';
 else
    figureName = upper(label);
    buttonLabel = ['Stop ' upper(label)];
 end

% Figure position, size is changed few lines below
posDim = [0.4, 0.4, 0.1, 0.1];
fhdl = figure('Name', figureName, 'NumberTitle', 'off', 'Color','red', 'Units', 'normalized', ...
                'Position', posDim);
set(fhdl, 'MenuBar', 'none');
set(fhdl, 'ToolBar', 'none');

% Set figure size (static) in centimeters
fhdl.Units = 'centimeters';
fhdl.Position(3:4) = [5.5, 2.5];
set(fhdl, 'Resize', 'off');

% Set button position and dimension inside the figure, in percent [x, y, w, h]
posDim = [0.1, 0.2, 0.8, 0.6];
StopButton = uicontrol('Style', 'pushbutton', 'Units', 'normalized', 'Position', posDim, ...
                        'String', buttonLabel, 'FontSize', 15, 'FontWeight', 'bold', ...
                        'Callback', 'delete(gcbo)');
end
