- Automate running the EDA notebook and saving it using papermill as pm
- After improving the EDA notebook, manually verify the data extracted for the 5 downloaded replays -> Need to run data extraction first
- Add parameters for choosing which columns to write to parquet files after the information has been extracted from a replay.
- Ensure .json writer contains helpful information in the json files -> Manual verification check needed here -> Some info missing, wrote claude prompt to address it.
- Look more into feature selection algorithms to determine what features to pass a model for strategy prediction
- Look more into the different strategies for turning huge matrices into tensor's attenable to ML



Look into hidden markov chains 

Plotting the column by time, where the column has states, that IS a markov chain basically 

Maybe think ensemble learning per reduced column and process each column as a model maybe 

Dimension reduction on the fly
    - autoencoder to process the raw data on the fly 
        - one recognizes cheese
        - one recognizes macro
            - run data stream through both and see which one matched it better
                - one matches more closer prolly the predicting label 
    - autoencoders, after being trained, are light and run quite quickly... just saying
        - autoencoders are used in stable diffusion arent they?


hidden markov models
    make observations, make inferences about behind the scenes


