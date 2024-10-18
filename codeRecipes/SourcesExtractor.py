# %%
import pickle
import textPreparation as pr
import transformers
from langchain.embeddings import HuggingFaceInstructEmbeddings
from langchain.vectorstores.faiss import FAISS
from langchain.chat_models import ChatOpenAI
from langchain.schema import (
    HumanMessage,
    SystemMessage, 
    BaseMessage
)
from langchain import HuggingFacePipeline, LLMChain, PromptTemplate
import os
import csv
import pandas as pd
import json
import requests as rq
from bs4 import BeautifulSoup
from transformers import pipeline

# Declaration of the zero-shot classifier model
classifier = transformers.pipeline("zero-shot-classification", model="valhalla/distilbart-mnli-12-1")

# Utility function to clean texts used during the script
def clean_text(docs):
    # Split, and clean
    texts = ""
    for text in docs:
        texts = texts + text.page_content.replace('\n',' ') + '''
        
        '''
    return texts

embeddings = HuggingFaceInstructEmbeddings(
    model_name="hkunlp/instructor-large",
    query_instruction="Represent the query for retrieval: "
)

# Parse PDF, extract text, and embed the text chunks
def preprocess(data_paper):
    id = data_paper['doi'].rsplit('/', 1)[-1]
    vectorsPath = "./codeRecipes/"+data_paper['journal']+"/vectors/"+id
    print(vectorsPath+"/index.faiss")
    if os.path.isfile(vectorsPath+"/index.faiss"):
        print("Loading embeddings")
        # Load the index
        docsearch = FAISS.load_local(vectorsPath,embeddings=embeddings,allow_dangerous_deserialization=True)
    else:
        print("Creating embeddings")
        pdfPaths = "codeRecipes/"+data_paper['journal']+"/documents/"
        texts, sources = pr.prepare_text(file_path = pdfPaths + data_paper['doi'].rsplit('/', 1)[-1]+".pdf")
        if (texts != 'error'):
            # Create an index search    
            docsearch = FAISS.from_texts(texts, embeddings, metadatas=[{"source": i} for i in sources])
            # Save the index locally
            FAISS.save_local(docsearch, vectorsPath)
            return docsearch, texts
        return 'error','error'
    return docsearch, ""

# Extract the usus dimensions
def uses(docsearch,tags):
    uses = {}
    ## Data uses
    uses['uses_uses_sources'] = docsearch.similarity_search_with_score("Recommended and non-recommended uses of the dataset", k=4)

    ## Data limits non-recommended uses
    uses['uses_data_limits_sources'] = docsearch.similarity_search_with_score("Recommended and non-recommended uses of the dataset", k=4)

    ## ML approach
    uses['uses_ml_approach_sources'] = docsearch.similarity_search_with_score("testing the data with a machine learning approach", k=4)
    uses['uses_represents_people_sources'] = docsearch.similarity_search_with_score("The data collected represents people?", k=4)
    uses['uses_biases_sources'] = docsearch.similarity_search_with_score("Biases issues of the data", k=4)
    uses['uses_privacy_sources'] = docsearch.similarity_search_with_score("Privacy issues of the data", k=4)
    uses['uses_sensitivity_sources'] = docsearch.similarity_search_with_score("sensitivity issues for specific social groups ", k=4)
    # Maintenance policies
    uses['uses_maintenance_policies_sources'] = docsearch.similarity_search_with_score("Maintenance policies of th dataset", k=4)
    return uses

# Extract the collection dimensions
def collection(docsearch, uses):    
    collection = {}
    collection['collection_explanation_sources'] = docsearch.similarity_search_with_score("How the data have been collected", k=4)
    collection['collection_team_sources'] = docsearch.similarity_search_with_score("The team who collects the data of the dataset", k=3)
    collection['collection_labour_sources'] = docsearch.similarity_search_with_score("labour information about the crowdsourcing team", k=4)
    # Demographic of the team
    collection['collection_team_demographic_sources'] = docsearch.similarity_search_with_score("The collection process of the dataset", k=4)
    collection['collection_target_demographics_sources'] = docsearch.similarity_search_with_score(" demographic data on the individuals from whom the data is collected", k=4)
       
    # Does the data represent language?
    collection['collection_speakers_demographics_sources'] = docsearch.similarity_search_with_score("Speech situation information", k=4)
    # Sources
    collection['collection_sources_sources'] = docsearch.similarity_search_with_score("The sources where the data is collected", k=4)
    # Infrastructure
    collection['collection_infrastructure_sources'] = docsearch.similarity_search_with_score("The infrastructure used to collect the data", k=4)
 

    return collection

# Extract the annotation dimensions
def annotation(docsearch): 

    annotation = {}
    ## Annotation Process

    annotation["annotation_explanation_sources"] = docsearch.similarity_search_with_score("The annotation of the data", k=4)
    annotation['annotation_team_demographi_sources'] = docsearch.similarity_search_with_score("The team who annotated the data", k=4)
    annotation['annotation_infrastructure_sources'] = docsearch.similarity_search_with_score("tools or infrastructure to annotate the data", k=4)
    annotation['annotation_validation_methods_sources'] = docsearch.similarity_search_with_score("Validation methods applied to the labels", k=4)

    return annotation



def extractor(dataPaperList): 
    results = []
    for index, data_paper in dataPaperList.iterrows():
        print("Processing the: "+str(index))
        if index > -1 and data_paper["error"] == True:
            tags = ""
            try:
                docsearch, finaltext = preprocess(data_paper)
            except:
                docsearch = 'error'
            if (docsearch != 'error'):
                uses_results = uses(docsearch,tags)
                collection_results = collection(docsearch, uses_results)
                annotation_results = annotation(docsearch)
                results.append({"id":data_paper['id']} | {"doi":data_paper['doi']} | uses_results | collection_results | annotation_results)
            else:
                results.append({"id":data_paper['id']} | {"doi":data_paper['doi']} | {"generated_tags":tags, "error": True})
            print(str(index) + " processed!")
            with open('results.pkl', 'wb') as f:
                pickle.dump(results, f)
    sources = pd.DataFrame().from_dict(results)
    return sources
    #output = pd.DataFrame().from_dict(results).to_excel(output)
    #print("done!")

####################################
# MAIN SCRIPT
####################################
#df = pd.read_excel("results/sources.xlsx", sheet_name="Raw Data")
df = pd.read_excel("results/sources.xlsx")
output = "codeRecipes/sources.xlsx"


sources = extractor(df)
sources.to_excel("sourcesClean.xlsx")
