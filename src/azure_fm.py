#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
All Rights Reserved
(c) Language Machines Corporation 2023
"""

import logging
import json
from gpt_api import ask, search, lang_model, chat
from collections import defaultdict
from cache import Cache
import PyPDF2



from utils.utils import above, not_in

logger = logging.getLogger(__name__)
print(logger)

class AzureVJ:
    """
The form recognizer creates a dictionary for each page. Here a list of important keys in this dictionary 
  1. <code>content:str</code> Concatenate string representation of all textual and visual elements in reading order.
  2. <code>paragraphs:List[DocumentParagraph]</code> Each element of this list is a dictionary. 
  This dictionary provides the content and bounding region for each paragraph
  3.<code>tables:List[DocumentTable]</code> Each element of this list is a dictionary. This dictionary has four 
  main keys: <code>'row_count', 'column_count', 'cells', 'bounding_regions'</code>.
     2. <code>'row_count', 'column_count'</code>: number of rows and columns in the table.
     3. <code>'bounding_regions'</code>: bounding region around the table
     4. <code>'cell':List[Cells]</code>: Each element of this list is a dictionary. This dictionary collects the following 
     attributes of the cell: <code>'kind', 'row_index', 'column_index', 'content', 'bounding_regions'</code>

    """

    def __init__(self, pdf_fn, vj=None, endpoint=None, key=None, cache=None):
        endpoint = endpoint or "https://eastus.api.cognitive.microsoft.com"
        key = key or "c43b2498028b4b61b813d797682c19e4 "
        
        from azure.ai.formrecognizer import DocumentAnalysisClient
        from azure.core.credentials import AzureKeyCredential
        self.pdf_fn = pdf_fn
        self.cache = cache or Cache()

        self.client = DocumentAnalysisClient(endpoint=endpoint, credential=AzureKeyCredential(key))

        # A list of pages.
        self.vj = vj
        
    def gen_vjson_pages(self, hints_keys, biller=None):
        from pdf2image import convert_from_path    
        from PyPDF2 import PdfWriter, PdfReader
        
        # This is for vijay's MacOS
        inputpdf = PdfReader(open(self.pdf_fn, "rb"))
        images = convert_from_path(self.pdf_fn, poppler_path="/usr/local/bin")
        
        logging.getLogger("azure").setLevel(logging.CRITICAL)
        vjs = {}
        import io
        for key in hints_keys:
            for pn in key["pages"]:
                output = PdfWriter()
                output.add_page(inputpdf.pages[pn])
                iob = io.BytesIO()
                output.write(iob)
                
                cache_key = self.pdf_fn+"#"+str(pn)   # TODO should be added more information to make this key more unique 
                cache_data = None
                if not key["use_cached_data"] or ((cache_data := self.cache.get(cache_key)) == None):
                    
                    poller = self.client.begin_analyze_document("prebuilt-layout", 
                                                            document=iob.getvalue())
                    vjs[pn] = poller.result().to_dict()
                    
                    if (len(vjs[pn]['tables']) == 0):
                        iob = io.BytesIO()
                        images[pn].save(iob, format="PNG")

                        poller = self.client.begin_analyze_document("prebuilt-layout", 
                                                            document=iob.getvalue())
                        vjs[pn] = poller.result().to_dict()
                    
                    self.cache.put(cache_key, str(vjs[pn]))
                    # parsing here for a single page 
                    biller.update_azure_page_count(1)
                else:
                    vjs[pn] = eval(cache_data)
            self.vj_pages = vjs
        

    def gen_vjson(self, force=False, per_page=True, biller=None, use_cached_data=True):
        """
        Deprecated. Takes too long. No need to use it. Use gen_vjson_pages.
        """
        if force or self.vj is None:
            if per_page: 
                # Generate an image per page.
                from pdf2image import convert_from_path

                # This is for vijay's MacOS
                images = convert_from_path(self.pdf_fn)

                jsons = []
                for i, image in enumerate(images):
                    # Save pages as images in the pdf
                    images[i].save(f'page_{i}.jpg', 'JPEG')

                for i, image in enumerate(images):
                    cache_key = self.pdf_fn+"#"+f"page_{i}.jpg"   # TODO should be added more information to make this key more unique 
                    cache_data = self.cache.get(cache_key)
                    if cache_data == None or not use_cached_data:
                        # Get bytes from the object returned by convert_from_path
                        poller = self.client.begin_analyze_document("prebuilt-layout", 
                                                                document=open(f"page_{i}.jpg", "rb"))
                        jsons.append(poller.result().to_dict())
                        self.cache.put(cache_key, str(poller.result().to_dict()))
                        # parsing here for a single page 
                        biller.update_azure_page_count(1)
                    else:
                         jsons.append(eval(cache_data) )   
                self.vj = jsons
            else: 
                cache_key = self.pdf_fn+"#"   # TODO should be added more information to make this key more unique 
                cache_data = self.cache.get(cache_key)
                
                if cache_data == None or not use_cached_data:
                    with open( self.pdf_fn,'rb') as file:
                        poller = self.client.begin_analyze_document("prebuilt-layout", document=file)
                        
                        self.vj = poller.result().to_dict()
                        self.cache.put(cache_key, str(poller.result().to_dict()))
                        pdf_reader = PyPDF2.PdfFileReader(self.pdf_fn)
                        pages = pdf_reader.getNumPages()
                        biller.update_azure_page_count(len(pages))
                else:
                     self.vj = eval(cache_data)       
            
            
    def pages(self):
        """
        Deprecated. Use self.vj_pages.
        """

        return [page['pages'][0] for page in self.vj] if self.vj is not None else self.vj
    
    def num_pages(self):
        """
        Deprecated. Should not be needed.
        """
        pages_ = self.pages()
        return pages_ and len(pages_)
    
    def tables(self):
        """
        Deprecated.
        """
        return self.vj and self.vj['tables']
    
    def text_for_page(self, i):
        if i in self.vj_pages:
            # Each vj_page was generated by a separate call to Azure with an image for the page.
            # Hence it will have exactly one page, extratt that.
            page = self.vj_pages[i]['pages'][0]
            return '\n'.join(line['content'] for line in page['lines'])
    
    def lines_not_in_tables(self, page_num, content_only=False):
        """
        Return all the lines on the page that are not in tables.
        If content_only, return only the content, else return the line (content + 
        bounding region information).
        
        Note that the version of Azure Form Recognizer we are using seems to number the pages
        in tables with an offset that is one off the pages in text.
        """
        tables = self.tables_for_page(page_num)
        table_brs = [br['polygon'] 
                     for table in tables 
                     for br in table['bounding_regions']]
                    

        page = self.vj_pages[page_num]['pages'][0] # 1 off compensation.
        text_lines = [line 
                      for line in page['lines'] 
                      if not_in(line['polygon'], table_brs)]
        
        return [l['content'] for l in text_lines] if content_only else text_lines
    
    def text_not_in_tables(self, page_num):
        lines = self.lines_not_in_tables(page_num, True)
        return '\n'.join(lines)
    
    
    def tables_for_page(self, i):
        """
        Return the list of tables starting on this page.
        """
        if i in self.vj_pages: 
            return self.vj_pages[i]['tables']
    