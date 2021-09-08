FROM memgraph/memgraph-mage:latest

USER root

# Install the NLP libraries
RUN python3 -m pip install -U pip setuptools wheel && \
    python3 -m pip install -U spacy

# Download the NLP model for English language
RUN python3 -m spacy download en_core_web_sm

# Copy the local query modules
COPY query_modules/ /usr/lib/memgraph/query_modules/

USER memgraph
