set PATH=c:\python39\;c:\python39\scripts\;%PATH%
set FILE_FILTER=%1
set TESTS_FILTER="%2"
set EXECUTION_TYPE="%3"
set IP_ADDRESS="%4"
set COMMUNICATION_PORT="%5"
set RETRIES=%6
set SERVER_GPU_NAME=%7
set SERVER_OS_NAME=%8
set COLLECT_TRACES=%9
if not defined EXECUTION_TYPE set EXECUTION_TYPE="client"
if not defined RETRIES set RETRIES=1
if not defined COLLECT_TRACES set COLLECT_TRACES="False"

python -m pip install -r ../jobs_launcher/install/requirements.txt

python ..\jobs_launcher\executeTests.py --test_filter %TESTS_FILTER% --file_filter %FILE_FILTER% --tests_root ..\jobs --work_root ..\Work\Results --work_dir StreamingSDK --cmd_variables clientTool "..\StreamingSDK\RemoteGameClient.exe" serverTool "..\StreamingSDK\RemoteGameServer.exe" executionType %EXECUTION_TYPE% ipAddress %IP_ADDRESS% communicationPort %COMMUNICATION_PORT% retries %RETRIES% serverGPUName %SERVER_GPU_NAME% serverOSName %SERVER_OS_NAME% collectTraces %COLLECT_TRACES%