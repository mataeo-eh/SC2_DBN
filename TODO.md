- Look into Pushing the updated EDA notebooks to kaggle as well to update the kaggle dataset notebooks when the EDA notebooks get updated
- Add parameters for choosing which columns to write to parquet files after the information has been extracted from a replay.
- Ensure .json writer contains helpful information in the json files -> Manual verification check needed here -> Some info missing, wrote claude prompt to address it.
- Look more into feature selection algorithms to determine what features to pass a model for strategy prediction
- Look more into the different strategies for turning huge matrices into tensor's/vectors attenable to ML
    - Essentially just research what we want to do for data pre-processing and handling to handle the huge state space and get the data into an ML friendly format
- Look into using UV and FastAPI to create the project in a way it can have the back end managed and then have a front-end webpage host that can interact with the code using FastAPI for quicker and clearer iterating on the EDA notebooks. 




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
        - autoencoders are used in stable diffusion arent they? -> Yes, for image processing stable diffusion


hidden markov models
    make observations, make inferences about behind the scenes


