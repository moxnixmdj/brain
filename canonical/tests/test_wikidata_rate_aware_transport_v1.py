import io,urllib.error,unittest
from canonical.runtime.bound_capabilities.wikidata_rate_aware_transport_v1 import RateAwareFetch

class Resp:
    def __init__(self,b=b"ok"):self.b=b
    def __enter__(self):return self
    def __exit__(self,*a):return False
    def read(self,n):return self.b

class Clock:
    def __init__(self):self.t=0.0;self.sleeps=[]
    def now(self):return self.t
    def sleep(self,x):self.sleeps.append(x);self.t+=x

class RateAwareTransportTests(unittest.TestCase):
    def test_serial_pacing(self):
        c=Clock(); f=RateAwareFetch(min_interval=1,opener=lambda *a,**k:Resp(),clock=c.now,sleeper=c.sleep)
        self.assertEqual(f("u"),b"ok");self.assertEqual(f("u"),b"ok")
        self.assertGreaterEqual(sum(c.sleeps),1.0)
        self.assertEqual(f.request_count,2)

    def test_429_retries_with_backoff(self):
        c=Clock();calls={"n":0}
        def op(*a,**k):
            calls["n"]+=1
            if calls["n"]==1:
                raise urllib.error.HTTPError("u",429,"too many",{"Retry-After":"2"},io.BytesIO())
            return Resp(b"yes")
        f=RateAwareFetch(min_interval=0.1,max_retries=2,opener=op,clock=c.now,sleeper=c.sleep)
        self.assertEqual(f("u"),b"yes")
        self.assertEqual(f.retry_count,1)
        self.assertGreaterEqual(sum(c.sleeps),2)

    def test_nontransient_error_fails_closed(self):
        c=Clock()
        def op(*a,**k):raise urllib.error.HTTPError("u",404,"no",{},io.BytesIO())
        f=RateAwareFetch(opener=op,clock=c.now,sleeper=c.sleep)
        with self.assertRaises(urllib.error.HTTPError):f("u")
        self.assertEqual(f.retry_count,0)

if __name__=="__main__":unittest.main(verbosity=2)
