#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
All Rights Reserved
(c) Language Machines Corporation 2023
"""

import logging


logger = logging.getLogger(__name__)
print(logger)

# These need to be changed as prices change.

AZURE_PER_PAGE_CHARGE = 0.02  # in USD

"""
For our models with 8k context lengths (e.g. gpt-4 and gpt-4-0314), the price is:
$0.03/1k prompt tokens
$0.06/1k sampled tokens
"""
GPT4_CHARGES = {
    "prompt" : 0.03  # USD per 1K tokens
    ,"completion": 0.06 # USD per 1K tokens 
}
 

class Biller:
    """
    The Biller tracks charges for additional services we use, here Azure Form Recognizer
    and OpenAI's GPT4. It does this by tracking page counts for the former and prompt
    and completion counts for the latter. These are then multiplied by published charges
    (copied manually into the code above) to compute the dollar price.

    TODO: Obtain current prices programmatically.
    """
    def __init__(self):
        self.billing_record = {
            "azure_page_count": 0
            , "gpt4_token_counts": {
                "prompt_tokens": 0
                , "completion_tokens": 0
            }
        }

    def update_azure_page_count(self, p):
        self.billing_record["azure_page_count"] += p

    def update_gpt4_token_counts(self, r):
        
        assert "completion_tokens" in r
        assert "prompt_tokens" in r

        self.billing_record["gpt4_token_counts"]["completion_tokens"] += r["completion_tokens"]
        self.billing_record["gpt4_token_counts"]["prompt_tokens"] += r["prompt_tokens"]

    def cost(self):
        amt = 0.0
        br = self.billing_record
        amt += br["azure_page_count"]*AZURE_PER_PAGE_CHARGE if "azure_page_count" in br else 0.0
        if  "gpt4_token_counts" in br:
            amt += br["gpt4_token_counts"]["prompt_tokens"]*GPT4_CHARGES["prompt"]/1000 
            amt += br["gpt4_token_counts"]["completion_tokens"]*GPT4_CHARGES["completion"]/1000

        return round(amt, 2)