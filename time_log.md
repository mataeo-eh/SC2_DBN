# Time Log - [SC2 Project]

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
| 2026-03-05 | 06:30 | 08:00 |  2.0h    |  Turning data extraction tool into its own github repository and using it in main project as a submodule   |
| 2026-03-10 | 05:00 | 06:00 |  1.0h    |  Doing some repo maintenance and improving claude's ability to work with this codebase.   |
| 2026-03-12 | 06:00 | 07:00 |  1.0h    |  Running EDA notebooks and looking through them to verify data. Documented data discrepancies; diagnosing and addressing with claude.   |
| 2026-03-14 | 07:00 | 08:00 |  1.0h    |  Re-running data extraction with new fixes to extraction pipeline. Adding EDA notebook running hooks into pipeline.   |
| 2026-03-20 | 06:00 | 07:00 |  1.0h    |  Checking data. Found some discrepencies. Working with claude to diagnose and fix.   |
| 2026-03-26 | 06:00 | 07:30 |  1.5h    |  Checking data. Cleaning up data visualizations.   |
| 2026-03-30 | 05:00 | 06:30 |  1.5h    |  Working on fixing data extraction pipeline and verifying the extracted data  |
| 2026-04-02 | 06:00 | 08:30 |  2.5h    |  Verifying extracted data. Automating pushing EDA notebooks to Kaggle.  |
| 2026-04-03 | 06:30 | 08:30 |  2.0h    |  Verifying extracted data. Tightening unit tracking logic.  |
| 2026-04-03 | 09:00 | 10:30 |  2.0h    |  Meeting with PI to discuss ML applications. Exploring topics discussed in meeting.  |
| 2026-04-06 | 04:00 | 06:00 |  2.0h    |  Ensuring pipeline is set up to do a large data extraction 1 to begin exploratory ML for PoC.  |
| 2026-04-06 | 16:30 | 17:30 |  1.0h    |  Adding batch streaming for parquet writing to fix catastrophic out of memory issue with data extraction pipeline on long replay files with 10k+ columns/rows.  |
| 2026-04-07 | 07:30 | 09:30 |  2.0h    |  Optimizing and tweaking data extraction tool to be more tenable for a large data extraction run.  |
| 2026-04-07 | 15:30 | 17:30 |  2.0h    |  Optimizing and tweaking data extraction tool to be more tenable for a large data extraction run.  |
| 2026-04-07 | 06:30 | 07:15 |  .75h    |  Checking everything after data extraction finished running. pushing to kaggle. creating strategies json to create labels.|
| 2026-04-09 | 07:00 | 08:00 |  1.0h    |  Working on tokenization schema |
| 2026-04-10 | 15:00 | 17:30 |  2.5h    |  Researching tokenization and token embeddings in other domains. Researching VQ-VAE and other audio signal processing token analogs. |
| 2026-04-10 | 05:30 | 07:00 |  1.5h    |  Working on tokenization schema. |
| 2026-04-13 | 17:30 | 19:30 |  2.0h    |  Ran initial PoC Naive Bayes. Gathering more data to balance the classes. Tightening API replay download logic. |
| 2026-04-14 | 20:30 | 21:30 |  1.0h    |  Fixing data pipeline. Applying tweaks to coarse label logic. |
| 2026-04-16 | 07:00 | 08:30 |  1.5h    |  Working on articulating future directions. Researching existing methods to base future directions around. |
| 2026-04-19 | 07:00 | 09:45 |  2.75h   |  Working on articulating future directions. Researching existing methods for tokenization and embeddings to direct future work. |
| 2026-04-19 | 13:30 | 17:30 |  4.0h    |  Working on articulating future directions. Adding logic to gather recent bot matches irrespective of bot name. |
| 2026-04-20 | 05:00 | 06:30 |  1.5h    |  Researching ML with data of ordered sequences of variable size unordered sets. |
| 2026-04-20 | 16:30 | 18:30 |  2.0h    |  Researching ML with data of ordered sequences of variable size unordered sets. Finalizing proposed direction flowchart. |
| 2026-04-21 | 16:00 | 16:30 |  0.5h    |  Re-thinking T2 and T3 tokenization to be more logically and practically coherent. |
| 2026-04-21 | 18:30 | 19:30 |  1.0h    |  Re-thinking T2 and T3 tokenization to be more logically and practically coherent. |
| 2026-04-21 | 18:00 | 20:00 |  2.0h    |  Re-thinking T2 and T3 tokenization to be more logically and practically coherent. |
| 2026-04-25 | 15:00 | 17:00 |  2.0h    |  Working on new replay strategy labelling and adding upgrades to tokenization. |
| 2026-04-26 | 13:00 | 15:00 |  2.0h    |  Working on new replay strategy labelling and adding upgrades to tokenization. |
| 2026-05-01 | 09:00 | 12:00 |  3.0h    |  Writing tokenization schema as a formal methods section write up. |
| 2026-05-01 | 14:00 | 17:00 |  3.0h    |  Writing tokenization schema as a formal methods section write up. |
| 2026-06-07 | 09:00 | 10:30 |  1.5h    |  Reviewing and re-writing tokenization schema and overall project architecture. |
| 2026-06-07 | 11:30 | 12:30 |  1.0h    |  Filling out Thesis project README with the distilled version of the project architecture |
| 2026-06-25 | 08:00 | 09:00 |  1.0h    |  Working with coding agents to begin implementing diffusionLM based architecture for ML |
| 2026-06-26 | 06:30 | 08:30 |  2.0h    |  Working with coding agents to begin implementing diffusionLM based architecture for ML. Refining the process along the way. |
| 2026-06-27 | 08:00 | 09:00 |  1.0h    |  Checking over implemented architecture and pre-training pipeline. Working on setting up cloud compute training for V1. |
| 2026-06-27 | 10:00 | 12:00 |  2.0h    |  Checking over implemented architecture and pre-training pipeline. Working on setting up cloud compute training for V1. Also working on script to help guide context window needed. |
| 2026-06-27 | 13:30 | 16:00 |  2.5h    |  Researching context window size for diffusion models and industry standards for reclaiming flexible-length generation. |
| 2026-07-01 | 16:00 | 18:00 |  2.0h    |  Down-scaling model and dataset to sizes manageable to train locally. Looking for proof of concept of learning and verification that the pre-training pipeline works. |
| 2026-07-01 | 21:00 | 22:00 |  1.0h    |  Debugging pre-training pipeline on downscaled model. Trying to run pipeline to attempt to overfit the small 25 replay pipeline. |
| 2026-07-02 | 05:00 | 06:00 |  1.0h    |  Interpreting results of small over-fit attempt test. Planning to make changes and re-run. |
| 2026-07-03 | 06:00 | 09:00 |  3.0h    |  Looking through results of 194 epoch over-fit attempt training run. Beginning to try and architect fine-tuning pipeline to test on the over-fitted model. |
| 2026-07-03 | 14:00 | 15:00 |  1.0h    |  Working to implement and test fine-tuning. |
| 2026-07-04 | 08:00 | 10:00 |  2.0h    |  Checking implementation of small model but full small dataset local test. Fixing bugs in pipeline. |
| 2026-07-04 | 14:00 | 16:00 |  2.0h    |  Attempting to debug and fix vRAM spike on resume state runs triggering sudden OOM errors. |
| 2026-07-04 | 19:30 | 21:30 |  2.0h    |  Found bug with pre-training pipeline with Win/Loss prediction added. Fixing pre-training pipeline. Addressing GPU data starvation problem in pre-training pipeline. |
| 2026-07-07 | 16:30 | 18:30 |  2.0h    |  Working on building inference task visualizations. Trying to resolve very small train loss with very poor inference performance when inferencing on samples from the training set. |
| 2026-07-08 | 16:30 | 18:30 |  2.0h    |  Removing input from pre-training pipeline |
| 2026-07-09 | 06:00 | 07:00 |  1.0h    |  Setting up pre-training V2. |
| 2026-08-04 | 09:00 | 11:00 |  2.0h    |  Writing prompts to overhaul model architecture and pipeline. |
| 2026-08-05 | 10:00 | 12:00 |  2.0h    |  Working with coding agents to implement pipeline architecture shift to uniform state diffusion. |
| 2026-08-06 | 16:00 | 19:00 |  3.0h    |  Beginning training, interpreting, and fixing bugs in overfitV2 training test. Attempting to isolate and diagnose code/logic bugs preventing rare class tokens from being memorized. |
| 2026-08-07 | 06:00 | 09:00 |  3.0h    | Continuing over-fit training, fixes more small training code bugs. Interpreting results and trying to reason about continued inability to memorize the rare tokens ([END] and [WIN] and [LOSS]) |
| 2026-08-07 | 10:00 | 15:00 |  5.0h    | Continuing over-fit training. Trying to interpret results and design a new test that will allow the model to truly exhibit over-fitting and pure memorization behaviour. |
| 2026-08-08 | 06:00 | 07:00 |  1.0h    | Reading through partial results of extra positional encodings ablation test. Promising for using frozen KV cache to speed up training. |
| 2026-08-09 | 06:00 | 09:00 |  3.0h    | Interpreting results of BOS/EOS base vocab overfitting results. Starting new test to see if model can overfit with regularization parameters turned off. Testing if model performs better at high t when trained on 25% high t sequences. |
| 2026-08-13 | 07:00 | 08:00 |  1.0h    | Working on deciding what changes to make to try a new full trianing run. Thinking of changing LR, LR schedule, weighting rare classes, changing corruption schedule to be skewed towards high t, and adding a corruption schedule weighting term to make low t corruption lower weighted in loss and high t higher loss weighted. |
| 2026-08-13 | 12:30 | 14:00 |  1.5h    | Working on deciding what changes to make to try a new full trianing run. Chenging LR schedule, up-weighting the end of game class and downweighting the PAD class, changing corruption schedule to be skewed towards high t, and adding some parameters to the model. |
|            |       |       |          |            |