#!/bin/bash

echo "Starting all Services..."

# 1. Start the Main Database Gateway and save output to gateway3.log
python3 link_dashboard_vanna/gateway3.py > gateway3.log 2>&1 &
PID1=$!
echo "Main Gateway (Database) started (PID: $PID1)"

# 2. Start the Session Service and save output to sessions.log
python3 link_dashboard_vanna/sessions_service.py > sessions.log 2>&1 &
PID2=$!
echo "Session Service started (PID: $PID2)"

# 3. Start the Basic Gateway and save output to gateway_basic.log
python3 link_dashboard_vanna/gateway_basic.py > gateway_basic.log 2>&1 &
PID3=$!
echo "Basic Gateway started (PID: $PID3)"

# 4. Start the Reco Gateway and save output to gateway_reco.log
python3 link_dashboard_vanna/gateway_reco.py > gateway_reco.log 2>&1 &
PID4=$!
echo "Reco Gateway started (PID: $PID4)"

echo "------------------------------------------------"
echo "All services are currently running in the background!"
echo "Press [CTRL+C] at any time to stop all of them."
echo "------------------------------------------------"

# This ensures that when you press CTRL+C, it safely shuts down the servers
trap "echo 'Shutting down services...'; kill $PID1 $PID2 $PID3 $PID4; exit" INT

# Keep the script running so the trap works
wait