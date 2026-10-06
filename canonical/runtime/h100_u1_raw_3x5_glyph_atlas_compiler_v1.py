from canonical.runtime.h100_u1_two_counter_compiler_v1 import I,P,L,assemble

# Runtime input:
# indices 0..14 = raw 3x5 target pixels, row-major bits.
# then 10 pairs: pattern,digit beginning at index 15.
def program():
    return assemble([
        # heap[0] = packed pattern = 0
        P(0),P(0),I("STORE"),
        # heap[1] = pixel index i = 0
        P(1),P(0),I("STORE"),
        L("PACK_LOOP"),
        P(1),I("LOAD"),P(15),I("LT"),I("JZ","PACK_DONE"),
        # pattern = pattern*2 + input[i]
        P(0),P(0),I("LOAD"),P(2),I("MUL"),
        P(1),I("LOAD"),I("READ"),I("ADD"),I("STORE"),
        # i++
        P(1),P(1),I("LOAD"),P(1),I("ADD"),I("STORE"),I("JMP","PACK_LOOP"),
        L("PACK_DONE"),
        # heap[2] = atlas index j = 0
        P(2),P(0),I("STORE"),
        L("LOOKUP"),
        P(2),I("LOAD"),P(10),I("LT"),I("JZ","NOT_FOUND"),
        # atlas pattern input index = 15 + 2*j
        P(2),I("LOAD"),P(2),I("MUL"),P(15),I("ADD"),I("READ"),
        P(0),I("LOAD"),I("EQ"),I("JZ","NEXT"),
        # digit input index = 16 + 2*j
        P(2),I("LOAD"),P(2),I("MUL"),P(16),I("ADD"),I("READ"),I("WRITE"),I("HALT"),
        L("NEXT"),
        P(2),P(2),I("LOAD"),P(1),I("ADD"),I("STORE"),I("JMP","LOOKUP"),
        L("NOT_FOUND"),
        P(-1),I("WRITE"),I("HALT"),
    ])

if __name__=="__main__":
    p=program(); print(len(p)); print(p.hex())
