from canonical.runtime.h100_u1_two_counter_compiler_v1 import I,P,L,assemble

def program():
    return assemble([
        P(0),P(0),I("READ"),I("STORE"),
        P(0),I("LOAD"),P(-7),I("LT"),I("JZ","MID"),
        P(0),I("LOAD"),P(2),I("MUL"),P(3),I("ADD"),I("WRITE"),I("HALT"),
        L("MID"),
        P(0),I("LOAD"),P(13),I("LT"),I("JZ","HIGH"),
        P(0),I("LOAD"),I("DUP"),I("MUL"),P(5),I("SUB"),I("WRITE"),I("HALT"),
        L("HIGH"),
        P(0),I("LOAD"),P(3),I("MUL"),P(11),I("SUB"),I("WRITE"),I("HALT"),
    ])

def truth(x:int)->int:
    if x < -7:
        return 2*x+3
    if x < 13:
        return x*x-5
    return 3*x-11

if __name__=="__main__":
    p=program()
    print(len(p))
    print(p.hex())
