from __future__ import annotations
import ast,json,pathlib,random,tempfile,unittest
from canonical.runtime import dna_storage_codec_v1 as codec
from canonical.runtime import dna_storage_task_kernel_v1 as k

class DNAStorageTaskKernelV1Tests(unittest.TestCase):
    def test_classifies_encode_decode_implementation_and_rejects_unrelated(self):
        a=k.classify_contract("Encode /data/input.bin into DNA oligos at /results/out.dna.",["/results"])
        b=k.classify_contract("Recover and decode DNA reads /data/reads.fasta to /results/file.bin.",["/results"])
        c=k.classify_contract("Implement a DNA storage codec as /results/codec.py.",["/results"])
        d=k.classify_contract("Fit a stellar spectrum.",["/results"])
        self.assertEqual(a['mode'],'encode'); self.assertEqual(b['mode'],'decode'); self.assertEqual(c['mode'],'implementation'); self.assertFalse(d['supported'])
        e=k.classify_contract("Implement a DNA storage codec that encodes bytes and decodes noisy reads as /results/codec.py.",["/results"])
        f=k.classify_contract("Encode then decode /data/payload.bin using DNA storage and save outputs in /results.",["/results"])
        self.assertEqual(e['mode'],'implementation'); self.assertEqual(f['mode'],'roundtrip')

    def test_encode_synthetic_task(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td); data=root/'data'; results=root/'results'; data.mkdir()
            src=data/'payload.bin'; src.write_bytes(bytes(range(256))*2)
            instr=f"Encode {src} into DNA oligos and save {results/'archive.dna'}."
            out=k.execute({'instruction':instr,'artifacts':[str(results)],'roots':[str(data)]})
            self.assertTrue(out['status'].startswith('PASS__'))
            oligos=(results/'archive.dna').read_text().splitlines()
            self.assertEqual(codec.decode_oligos(oligos),src.read_bytes())

    def test_decode_synthetic_fasta_with_reverse_complements_and_erasures(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td); data=root/'data'; results=root/'results'; data.mkdir()
            raw=bytes((i*17)%256 for i in range(700)); oligos=codec.encode_bytes(raw,parity_shards=4)
            packets=[codec.decode_oligo_packet(s) for s in oligos]; drop=set()
            by={}
            for i,p in enumerate(packets): by.setdefault(p['block_index'],[]).append(i)
            for rows in by.values(): drop.update(rows[:3])
            kept=[]
            for i,s in enumerate(oligos):
                if i in drop: continue
                kept.append(codec.reverse_complement(s) if i%2 else s)
            fasta=data/'reads.fasta'
            with fasta.open('w') as fh:
                for i,s in enumerate(kept): fh.write(f">r{i}\n{s}\n")
            outp=results/'restored.bin'
            instr=f"Decode and recover DNA reads from {fasta} and write {outp}."
            out=k.execute({'instruction':instr,'artifacts':[str(results)],'roots':[str(data)]})
            self.assertEqual(out['mode'],'decode'); self.assertEqual(outp.read_bytes(),raw)

    def test_directory_default_outputs(self):
        c=k.classify_contract("Encode this payload into a DNA storage representation.",["/results"])
        self.assertEqual(k.output_paths(c),["/results/encoded.dna"])

    def test_ambiguous_or_missing_artifacts_fail_closed(self):
        with self.assertRaises(k.DNAStorageTaskError):
            k.execute({'instruction':'Encode bytes into DNA storage.','artifacts':[],'roots':[]})

    def test_ambiguous_family_without_action_fails_closed(self):
        c=k.classify_contract("Design notes for a DNA storage system.",["/results"])
        self.assertFalse(c["supported"])
        self.assertIsNone(c["mode"])

    def test_bare_artifact_directory_uses_default_filename(self):
        c=k.classify_contract("Encode the payload to DNA and save it in /results.",["/results"])
        self.assertEqual(c["explicit_output_paths"],[])
        self.assertEqual(k.output_paths(c),["/results/encoded.dna"])

    def test_json_encode_output_decodes(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td); data=root/'data'; results=root/'results'; data.mkdir()
            raw=bytes((i*31+7)%256 for i in range(333)); src=data/'payload.bin'; src.write_bytes(raw)
            dna=results/'archive.json'
            k.execute({'instruction':f"Encode {src} to DNA at {dna}.",'artifacts':[str(results)],'roots':[str(data)]})
            outp=results/'restored.bin'
            result=k.execute({'instruction':f"Decode DNA reads from {dna} to {outp}.",'artifacts':[str(results)],'roots':[str(results)]})
            self.assertEqual(result['mode'],'decode')
            self.assertEqual(outp.read_bytes(),raw)

    def test_fastq_decode_and_n_read_is_rejected_as_erasure(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td); data=root/'data'; results=root/'results'; data.mkdir()
            raw=bytes((i*23+3)%256 for i in range(500)); oligos=codec.encode_bytes(raw,parity_shards=4)
            packets=[codec.decode_oligo_packet(s) for s in oligos]
            by={}
            for i,p in enumerate(packets): by.setdefault(p['block_index'],[]).append(i)
            mutated=list(oligos)
            for rows in by.values():
                i=rows[0]; seq=list(mutated[i]); seq[len(seq)//2]='N'; mutated[i]=''.join(seq)
            fastq=data/'reads.fastq'
            with fastq.open('w') as fh:
                for i,s in enumerate(mutated): fh.write(f"@r{i}\n{s}\n+\n{'I'*len(s)}\n")
            outp=results/'restored.bin'
            k.execute({'instruction':f"Recover DNA reads from {fastq} to {outp}.",'artifacts':[str(results)],'roots':[str(data)]})
            self.assertEqual(outp.read_bytes(),raw)

    def test_implementation_materializes_standalone_codec(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td); results=root/'results'
            outp=results/'codec.py'
            result=k.execute({'instruction':f"Implement a DNA storage codec as {outp}.",'artifacts':[str(results)],'roots':['/root/data','/definitely/inaccessible/or/missing']})
            self.assertEqual(result['mode'],'implementation')
            source=outp.read_text(encoding='utf-8')
            self.assertIn('def encode_bytes',source)
            self.assertIn('def decode_oligos',source)

    def test_cli_entrypoint_executes_exact_payload(self):
        import contextlib,io
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td); data=root/'data'; results=root/'results'; data.mkdir()
            src=data/'payload.bin'; raw=b"cli-payload"*37; src.write_bytes(raw)
            request=root/'request.json'
            request.write_text(json.dumps({'instruction':f"Encode {src} to DNA at {results/'archive.dna'}.",'artifacts':[str(results)],'roots':[str(data)]}),encoding='utf-8')
            buf=io.StringIO()
            with contextlib.redirect_stdout(buf):
                self.assertEqual(k.main([str(request)]),0)
            receipt=json.loads(buf.getvalue().strip().splitlines()[-1])
            self.assertTrue(receipt['status'].startswith('PASS__'))
            self.assertEqual(codec.decode_oligos((results/'archive.dna').read_text().splitlines()),raw)

    def test_no_model_or_network_dependencies(self):
        tree=ast.parse(pathlib.Path(k.__file__).read_text(encoding='utf-8'))
        imported=set()
        for n in ast.walk(tree):
            if isinstance(n,ast.Import): imported.update(x.name for x in n.names)
            if isinstance(n,ast.ImportFrom) and n.module: imported.add(n.module)
        forbidden={'openai','anthropic','transformers','torch','requests','httpx','urllib','socket','ollama','vllm','litellm'}
        self.assertFalse(any(x.split('.')[0] in forbidden for x in imported),sorted(imported))
        self.assertEqual(k.MODEL_DEPENDENCY_COUNT,0); self.assertEqual(k.NETWORK_DEPENDENCY_COUNT,0)

if __name__=='__main__': unittest.main(verbosity=2)
