#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
All Rights Reserved
(c) Vijay A. Saraswat 2020, 2021, 2022, 2023
"""

import math
import openai
from typing import List
import logging
import time

logging.basicConfig(level=logging.INFO)
logger=logging.getLogger(__name__)

chatgpt = "gpt-3.5-turbo"
chatgpt = "gpt-4"

import random
import time
 
import openai

print("hellooo again from gpt api")
# define a retry decorator
# Code taken from OpenAI pages -- they recommend backoff strategies
def retry_with_exponential_backoff(
    func,
    initial_delay: float = 1,
    exponential_base: float = 2,
    jitter: bool = True,
    max_retries: int = 10,
    errors: tuple = (openai.error.RateLimitError,),
):
    """Retry a function with exponential backoff."""
 
    def wrapper(*args, **kwargs):
        # Initialize variables
        num_retries = 0
        delay = initial_delay
 
        # Loop until a successful response or max_retries is hit or an exception is raised
        while True:
            try:
                return func(*args, **kwargs)
 
            # Retry on specific errors
            except errors as e:
                # Increment retries
                num_retries += 1
 
                # Check if max retries has been reached
                if num_retries > max_retries:
                    raise Exception(
                        f"Maximum number of retries ({max_retries}) exceeded."
                    )
 
                # Increment the delay
                delay *= exponential_base * (1 + jitter * random.random())
 
                # Sleep for the delay
                time.sleep(delay)
 
            # Raise exceptions for any errors not specified
            except Exception as e:
                raise e
 
    return wrapper
    
@retry_with_exponential_backoff
def completions_with_backoff(**kwargs):
    return openai.ChatCompletion.create(**kwargs)

def chat(message='', history=None, model=chatgpt, biller=None, use_cached_data=False):
    if True:
        history = history or [ {"role": "system", "content": "You are a helpful assistant."}]
        logger.info(f"Chatting with {model} (content {len(message)} chars).")
        t0 = time.time()
        result = completions_with_backoff(model=model,
                                        messages = history + [ {"role": "user", "content": message}],
                                        temperature=0
                                        )
        t1 = time.time()
        # print(result['usage']['completion_tokens'])
        # print(result['usage']['prompt_tokens'])
        logger.info(f"Response {result['usage']} ({round(t1-t0,3)} sec).")
    return result

def ask(context=None, data=None, data_prompts=None, add_ans_prompt=False,
        query="", max_tokens=40, logprobs=5, stop=None, engine:str="davinci",
        n:int=1,
        temperature:float=0.,threshold=0.3,
        top_p:float=1):

    if context is None:

        context = ""
    if data is not None:
        if data_prompts is None:
            data_prompts=("Q:", "A:")
        context += '\n'.join([f"\n{data_prompts[0]} {q}{data_prompts[1]} {a}"
                              for q, a in data])
    if data_prompts:
        context += f"\n\n{data_prompts[0]} "
        stop = data_prompts[0] if stop is None else stop + [data_prompts[0]]

    context += f"{query}"

    if add_ans_prompt:
        if data_prompts:
            context += f"{data_prompts[1]} "

    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"length={len(context.split())}, stop={stop}, max_tokens={max_tokens}")
        logger.debug(f"|{context}|")

    x = openai.Completion.create(engine=engine,
                                 prompt=context,
                                 max_tokens=max_tokens,
                                 stop=stop,
                                 logprobs=logprobs,
                                 n=n,
                                 temperature=temperature
                                 ) 
                                 
    results = [(d['text'], round(p, 4))
               for choice in x['choices']
               for d in [choice.to_dict()]
               for probs in [d['logprobs']['token_logprobs']]
               for p in [math.exp(sum(probs)/len(probs))]
               if p > threshold
    ]
    results=sorted(results, key=lambda x:x[1],reverse=True)
               

    return results, x, stop


def search(docs, query,engine="davinci"):
    result=openai.Engine(engine).search(documents=docs,query=query)
    item=max(result['data'], key=lambda x: x['score'])
    return docs[item['document']], item['score'], result

def lang_model(text:List[str], context:str="", engine:str="davinci", logprobs:int=30,
               temperature:float=0.2, verbose:bool=False, approx:bool=True, adjust:float=0.5):
    """
    Return the conditional (log)probability of text, given context. Given the current
    API for OpenAI, we only get logprobs values back (bounded at 100). So if a prob
    value is not returned, the conditional prob is approximated by the lowest prob returned, 
    and computation continues (if approx is True, else None is returned).

    :param text: A list of tokens.
    """

    result = 0.0
    for i, tok in enumerate(text):
        x  = openai.Completion.create(engine=engine,
                                      prompt=context,
                                      max_tokens=1,
                                      logprobs=logprobs,
                                      n=1,
                                      temperature=temperature)
        if not x['choices']:
            " No continuation returned."
            return None
        choice = x['choices'][0]
        tokens =  choice["logprobs"]["top_logprobs"][0]

        if tok not in tokens and not approx:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"i:{i}, |{context}| ==> |{tok}| not found in returned probabilities {tokens}.")
            return None
            
        min_ = min(tokens.values()) - adjust
        result += tokens[tok] if tok in tokens else min_
        if logger.isEnabledFor(logging.DEBUG):
            if tok in tokens:
                logger.debug(f"i:{i}, |{context}| ==> |{tok}| p={tokens[tok]}")
            else:
                logger.debug(f"i:{i}, |{context}| ==> |{tok}| not found, assuming p= min of top {logprobs}  = {min_}")
        context += tok

    return result

                
            

                                      
    

    
             
