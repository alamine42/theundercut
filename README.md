# The Undercut

Steps to build:

0a. (Optional) Get list of circuits and pre-load DIM_CIRCUIT
0b. (Optional) Get list of drivers and pre-load into DIM_DRIVER

1. Get meeting data: the script runs every week on Monday at 3am and looks for a meeting in the past 72 hrs, or something like that. Load into a DIM_CIRCUIT table.

2. Get race session data: Get session data for the selected meeting where session name = "race". No Sprint races for now. Load into a DIM_SESSION table.

2. Get drivers: get the list of drivers for that race, load (1) into a DIM_DRIVER table and (2) into a DIM_SESSION_DRIVER table.

3. Get laps

