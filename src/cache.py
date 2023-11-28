#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
All Rights Reserved
(c) Language Machines Corporation 2023
"""

import logging


logger = logging.getLogger(__name__)
print(logger)

import hashlib
import redis
from dotenv import dotenv_values

class Cache:
    def __init__(self, db=0):
        config = dotenv_values("../.env")
        host = config.get("REDIS_HOST", "localhost")
        port = config.get("REDIS_PORT", 6380)
        secret_key = config.get("REDIS_SECRET_KEY", "")
        self.redis_client = redis.StrictRedis(host=host,
        port=port, db=0, password=secret_key, ssl=True)

    def _generate_redis_key(self, data):
        sha256_hash = hashlib.sha256()
        sha256_hash.update(data.encode('utf-8'))
        return sha256_hash.hexdigest()

    def get(self, key):
        redis_key = self._generate_redis_key(key)
        cached_data = self.redis_client.get(redis_key)
        return cached_data

    def put(self, key, data, expiration=None):
        redis_key = self._generate_redis_key(key)
        self.redis_client.set(redis_key, data, ex=expiration)
