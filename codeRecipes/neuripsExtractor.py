# %%
import pickle
import scipdf ## You need a Gorbid service available
from langchain.text_splitter import  SpacyTextSplitter
import transformers
from langchain.embeddings import HuggingFaceInstructEmbeddings
from langchain.vectorstores import FAISS
from langchain_openai import ChatOpenAI
from langchain.schema import (
    HumanMessage,
    SystemMessage
)
from langchain import HuggingFacePipeline
import os
import csv
import pandas as pd
import json
import getpass
import requests as rq
from bs4 import BeautifulSoup
import zipfile
import requests


if not os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = getpass.getpass("Enter your OpenAI API key: ")
# Insert your OpenAI APIkey
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
    # api_key="...",  # if you prefer to pass api key in directly instaed of using env vars
    # base_url="...",
    # organization="...",
    # other params...
)

k_search = 10 ## Number of documents retrieved

# Definition of the prompt base template
def LanguageModel(system, message):
    messages = [
        SystemMessage(content=system),
        HumanMessage(content=message)
    ]
    try:
        result = llm.invoke(messages)
        return result
    except:
        return(HumanMessage(content="error"))

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

def get_attachments(id):
    path = "https://openreview.net/attachment?id="+id+"&name=supplementary_material"
    response =  requests.get(path)
    with open("codeRecipes/neurips/attachments/"+id+".zip", "wb") as file:
        file.write(response.content)
    

def return_pdf_attachements(zip_file_path):
  
    extract_to_dir = os.getcwd() +"/temp/attachments/"
    with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
        print("hello1")
        zip_ref.extractall(extract_to_dir)
        extracted_files = zip_ref.namelist()
        for file_name in extracted_files:
            if file_name.lower().endswith('.pdf'):
                print(f"Found PDF file: {file_name}")
                return extract_to_dir + file_name
    return False

def prepare_text(file_path):
    # Document folder
    
    #file_path = os.getcwd()+"/neurips/documents/trial.pdf"
    chunk_size = 1000
    text_splitter = SpacyTextSplitter(chunk_size=1000, chunk_overlap=300)

    # Parse the PDF
    article_dict = scipdf.parse_pdf_to_dict(file_path, soup=True,return_coordinates=False, grobid_url="https://kermitt2-grobid.hf.space") # return dictionary
    #f = open('codeRecipes/convert.txt') 
    #article_dict = json.load(f) 
  
    if (article_dict is not None):
        print("Parsing PDF")
        documents = []
        documents.append({"sectitle":"Title","text":"Title:"+article_dict['title']+" \n\n Authors: " + article_dict['authors']})
        documents.append({"sectitle":"Abstract","text":"Abstract: " + article_dict['abstract']})
        for section in article_dict['sections']:
            sectitle = section['heading'] + ": "
            if(isinstance(section['text'], str)):
                res = len(section['text'].split())
                if(res*1.33 > chunk_size):
                    #Split text
                    splittedSections = text_splitter.split_text(section['text'])
                    prevsplit = ''
                    for split in splittedSections:
                        documents.append({"sectitle":section['heading'],"text":sectitle + prevsplit + split})
                        # We are loading the last sentence and appending them to the next split
                        anotherSplitter = SpacyTextSplitter(chunk_size=50, chunk_overlap=1)
                        sentences = anotherSplitter.split_text(split)
                        prevsplit = sentences[len(sentences)-1] +". "
                else:
                    documents.append({"sectitle":section['heading'],"text":sectitle + section['text']}) 
            else:
                for text in section['text']:
                    sec = sec + text+ " \n\n " 
                res = len(sec.split())
                if(res*1.33 > chunk_size):
                    #Split text
                    splittedSections = text_splitter.split_text(section['text'])
                    prevsplit = ''
                    for split in splittedSections:
                        documents.append({"sectitle":section['heading'],"text": sectitle + prevsplit + split})
                        sentences = text_splitter.split_text(split)
                        prevsplit = sentences[len(sentences)-2] +". "+ sentences[len(sentences)-1] + ". "
                else:
                    documents.append({"sectitle":section['heading'],"text":section['heading'] +": "+sec})
        figures = ''
        for figure in article_dict['figures']:
           
            if (figure['figure_type'] == 'table'):
                figures = figures + "In table " + figure['figure_label'] +' of the document we can see: '+ str(figure['figure_caption'])[0:700] + " \n\n "
                title = "Table "+figure['figure_label']
            else:
                figures = figures + "In figure " + figure['figure_label'] +' of the document we can see: '+ str(figure['figure_caption'])[0:700] + " \n\n "
                title = "Figure "+figure['figure_label']
            res = len(figures.split())
            if(res*2 > chunk_size):
                documents.append({"sectitle":title,"text":figures})
                figures = ''
        #finaltext.append(figures)
        print("PDF parsed")
        texts = []
        sources = []
        for document in documents:
            texts.append(document['text'])
            sources.append(document['sectitle'])
        return texts, sources
    print("PDF not parsed")
    return 'error'


def preprocess(data_paper):         
    id = data_paper['doi']
    if os.path.isfile("codeRecipes/neurips/vectors/"+id+"/index.faiss"):
        print("Loading embeddings")
        # Load the index
        docsearch = FAISS.load_local("codeRecipes/neurips/vectors/"+id,embeddings=embeddings,allow_dangerous_deserialization=True)
        return docsearch, ""
    else:
        print("Parsing and extratcion error")
        return 'error','error'


def maintenance(docsearch):
    # Maintenance policies
    authoring = {
    'maintenance_policies':""
    }
    docs = clean_text(docsearch.similarity_search("Maintenance policies of th dataset", k=k_search))
    system = '''Answer the question based solely in the provided context. Please, answer with "yes" or "no" followed by the explanation. 
    ##
    Example: Yes, the maintenance policies are described in the context
    Example: No, there is no mention about maintenance policies in the context
    '''
    query = """Is there any maintenance policies of the dataset?"""
    message = 'Question:'+query+' \n ### \n Context: '+ docs+' ### Answer :'
    authoring['maintenance_policies'] = LanguageModel(system=system,message=message).content
    return authoring
def uses(docsearch):
    # USES
    uses = {
        "uses_uses":str,
        "uses_ml_approach": str,
        "uses_ml_approach_bool":str,
        "uses_data_limits":str,
        "uses_represents_people":str,
        "uses_collected_from_people":str,
        "uses_biases":str, 
        "uses_biases_bool":str, 
        "uses_sensitivity":str, 
        "uses_sensitivity_bool":str,
        "uses_privacy":str, 
        "uses_privacy_bool":str,

    }

    ## Uses
    uses['uses_uses_sources'] = docsearch.similarity_search("Recommended and non-recommended uses of the dataset", k=k_search)
    docs = clean_text(uses['uses_uses_sources'])
    system = """Answer the question based solely in the provided context. Please, summarize each recommended use of the dataset in one sentence
    ##
    Example: The dataset is inteded to detect tumor lesions in skin. The dataset aims provide a complete corpus for scene recognition
    Example: The dataset aim to fill the gap of language data in dutch. The dataset is intended for sentiment classification.
    ##
    """
    query = """Which are the recommended uses of the dataset?"""
    message = 'Question:'+query+' \n ### \n Context: '+ docs+' ### Answer :'
    uses['uses_uses'] = LanguageModel(system=system,message=message).content
  

    ## Data limits non-recommended uses
    uses['uses_data_limits_sources'] = docsearch.similarity_search("Recommended and non-recommended uses of the dataset", k=k_search)
    docs = clean_text(docsearch.similarity_search("Recommended and non-recommended uses of the dataset", k=k_search))
    system = """Answer the question based solely in the provided context. Please, answer with "yes" or "no" followed by the explanation. 
    ##
    Example: Yes, the data is not recommended to be used for for genre research
    Example: No, there is no mention about non-recommended uses or generalization limits of the data.
    Example: Yes, the context mentions that the cohort of patients are limitied to one hospital
    ##
    """
    query = """Is there any mention in the context about non-recommended uses, or generalization limits of the data?"""
    message = 'Question:'+query+' \n ### \n Context: '+ docs+' ### Answer :'
    uses['uses_data_limits'] = LanguageModel(system=system,message=message).content
    print(uses['uses_data_limits'])

    ## ML approach
    uses['uses_ml_approach_sources'] = docsearch.similarity_search("testing the data with a machine learning approach", k=k_search)
    docs = clean_text(uses['uses_ml_approach_sources'])
    system = """Answer the question based solely in the provided context. Please, answer with "yes" or "no" followed by the explanation. 
    ##
    Example: Yes, the data have been tested using the following machine learning model: DICE. Metrics are provided in table 2.
    Example: No, there is no mention about any test using a machine learning approach
    ##
    """
    query = """Has the dataset been tested in any machine learning approach?"""
    message = 'Question:'+query+' \n ### \n Context: '+ docs+' ### Answer :'
    uses['uses_ml_approach'] = LanguageModel(system=system,message=message).content
    classifications = classifier(uses['uses_ml_approach'], ["Yes","No"])
    uses['uses_ml_approach_bool'] = classifications['labels'][0]
    print(uses['uses_ml_approach'])


    # The uses of the data
    system = "The context are the relevant passages of a scientific paper explaining a dataset. Use the following context to answer the provided question. "
    query = """Provide a complete explanation of the collected data"""
    docs = clean_text(docsearch.similarity_search("The data of the dataset", k=k_search))
    message = 'Question:'+query+' \n ### \n Context: '+ docs+' ### Answer :'
    uses['uses_data'] = LanguageModel(system=system,message=message).content

    
    docs = clean_text(docsearch.similarity_search("The data collected represents people?", k=k_search))
    system = "The context is a scientific paper describing a dataset, answer the question based on the context. Please, answer with 'yes' or 'no' followed by the explanation. "
    query = """The subjects of the collection process are humans?"""
    message = 'Question:'+query+' \n ### \n Context: '+ uses['uses_data']+' \n\n '+ docs+' ### Answer :'
    uses['uses_collected_from_people'] = LanguageModel(system=system,message=message).content
    print(uses['uses_collected_from_people'])
    classifications_col = classifier(uses['uses_collected_from_people'], ["Yes","No"])
    classifications_rep = ''
    if (classifications_col['labels'][0] == 'Yes'):
        uses['uses_represents_people'] = "Yes, data represents people as is collected from people"
    if(classifications_col['labels'][0] == 'No'):
        ## Does the data represents people? ## if yes, check biases
        docs = clean_text(docsearch.similarity_search("The data collected represents people?", k=k_search))
        system = "The context is a scientific paper describing a dataset, answer the question based on the context. Please, answer with 'yes' or 'no' followed by the explanation. "
        query = """The data of the dataset represents people?"""
        message = 'Question:'+query+' \n ### \n Context: '+ docs+' ### Answer :'
        uses['uses_represents_people'] = LanguageModel(system=system,message=message).content
        print(uses['uses_represents_people'])
        classifications_rep = classifier(uses['uses_represents_people'], ["Yes","No"])
    if(classifications_col['labels'][0] == 'Yes' or classifications_rep['labels'][0] == 'Yes'):
        # Biases
        query = """The context provides information about biases issues of the data? """
        uses['uses_biases_sources'] = docsearch.similarity_search("Biases issues of the data", k=k_search)
        docs = clean_text(uses['uses_biases_sources'])
        message = 'Question:'+query+' \n ### \n Context: '+ docs+' ### Answer :'
        uses['uses_biases'] = LanguageModel(system=system,message=message).content
        classifications = classifier(uses['uses_biases'], ["Yes","No"])
        uses['uses_biases_bool'] = classifications['labels'][0]
        # privacy
        query = """The context provides information about privacy issues of the data? """
        uses['uses_privacy_sources'] = docsearch.similarity_search("Privacy issues of the data", k=k_search)
        docs = clean_text(uses['uses_privacy_sources'])
        message = 'Question:'+query+' \n ### \n Context: '+ docs+' ### Answer :'
        uses['uses_privacy'] = LanguageModel(system=system,message=message).content
        classifications = classifier(uses['uses_privacy'], ["Yes","No"])
        uses['uses_privacy_bool'] = classifications['labels'][0]
        # sensitivity
        query = """The context provides information sensitive issues of the data? Can data be ofensive for some people? """
        uses['uses_sensitivity_sources'] = docsearch.similarity_search("sensitivity issues for specific social groups ", k=k_search)
        docs = clean_text(uses['uses_sensitivity_sources'])
        message = 'Question:'+query+' \n ### \n Context: '+ docs+' ### Answer :'
        uses['uses_sensitivity'] = LanguageModel(system=system,message=message).content
        classifications = classifier(uses['uses_sensitivity'], ["Yes","No"])
        uses['uses_sensitivity_bool'] = classifications['labels'][0]

    return uses

def collection(docsearch, uses):    
    # Collection process
    collection = {
        "collection_explanation":"",
        "collection_type":"",
        "collection_team_type":"",
        "collection_labour":"",
        "collection_team_demographic": "",
        "collection_target_demographics": "",
        "collection_language":"",
        "collection_speakers_demographics":"",
        "collection_sources":"",
        "collection_infrastructure":"",
    }


    # Collection process
    #system = "The context are the relevant passages of a scientific paper explaining a dataset. Use the following context to answer the provided question. "
    #query = """Provide a complete explanation of the collection process of the dataset. """
    #collection['collection_explanation_sources'] = docsearch.similarity_search("How the data have been collected", k=k_search)
    #docs = clean_text(collection['collection_explanation_sources'])
    #message = 'Question:'+query+' \n ### \n Context: '+ docs+' ### Answer :'
    #collection['collection_explanation'] = LanguageModel(system=system,message=message).content


    # Collection process Type
    #system = "Use the following context to answer the provided question. Answer only with one of the provided types."
    #query = """Which of the following types best matches the collection process mentioned in the context?
    #    Types: Web API, Web Scrapping, Sensors, Manual Human Curator, Software collection, Surveys, Observations, Interviews, Focus groups, Document analysis, Secondary data analysis, Physical data collection, Self-reporting, Experiments, Direct measurement, Interviews, Document analysis, Secondary data analysis, Physical data collection, Self-reporting, Experiments, Direct measurement, Customer feedback data, Audio or video recordings, Image data, Biometric data, Medical or health data, Financial data, Geographic or spatial data, Time series data, User-generated content data.
#
#        Example: Web API
#        Example: Manual Human Curator
 #   """
 #   message = 'Question:'+query+' \n ### \n Context: '+ collection['collection_explanation']+' ### Answer :'
 #   collection['collection_type'] = LanguageModel(system=system,message=message).content
 #   print(collection['collection_type'])

    # Collection Team Type
 #   system = "Use the following pieces to answer the provided question with one of the provided team types. "
 #   query = """The data was collected by an internal team, an external team, or crowdsourcing team?
 #   """
 #   docs = clean_text(docsearch.similarity_search("The team who collects the data of the dataset", k=k_search))
 #   message = 'Question:'+query+' \n ### \n Context: '+collection['collection_explanation']+' \n\n '+ docs+' ### Answer :'
 #   collection['collection_team_type'] = LanguageModel(system=system,message=message).content
 #   print(collection['collection_team_type'])
    # We check if the team is crowdsourcing
 #   classifications = classifier(collection['collection_team_type'], ["Is an internal team","Is an external team","Is a crowdsourcing team"])
 #   if(classifications['labels'][0] == 'Is a crowdsourcing team'):
 #       system = system = 'Answer the question based solely in the provided context. Please, answer with "yes" or "no" followed by the explanation. '
 #       query = """Is there any labour information about the crowdsourcing team that collects the data?"""
 #       docs = clean_text(docsearch.similarity_search("labour information about the crowdsourcing team", k=k_search))
 #       message = 'Question:'+query+' \n ### \n Context: '+ docs+' ### Answer :'
 #       collection['collection_labour'] = LanguageModel(system=system,message=message).content
 #       print(collection['collection_labour'])
    # Demographic of the team
   # collection['collection_team_demographic_sources'] = docsearch.similarity_search("The collection process of the dataset", k=k_search)
   # docs = clean_text(collection['collection_team_demographic_sources'])
   # system = """Answer the question based solely in the provided context. Please, answer with "yes" or "no" followed by the explanation. 
   # ##
   # Example: Yes, the demographic information is genre and age of the team who collects the data
   # Example: No, there is no mention of demographic information of the team who collects the data
    ## """
   # query = 'The context provides demographic information about the team who collect the data? '
   # message = 'Question:'+query+' \n ### \n Context: '+ docs+' ### Answer :'
   # collection['collection_team_demographic'] = LanguageModel(system=system,message=message).content
   # print(collection['collection_team_demographic'])
   # # Demographics information about the target people if represents people
    classifications = classifier(uses['uses_represents_people'], ["Yes","No"])
    if(classifications['labels'][0] == 'Yes'):
        system = "Use the following pieces to answer the provided question. Please, answer with 'yes' or 'no'. "
        query = """Is there in the context demographic data on the individuals from whom the data is collected?"""
        collection['collection_target_demographics_sources'] = docsearch.similarity_search(" demographic data on the individuals from whom the data is collected", k=4)
        docs = clean_text(collection['collection_target_demographics_sources'])
        message = 'Question:'+query+' \n ### \n Context: '+ docs+' ### Answer :'
        collection['collection_target_demographics'] = LanguageModel(system=system,message=message).content
        print(collection['collection_target_demographics'])
    # Does the data represent language?
    system = "Use the following pieces to answer the provided question. Please, answer with 'yes' or 'no'.  "
    query = """The collected data could represents natural language spoken or written?"""
    docs = clean_text(docsearch.similarity_search("From who the data has been collected?", k=k_search))
    message = 'Question:'+query+' \n ### \n Context: '+ docs+' ### Answer :'
    collection['collection_language'] = LanguageModel(system=system,message=message).content
    classifications = classifier(collection['collection_language'], ["Yes","No"])
    print(collection['collection_language'])
    if(classifications['labels'][0] == 'Yes'):
        # Situation Speech
        system = "Use the following pieces to answer the provided question with one of the provided . Please, answer with 'yes' or 'no' followed by the explanation.  "
        query = """The context provides information about the speech situation, such as as the genre, the modality or the topics?"""
        collection['collection_speakers_demographics_sources'] = docsearch.similarity_search("Speech situation information", k=k_search)
        docs = clean_text(collection['collection_speakers_demographics_sources'])
        message = 'Question:'+query+' \n ### \n Context: '+ docs+' ### Answer :'
        collection['collection_speakers_demographics'] = LanguageModel(system=system,message=message).content
        print(collection['collection_speakers_demographics'])

        # Sources
        collection['collection_sources_sources'] = docsearch.similarity_search("The collection process of the dataset", k=k_search)
        docs = clean_text(collection['collection_sources_sources'])
        system = 'Use the following pieces of context to answer the question.'
        query = 'From which sources or subjects the data has been collected? Answer only with the names of the sources or subjects'
        message = 'Question:'+query+' \n ### \n Context: '+ docs+' ### Answer :'
        collection['collection_sources'] = LanguageModel(system=system,message=message).content
        print(collection['collection_sources'])


        # Infrastructure
        collection['collection_infrastructure_sources'] = docsearch.similarity_search("The collection process of the dataset", k=k_search)
        docs = clean_text(collection['collection_infrastructure_sources'])
        system = 'Use the following pieces of context to answer the question.'
        query = 'Which tools, devices or infrastructure has been used during the collection process?'
        message = 'Question:'+query+' \n ### \n Context: '+ docs+' ### Answer :'
        collection['collection_infrastructure'] = LanguageModel(system=system,message=message).content
        print(collection['collection_infrastructure'])

        return collection

def annotation(docsearch): 

    annotation = {
    "annotation_done":"",
    "annotation_explanation":"",
    "annotation_type":"",
    "annotation_manual":"",
    "annotation_team_type":"",
    "annotation_team_demographic": "",
    "annotation_infrastructure":"",
    "annotation_validation_methods_bool":"",
    "annotation_validation_methods":""
    }
    ## Annotation Process

   
    ## Generate an explanations of the process
    annotation["annotation_explanation_sources"] = docsearch.similarity_search("The annotation of the data", k=k_search)
    docs = clean_text(annotation["annotation_explanation_sources"])
    system = 'Use the following pieces of context to answer the question.'
    query="Can you provide an explanation of the annotation process done over the data?"
    message = 'Question:'+query+' \n ### \n Context: '+ docs+' ### Answer :'
    annotation["annotation_explanation"] = LanguageModel(system=system,message=message).content

    # # Is there an annotation process?
    
    system = 'Use the following pieces of context to answer the question. Please, answer only with "yes" or "no". '
    query="The data of the dataset have been annotated?"
    message = 'Question:'+query+' \n ### \n Context: '+annotation["annotation_explanation"]+' ### Answer :'
    annotation['annotation_done'] = LanguageModel(system=system,message=message).content
    print(annotation['annotation_done'])
    classifications = classifier(annotation['annotation_done'], ["Yes","No"])
    if(classifications['labels'][0] == 'Yes'):
    
        ## Type of the annotation
        #system = 'Use the following pieces of context to answer the question. Please, answer only with the provided categories'
        #query = '''Which  of the following category corresponds to the annotation process mentioned in the context? 
        #        Categories: Bounding boxes, Lines and splines, Semantinc Segmentation, 3D cuboids, Polygonal segmentation, image Landmark and key-point, text Entity Annotation, Text Categorization, Audio Transcription, Speakers Identification, Anomaly Detection, Music Genre Classification, audio Pitch Annotation, Pose Estimation, video Object Tracking, Action Cecognition, Event Annotation, Temporal Annotation, Emotion Recognition, State Labeling, Temporal Pattern Recognition
        #        If you are not sure, answer with 'others'. Please answer only with the categories provided in the context. '''
        #message = 'Question:'+query+' \n ### \n Context: '+ annotation["annotation_explanation"] +' \n\n'+ docs+' ### Answer :'
        #annotation['annotation_type'] = LanguageModel(system=system,message=message).content


        ## Type of the team
        #docs = clean_text(docsearch.similarity_search("The team who has annotated the data", k=k_search))
        #query = 'The data was annotated by an internal team (e.g the authors), an external team, or crowdsourcing team?'
        #message = 'Question:'+query+' \n ### \n Context: '+ annotation["annotation_explanation"] +' \n\n'+ docs+' ### Answer :'
        #annotation['annotation_team_type'] = LanguageModel(system=system,message=message).content
        #print(annotation['annotation_team_type'])

        # Demographic information of the team
        annotation['annotation_team_demographic_sources'] = docsearch.similarity_search("The team who has annotated the data", k=k_search)
        system = "Use the following context to answer the provided question.  Please, answer with 'yes' or 'no' followed by the explanation.  "
        query = """The context provides demographic information about team who annotate the data?"""
        message = 'Question:'+query+' \n ### \n Context: '+ docs+' ### Answer :'
        annotation['annotation_team_demographic'] = LanguageModel(system=system,message=message).content
        print(annotation['annotation_team_demographic'])

        # Infrastructure
        system = "Use the following context  to answer the provided question. Please, answer with 'yes' or 'no' followed by the name of the tools or infrastructures. "
        query = """The context provides information about the tools or infrastructure has been used during the annotation process?'"""
        annotation['annotation_infrastructure_sources'] = docsearch.similarity_search("tools or infrastructure to annotate the data", k=k_search)
        docs = clean_text(annotation['annotation_infrastructure_sources'])
        message = 'Question:'+query+' \n ### \n Context: '+ annotation["annotation_explanation"] +' \n\n '+docs+' ### Answer :'
        annotation['annotation_infrastructure'] = LanguageModel(system=system,message=message).content
        print(annotation['annotation_infrastructure'])

        # Validation methods
        system = "Use the following pieces to answer the provided question. Please answer with 'yes' or 'no', followed by an explanation. "
        query = """The context provides information about the validation methoda done to validate the labels? Can you summarize it?"""
        annotation['annotation_validation_methods_sources'] = docsearch.similarity_search("Validation of the labels/annotations", k=k_search)
        docs = clean_text(annotation['annotation_validation_methods_sources'])
        message = 'Question:'+query+' \n ### \n Context: '+ annotation["annotation_explanation"] +' \n\n '+ docs+' ### Answer :'
        annotation['annotation_validation_methods'] = LanguageModel(system=system,message=message).content
        classifications = classifier(annotation['annotation_validation_methods'], ["Yes","No"])
        print(annotation['annotation_validation_methods'])
        if('Yes' or classifications['labels'][0] == 'Yes'):
            # Validation methods
            system = "Use the following pieces to answer the provided question. Please, answer only with the provided types "
            query = """Which kind of validation methods have been used to validate the labels? 
            Types: Ground Truth Labels, Inter-annotator agreement, Expert Annotations, Test re-test realiability, Proxy-labels, others """
            docs = clean_text(docsearch.similarity_search("Validation of the labels", k=4))
            message = 'Question:'+query+' \n ### \n Context: '+ docs+'\n\n'+annotation['annotation_validation_methods']+'\n\n ### Answer :'
            annotation['annotation_validation_methods_type'] = LanguageModel(system=system,message=message).content

    return annotation

# Reading previous results
#df = pd.read_csv('DBrief/ListDataPapersDBrief.csv')

    
#print("Processing the:"+ data_paper['display_name'])
print("Processing trial for neurips")
print(os.getcwd())
dataPapersList = pd.read_excel('neurips/dataset_filtered_clean.xlsx')
output_path = "neurips/neuripsResults.xlsx"
# If process is interrupted, look at the results and change this number
results = []
#file = open('resultsNeurips4.pkl', 'rb')
#results = pickle.load(file)
for index, data_paper in dataPapersList.iterrows():
    if index > -1:
        #try:
        docsearch, finaltext = preprocess(data_paper)
        #with open("codeRecipes/neurips/texts.txt", "w") as file: 
            #file.writelines(finaltext)
        #except:
            #docsearch = 'error'
        if (docsearch != 'error'):
            print("Collecting answers")
            maintenance_results = maintenance(docsearch)
            uses_results = uses(docsearch)
            collection_results = collection(docsearch, uses_results)
            annotation_results = annotation(docsearch)
            results.append({"doi":data_paper['doi']} | maintenance_results | uses_results | collection_results | annotation_results)
        else:
            print("Embedding creation error")
            results.append({"doi":data_paper['doi']} | {"error": True})
        with open('resultsNeurips.pkl', 'wb') as f:
            pickle.dump(results, f)
        print(str(index) + " processed!")
    #exit()
    output = pd.DataFrame().from_dict(results).to_excel(output_path)

print("done!")