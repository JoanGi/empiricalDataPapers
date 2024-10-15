
import scipdf ## You need a Gorbid service available
from langchain.text_splitter import  SpacyTextSplitter


## This function parse and prepare the text to be encoded in a dense representation. It chunks papers for paragraphs adding relevant section information such as the section's title.

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