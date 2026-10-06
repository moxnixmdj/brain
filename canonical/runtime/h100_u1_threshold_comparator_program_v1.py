from canonical.runtime import h100_reference_machine_u1_v1 as u

PROGRAM=[
("READ",),("STORE",0),("READ",),("STORE",1),("READ",),("STORE",2),("READ",),("STORE",3),
("READ",),("STORE",4),("LOAD",4),("LOAD",0),("LT",),("JZ",17),("LOAD",1),("WRITE",),("JMP",26),
("LOAD",4),("LOAD",0),("EQ",),("JZ",24),("LOAD",2),("WRITE",),("JMP",26),("LOAD",3),("WRITE",),
("READ",),("STORE",4),("LOAD",4),("LOAD",0),("LT",),("JZ",35),("LOAD",1),("WRITE",),("JMP",44),
("LOAD",4),("LOAD",0),("EQ",),("JZ",42),("LOAD",2),("WRITE",),("JMP",44),("LOAD",3),("WRITE",),
("HALT",)
]
PROGRAM_BYTES=u.encode(PROGRAM)
assert len(PROGRAM_BYTES)==73
