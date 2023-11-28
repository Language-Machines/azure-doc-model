#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
All Rights Reserved
(c) Language Machines Corporation 2023
"""

import logging
import json
from gpt_api import chat
from collections import defaultdict

logger = logging.getLogger(__name__)
print(logger)


class Converter:
    """
    Extract and Normalize field values.

    We cannot assume that the granularity at which a particular document expresses information matches
    the granularity at which the ontology expects it.

    If the document provides a coarser representation, we will need to project out multiple ontology facts from it.
    For instance, one of the test documents has a table with a column "Name and Address of Transferee". The ontology
    expects name and address as two separate facts. So we need a generic way to do this extraction.
    (Here we just use GPT4. But this is expensive. We could use a separate, customized, cheaper entity name extractor 
    and address extractor instead.)

    Logically it is possible that the granularity of information in the document is finer than in the ontology and 
    we have to synthesize a fact from information from multiple places in the document. I have not seen this in 
    practice.

    TODO: Move much of the normalization in scoring to this class.
    """
    def __init__(self, biller, hints=None):
        self.biller = biller
        self.hints = hints

    def chat(self, message, history=None, model=None, use_cached_data=False):
        model = model or (self.hints["LLM"] if "LLM" in self.hints else "gpt-4")
        result = chat(message, history=history, model=model, biller=self.biller, use_cached_data=use_cached_data)
        return result

    def get_entity_name(self, s, use_cached_data = False):
        logger.info(f"get_entity_name extraction.")
        model = self.hints["LLM"] if "LLM" in self.hints else "gpt-4"
        u = self.chat(f"""Extract the entity's name from the following passage. Emit a JSON with field "entity_name".
-- Passage
{s}
-- Answer JSON""", model=model,use_cached_data=use_cached_data)
        data = u['choices'][0]['message']['content']
        r = json.loads(data)
        return r["entity_name"]

    def get_address(self, s, use_cached_data=False):
        logger.info(f"get_address extraction.")
        model = self.hints["LLM"] if "LLM" in self.hints else "gpt-4"
        u = self.chat(f"""Extract the entity's addres from the following passage. Emit a JSON with field "address".
-- Passage
{s}
-- Answer JSON""", model=model, use_cached_data=use_cached_data)
        r = json.loads(u['choices'][0]['message']['content'])
        return r["address"]

    def apply_conversion(self, field, value, use_cached_data=False):
        """
        Return a synthesized fact from given value for field.
        """
        #print()
        #print(field)
        converted_value = value #vj: default to value, then convert if possible.

        try:
            for converter in field["converters"]:
                if converter["type"] == "regex":
                    converted_value = self._apply_regex(converter["regex"], value)

                if converter["type"] == "function":
                    converted_value = getattr(self, converter["function"])(value,use_cached_data)

        except Exception as e:
            pass

        return {
            "field_name": field["field_name"],
            "field_key": field["field_key"],
            "table_name": field["table_name"],
            "section_name": field["section_name"],
            "column": field["column"] if 'column' in field else 0,
            "tab": field["tab"] if 'tab' in field else 0,
            "comment": field["comment"] if "comment" in field else "",
            "user_defined_key": field["user_defined_key"] if "user_defined_key" in field else "",
            "value": value,
            "converted_value": converted_value
        }
