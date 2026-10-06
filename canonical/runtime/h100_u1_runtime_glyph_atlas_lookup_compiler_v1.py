from canonical.runtime.h100_u1_two_counter_compiler_v1 import I,P,L,assemble

# Runtime input layout:
# [target_pattern, pattern_0,digit_0, pattern_1,digit_1, ... pattern_9,digit_9]
# Program is mapping-independent. It linearly searches the runtime atlas.
def program():
    return assemble([
        # heap[0]=target
        P(0),P(0),I("READ"),I("STORE"),
        # heap[1]=i=0
        P(1),P(0),I("STORE"),
        L("LOOP"),
        # if i < 10 else NOT_FOUND
        P(1),I("LOAD"),P(10),I("LT"),I("JZ","NOT_FOUND"),
        # input index for pattern = 1 + 2*i
        P(1),I("LOAD"),P(2),I("MUL"),P(1),I("ADD"),I("READ"),
        # compare to target
        P(0),I("LOAD"),I("EQ"),I("JZ","NEXT"),
        # matched: digit index = 2 + 2*i
        P(1),I("LOAD"),P(2),I("MUL"),P(2),I("ADD"),I("READ"),I("WRITE"),I("HALT"),
        L("NEXT"),
        # i=i+1
        P(1),P(1),I("LOAD"),P(1),I("ADD"),I("STORE"),I("JMP","LOOP"),
        L("NOT_FOUND"),
        P(-1),I("WRITE"),I("HALT"),
    ])

if __name__=="__main__":
    p=program()
    print(len(p)); print(p.hex())
