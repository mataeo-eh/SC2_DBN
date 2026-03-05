# Time Log - [SC2 DBN]

| Date       | Start | End   | Duration | Task/Notes |
|------------|-------|-------|----------|------------|
| 2026-01-22 | 15:00 | 17:00 |  2.0h    | Researching replay parsing tools, documentation, and programatically retrieving game data from replays. |
| 2026-01-23 | 10:30 | 13:00 |  2.5h    | Researching mapping move action IDs to real commands. Began extracting replay info. |
| 2026-01-23 | 13:45 | 15:45 |  2h      | Began attempts to programatically extract information from replays.        |
| 2026-01-23 | 16:00 | 17:00 |  1h      | Launched claude code research to help parse unit locations from replay data.        |
| 2026-01-24 |  5:30 |  8:00 |  2.5h    | Troubleshooting Claude's parsing implementation. Testing Parsing. Checking parsed info integrity.    |
| 2026-01-24 | 14:30 | 18:00 |  3.5h    | Beginning EDA of parsed data to confirm what is and is not present. Switching to using game engine to capture Ground Truth Game State    |
| 2026-01-25 | 10:00 | 11:00 |  1h      | Using claude code to help build new data extraction pipeline using pysc2.        |
| 2026-01-26 | 06:30 | 07:45 |  1.25h   | Testing data extraction pipeline. Exploring extracted data structure.        |
| 2026-01-26 | 09:15 | 12:15 |  3h      | Validating data extraction, exploring available data, setting up kaggle dataset. Began using aiarena.net API to download replays.       |
| 2026-01-28 | 07:30 | 09:00 |  1.5h    | Attempting to finish programmatic replay extraction, game state parsing, and data set building pathway.      |
| 2026-01-28 | 10:00 | 13:00 |  3h      | Testing programmatic replay extraction, attemtping to finish game state parsing, and data set building pathway.      |
| 2026-02-02 | 09:00 | 12:30 |  3.5h    |  Working to finalize dataset building pipeline. Testing the dataset building pipeline.          |
| 2026-02-07 | 11:30 | 14:30 |  3h      |  Fixing dataset building pipeline. Adding logging to debug why some replays do not parse.         |
| 2026-02-08 | 09:00 | 10:00 |  1h      |  Adding some engineered features and discretized features to begin simple modelling on   |
| 2026-02-08 | 12:30 | 15:30 |  3h      |  Continue adding some engineered features and discretized features to begin simple modelling on. Adding some EDA to understand data pulled from replays already.   |
| 2026-02-09 | 08:30 | 12:30 |  4h      |  Working to integrate data collection fixes and feature engineering into the quickstart.py pipeline for a full data run   |
| 2026-02-10 | 15:00 | 16:30 |  1.5h    |  Checking status after doing full pipeline run. Using claude code to troubleshoot and fix pipeline problems. Making small tweaks to dataset to make it better for machine learning.   |
| 2026-02-13 | 10:30 | 12:30 |  2h      |  Researching sc2 API documentation to see what exactly is available for raw information from the game from a replay   |
| 2026-02-13 | 13:30 | 16:00 |  2.5h    |  Researching sc2 API documentation to see what exactly is available for raw information from the game from a replay. Editing Claude's research file to reflect. Attempting claude code implementation of new structure.   |
| 2026-02-14 | 07:00 | 08:30 |  1.5h    |  Attempting claude code re-write of data parsing. Iterating on change to fix new bugs.   |
| 2026-02-14 | 16:00 | 17:30 |  1.5h    |  Convincing Claude not to screw up my pipeline but to actually fix the bugs (:   |
| 2026-02-21 | 05:00 | 07:30 |  2.5h    |  Confirming bug fixes. Confirmed replays now load with "perfect info." Using Claude to confirm data integrity. Data extraction is now bugged, but game messages are successfully extracted now (helps for automatic labelling)  |
| 2026-02-24 | 05:30 | 06:00 |  1.5h    |  Working with claude to continue implementing pipeline fixes   |
| 2026-02-26 | 06:30 | 08:00 |  1.5h    |  Working with claude to continue implementing pipeline fixes   |
| 2026-03-03 | 07:30 | 08:00 |  0.5h    |  Working with claude to create data visualization to confirm data extraction pipeline   |
| 2026-03-05 | 06:30 | 08:00 |  1.5h    |  Turning data extraction tool into its own github repository and using it in main project as a submodule   |
|            |       |       |          |            |