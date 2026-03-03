- Automate pushing to github after a data run with subprocess
- Add discretized data visualization to the EDA notebook
- Automate running the EDA notebook and saving it using papermill as pm
- Need to improve the EDA notebook to help assess the quality of gathered data
- Need to remove the messages.parquet writer - no longer needed
- After improving the EDA notebook, manually verify the data extracted for the 5 downloaded replays
- Data visualization skill for claude grounded in Stephen Few and Edward Tufte's work for better visualization graphics.
- Have .json writer save "metadata" information about each parquet file. More useful.



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


hidden markov models
    make observations, make inferences about behind the scenes



