@echo OFF

set shimmerPath=C:/Users/LARNA/Documents/MATLAB/Acute_Tinnitus/Shimmer

set cmdECG="try; StreamShimmer('6', 'ECG', 'lsl', true, 'lsl_data', 'raw', 'duration', inf); catch ME; disp(['ERROR: ', ME.identifier, ' - ', ME.message]); end; exit"
set cmdGSR="try; StreamShimmer('7', 'GSR', 'lsl', true, 'lsl_data', 'raw', 'duration', inf); catch ME; disp(['ERROR: ', ME.identifier, ' - ', ME.message]); end; exit"

set gsr_error_log=error_log_GSR.txt
set ecg_error_log=error_log_ECG.txt

cmd.exe /c "cd /d %shimmerPath% & matlab -nosplash -nodesktop -singleCompThread -minimize -r %cmdGSR% -logfile %gsr_error_log%"
cmd.exe /c "cd /d %shimmerPath% & matlab -nosplash -nodesktop -singleCompThread -minimize -r %cmdECG% -logfile %ecg_error_log%"