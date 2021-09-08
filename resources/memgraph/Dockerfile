#FROM memgraph/memgraph-mage
FROM memgraph/memgraph:latest

USER root

# Remove this after memgraph-mage starts working again
RUN apt-get update && \
    apt-get --yes install curl git cmake g++ clang python3-dev uuid-dev && \
    cd /usr/local/bin && \
    ln -s /usr/bin/python3 python && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Install the NLP libraries
RUN python3 -m pip install -U pip setuptools wheel && \
    python3 -m pip install -U spacy

# Download the NLP model for English language
RUN python3 -m spacy download en_core_web_sm

# Copy the local query modules
COPY query_modules/ /usr/lib/memgraph/query_modules/

USER memgraph
