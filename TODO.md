- Look into research 32 about the weird unit edge cases and how to handle weird state transitions for units like zerg eggs and the archon cocoon
- Add parameters for choosing which columns to write to parquet files after the information has been extracted from a replay.
- Look into adding a CLI hook for choosing how many gamesteps to pull info from.
    - I.E. current pipeline pulls every 1 gamestep, but may be prudent to pull every 25 or so instead (1.1 seconds)
- Look more into feature selection algorithms to determine what features to pass a model for strategy prediction
- Look into using UV and FastAPI to create the project in a way it can have the back end managed and then have a front-end webpage host that can interact with the code using FastAPI for quicker and clearer iterating on the EDA notebooks.
    - Some sort of GUI or an equivalent of some sort to make the pipeline easier to use and more user-friendly than purely relying on CLI commands and usage and documentation.

- Dynamic Time Warping
- Graphical Network...
    - Nodes = timestep and entity
        - Allows community detection analysis
        - degree node
            - distribution of degrees
        - sub-graphs/motifs
            - isomorphic sub-graph (similar graphs in other places)
            - Clique's = all nodes in a subgraph are connected to all other nodes in the clique community
                - sorta like the idea of a motif
        - Basically allows a different representation of the data 
    - Think in time ranges, something like relative time space rather than absolute
        - somethign that represents a strategy over 3 min interval doesnt have to be minutes 1-4 but can be any 3 minute interval
    - XL-node? = excel
    - Gephi - opensource and free sorta version 
    - algorithms for re-graphing graphs based on different ideas. Fascinating area

- Token Embeddings versus Order
    - When you have a sequence, C A B, and B A C, each token has embedding, if you multiply/add those embeddings, they become sequence invariant essentially
    - Idea is mathematical operations that are 'order independent' 

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

Think about a way to represent the data in an abstraction that makes it - at least appear - uniform. 
    How you represent the data to make the problem more tractable is a contribution in and of itself sometimes ya know. 

- View the problem in an NLP framing. Make the time series more like a series of tokens.
    - Take pieces from other domains as well, like vision transformers. Rather than taking the NLP token sequence approach where each position
    can only consist of a single token, allow multiple tokens to be assigned the same position. Essentially a token becomes an (entity, time step) pair
    keeping the positional encoding but just giving it different rules than NLP uses.
    - Make entities the tokens (like deepminds alphastar basically) but explicitly. Then they can be embedded with information like position coordinates, 
    health, energy, shields, etc.
        - For the naive bayes, can't give the tokens embeddings, but can do alphastar style 3 pair tokens (entity, time step, coordinate) sort of style
    - For Naive Bayes, make it an easy 2 class problem, like classifying emails as Ham or Spam. SC2 can have cheese and not cheese
- The big thing, will be in how you decide to do tokenization. In NLP one can see the progression from naive rule based tokenization,
to intentional feature engineering style tokenization (things like lemmatization and stemming -- ways to make similar things actually appear as similar),
all the way to BPE/BERT and learned tokenization where the data decides how to tokenize.
    - So far, lots of research has in some way done something similar to tokenization. With most research not explicitly framing it in that sense. The contribution
    is explicitly framing it as tokenization and then contributing a meaningful way to tokenize the data.
        - Must decide what 'letting the data decide' how to tokenize looks like. What is the SC2 equivalent of greedy subword tokenization. Modern LLM
        tokenizers are not 'learned' with the model in training, they are frozen, but the tokenizer itself was at some point trained on a huge dataset itself.
        - Creating token embeddings is the next step in the comparison. This is a learned process done during model training. 
            - Modern LLMs don't just stop at creating token embeddings. Those embeddings are then altered through attention to become more meaningful.
            - Must decide and do research into what the SC2 equivalent of learned embeddings and then attention across tokens looks like (graphs)
