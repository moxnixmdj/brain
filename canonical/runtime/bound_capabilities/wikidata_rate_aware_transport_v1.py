#!/usr/bin/env python3
"""Shared rate-aware transport for Wikidata public API reads V1.

Serializes calls through one process-wide scheduler and retries transient
429/503 responses with bounded backoff. Designed to be injected into existing
Wikidata search/neighborhood primitives as fetch_fn. No model cognition.
"""
from __future__ import annotations
import threading,time,urllib.error,urllib.request
from typing import Any,Callable

SCHEMA="PROJECT_BRAIN_WIKIDATA_RATE_AWARE_TRANSPORT_V1"
UA="ProjectBrain-WikidataRateAware/1.0 (+zero-cost model-independent research)"

class RateAwareFetch:
    def __init__(
        self, *,
        min_interval:float=1.0,
        max_retries:int=3,
        max_retry_after:float=8.0,
        opener:Callable[...,Any]=urllib.request.urlopen,
        clock:Callable[[],float]=time.monotonic,
        sleeper:Callable[[float],None]=time.sleep,
    ):
        self.min_interval=max(0.0,min(float(min_interval),10.0))
        self.max_retries=max(0,min(int(max_retries),6))
        self.max_retry_after=max(0.0,min(float(max_retry_after),30.0))
        self.opener=opener;self.clock=clock;self.sleeper=sleeper
        self._lock=threading.Lock();self._last=None
        self.request_count=0;self.retry_count=0

    def _pace(self):
        now=self.clock()
        if self._last is not None:
            wait=self.min_interval-(now-self._last)
            if wait>0:self.sleeper(wait)
        self._last=self.clock()

    def __call__(self,url:str,*,timeout:int=15)->bytes:
        with self._lock:
            for attempt in range(self.max_retries+1):
                self._pace()
                req=urllib.request.Request(str(url),headers={"User-Agent":UA,"Accept":"application/json"})
                self.request_count+=1
                try:
                    with self.opener(req,timeout=timeout) as resp:
                        return resp.read(5_000_000)
                except urllib.error.HTTPError as exc:
                    if exc.code not in {429,502,503,504} or attempt>=self.max_retries:
                        raise
                    self.retry_count+=1
                    raw=exc.headers.get("Retry-After") if exc.headers else None
                    try:delay=float(raw) if raw is not None else float(2**attempt)
                    except Exception:delay=float(2**attempt)
                    self.sleeper(min(self.max_retry_after,max(self.min_interval,delay)))
            raise RuntimeError("UNREACHABLE")

def make_fetcher(**kwargs)->RateAwareFetch:
    return RateAwareFetch(**kwargs)
