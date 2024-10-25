### This is the data supporting the study: "On the Readiness of Scientific Data for a Fair and Transparent Use in Machine learning"
[![DOI](https://zenodo.org/badge/692880864.svg)](https://zenodo.org/doi/10.5281/zenodo.10514145)


In this repository you will find:

1 - **Full Results**: The full results of the extraction process containing 4041 data papers annotated using the scripts in the root of this project

The *results/fullResults.xlsx* file contains the whole results of the extraction process. This excel file contains the raw data in the sheet "Raw Data", and the contains a ser of sheets showing the overall analysis, the stratified analysis by journal, by topics, and the comparison with Neurips D&B track.

2 - **Partial Results**: Inside the folder codeRecipes, partial results by venue (Neurips, DBrief, and SData) are presented. This results are used by the scripts in this repo to perform the calculations and are required to perform the scripts. 

4 - **Topic model**: The topic model used during this study is shared in serialized in the codeRecipes/topicModeling folder along a code recipe to replicate the training of the model.

3 - **Code**: The code used to extract the data and manipulate the data is the folder codeRecipes, a requirements.txt could be found to quickly replicate the environment, Python 3.9 required. 

*dataPaperScrapping.ipynb* notebook contains the code used to filter all the data papers type of both journals, and get the PDF (when possible). If you want to reproduce the experiment you may start by this notebook. 

Once you have all the PDF of the journals, *SDataExtractor.py* and *DBriefExtractor.py* and *neuripsExtractor.py* contains the code to perform the extraction for each journal. Note you will need and OpenAI ApiKey and a GROBID service running to execute the notebooks.

For the journal section's analysis, the *SourceExtractor.py* script run the retrieval phase of the method to get the sources relevant paragraph for each dimensions. Then the *analysisNoteBook.ipyb* can be followed to reach the calculus prestend in the manuscripts.




