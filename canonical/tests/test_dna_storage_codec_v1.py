from __future__ import annotations
import ast
import pathlib
import random
import tempfile
import unittest

from canonical.runtime import dna_storage_codec_v1 as c


class DNAStorageCodecV1Tests(unittest.TestCase):
    def test_roundtrip_varied_lengths(self):
        rng=random.Random(7)
        for n in (0,1,15,16,17,127,384,385,2048):
            data=bytes(rng.randrange(256) for _ in range(n))
            oligos=c.encode_bytes(data,shard_size=16,parity_shards=4,max_data_shards=24)
            self.assertEqual(c.decode_oligos(oligos),data)

    def test_dna_constraints_and_determinism(self):
        data=(b"project-brain-dna-storage"*20)+bytes(range(64))
        a=c.encode_bytes(data,shard_size=16,parity_shards=4)
        b=c.encode_bytes(data,shard_size=16,parity_shards=4)
        self.assertEqual(a,b)
        for seq in a:
            self.assertTrue(set(seq)<=set("ACGT"))
            self.assertEqual(c.max_homopolymer(seq),1)
            self.assertGreaterEqual(c.gc_fraction(seq),0.35)
            self.assertLessEqual(c.gc_fraction(seq),0.65)

    def test_recovers_full_parity_erasure_budget(self):
        data=bytes((i*37+11)%256 for i in range(900))
        oligos=c.encode_bytes(data,shard_size=16,parity_shards=4,max_data_shards=24)
        packets=[c.decode_oligo_packet(x) for x in oligos]
        remove=set()
        per_block={}
        for i,p in enumerate(packets):
            per_block.setdefault(p["block_index"],[]).append((i,p))
        for rows in per_block.values():
            for i,_ in rows[:4]:
                remove.add(i)
        surviving=[x for i,x in enumerate(oligos) if i not in remove]
        self.assertEqual(c.decode_oligos(surviving),data)

    def test_corruption_and_indel_become_erasures(self):
        data=bytes((i*19+5)%256 for i in range(600))
        oligos=c.encode_bytes(data,shard_size=16,parity_shards=5,max_data_shards=24)
        packets=[c.decode_oligo_packet(x) for x in oligos]
        by_block={}
        for i,p in enumerate(packets):
            by_block.setdefault(p["block_index"],[]).append(i)
        keep=[True]*len(oligos)
        mutated=list(oligos)
        for rows in by_block.values():
            for i in rows[:3]:
                seq=list(mutated[i])
                pos=len(seq)//2
                seq[pos]=next(base for base in "ACGT" if base!=seq[pos])
                mutated[i]="".join(seq)
            for i in rows[3:5]:
                keep[i]=False
        noisy=[seq for i,seq in enumerate(mutated) if keep[i]]
        self.assertEqual(c.decode_oligos(noisy),data)

    def test_reverse_complement_and_shuffle(self):
        data=bytes(range(256))*3
        oligos=c.encode_bytes(data,shard_size=16,parity_shards=4)
        mixed=[c.reverse_complement(s) if i%2 else s for i,s in enumerate(oligos)]
        random.Random(13).shuffle(mixed)
        self.assertEqual(c.decode_oligos(mixed),data)

    def test_fails_closed_beyond_erasure_budget(self):
        data=b"x"*300
        oligos=c.encode_bytes(data,shard_size=16,parity_shards=2,max_data_shards=24)
        packets=[c.decode_oligo_packet(x) for x in oligos]
        first_block=[i for i,p in enumerate(packets) if p["block_index"]==0]
        drop=set(first_block[:3])
        with self.assertRaises(c.DNAStorageCodecError):
            c.decode_oligos([x for i,x in enumerate(oligos) if i not in drop])

    def test_duplicates_do_not_break_valid_decode(self):
        data=b"abc123"*80
        oligos=c.encode_bytes(data,shard_size=16,parity_shards=3)
        duplicated=oligos+oligos[:5]
        self.assertEqual(c.decode_oligos(duplicated),data)

    def test_file_roundtrip(self):
        data=bytes((i*11)%256 for i in range(1024))
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td)
            inp=root/"input.bin"; dna=root/"encoded.dna"; out=root/"output.bin"
            inp.write_bytes(data)
            e=c.encode_file(inp,dna,shard_size=16,parity_shards=4)
            d=c.decode_file(dna,out)
            self.assertTrue(e["status"].startswith("PASS__"))
            self.assertTrue(d["status"].startswith("PASS__"))
            self.assertEqual(out.read_bytes(),data)

    def test_no_model_or_network_dependencies(self):
        tree=ast.parse(pathlib.Path(c.__file__).read_text(encoding="utf-8"))
        imported=set()
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):
                imported.update(n.name for n in node.names)
            if isinstance(node,ast.ImportFrom) and node.module:
                imported.add(node.module)
        forbidden={"openai","anthropic","transformers","torch","requests","httpx","urllib","socket","ollama","vllm","litellm"}
        self.assertFalse(any(name.split(".")[0] in forbidden for name in imported),sorted(imported))
        self.assertEqual(c.MODEL_DEPENDENCY_COUNT,0)
        self.assertEqual(c.NETWORK_DEPENDENCY_COUNT,0)

    def test_small_generator_is_mds_exhaustively(self):
        import itertools
        for k,m in ((1,4),(2,3),(3,3),(4,3),(5,2),(6,2)):
            g=c._generator_matrix(k,m)
            for subset in itertools.combinations(range(k+m),k):
                inv=c._matrix_invert([g[i] for i in subset])
                self.assertEqual(len(inv),k)

    def test_randomized_fault_roundtrips(self):
        rng=random.Random(20261011)
        for _ in range(120):
            n=rng.randrange(0,5000)
            data=bytes(rng.randrange(256) for _ in range(n))
            shard_size=rng.choice([8,12,16,24,32])
            parity=rng.choice([2,3,4,5,6])
            max_data=rng.choice([8,12,16,24])
            oligos=c.encode_bytes(data,shard_size=shard_size,parity_shards=parity,max_data_shards=max_data)
            packets=[c.decode_oligo_packet(s) for s in oligos]
            by_block={}
            for i,p in enumerate(packets):
                by_block.setdefault(p["block_index"],[]).append(i)
            noisy=list(oligos)
            keep=[True]*len(noisy)
            for rows in by_block.values():
                budget=min(parity,len(rows)-1)
                e=rng.randrange(budget+1)
                bad=rng.sample(rows,e)
                for j,i in enumerate(bad):
                    if j%2:
                        keep[i]=False
                    else:
                        seq=list(noisy[i])
                        pos=rng.randrange(len(seq))
                        seq[pos]=rng.choice([b for b in "ACGT" if b!=seq[pos]])
                        noisy[i]="".join(seq)
            self.assertEqual(c.decode_oligos([s for i,s in enumerate(noisy) if keep[i]]),data)


if __name__=="__main__":
    unittest.main(verbosity=2)
