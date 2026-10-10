from pathlib import Path
import ast, base64, hashlib, json, zlib

PAYLOAD = """c-n<rTeIA@k^V1wPAMP=l3?C;<2bcj)~@VmU$V8u!u1@+Gs6)%Jd&Ksf8WL(ATe^etb_g<L*mlt{u%`N&v)Cm>;2mw@5|-e_D8YYw#T}Q$Fjb^e|z_*f4<{vQ`7d!aM!>4(>ta{D%!Sb2Q3=ZGNt;4^|a|J>j&L%g<DBT-(o~~)5u0p+39f*v~MWy`}W-*-hIBYtJ>cE>3`o%@op2lyePi1S-ktdKfHUe^+i3>O{Ekg>P9KJW-V>U9%CYhrk5Q-J(65v(u!UTW2<!6HhAb2++Qg@B7qcE@Ba0NqLWhHHpSNY@mlSp;s^~4iLs-sCC~}zC?`_VmQx{U)4;`{i+v|KL2MW#RRlM<LGZ(I>{QW5dA(1JZ-Cj7l+(+)>^GSK*ZtxpIluXm`g&)vlKT32Uwm2Xtk$KOZp(TN61LK`ecsus!jG@)YhDR%Ha%1n@9ARq{5JRHODJXFs>1KqHEYK9c@3qVm;Ez9>YtIq&G+MI?8Rv8`55fk80^)K?x`z#-jzLeWlvq%Q&*t4Zm+X`c%kgTo;A5*m$(xOG1N=aX)*SibBZKIm}1$sW81ZIWJ0xMXmr!#ULifUy%K659cq+dRl5XRoJG|x@yKY)2F%8xX%wt3(l)ef2G(;;`bO}MH3|_)#HgVigkwqvCUm2FE(h9_Yj0IzlImquYMO7L%7M$gJpwe}^o2cCu-E(j@@=}ac?~8l7HF$CUzJx?|4`x)Em&N388mubVDe1IJ>W(>T(P_(*u!H!T>7S7*kgWE(>(%PxRtRC77Xt8c#YP*UiWx``?Af&1-8p9R9<$2V#O~k)B<0nrk_3qYc0oOPh+tcW3eB5yjOa)=Plo3%Z+`)B3Od4K9=dR-!H0Wj=b$9!mQPZgYN~a1UnH5>;P$Sh@BcZVH~_ASF&q_&<r<}2!s(Pi1v7_n&V?xE?d<cQA_%vYuZkYsv8=(ywa^`g~Gi?tnU%gBLjQwIFduB=qP*Lv~1MiD{(jWr8!#Ty1c-!8?!M*V}J+rh3(rmvuLj30&W~e@wQyIXu>nNNcCn1G6BiNjcR(Z`H~F$0ag#wkfuD{G8*|6Oh!dF?QfBOkzX}gv<Ywzb$gVc`ubRzIDlYUHxU<rZ_!as_q%wPWn8g(Q|lvHsJqNwG<rW=)R>hr?Z2{@D2K}!uP0dD##G<&PBmH%QnQ9g%E?H;ZA(ruLJe<6raPE##0BC#8k@dpMouWqJXVr5CmUO?Y`%rRb;<#rwHYaC;f5Ls0g=9eI1IM{D{C>7I?+o7Rt;1D%)jp`MPTV2)J2Ub?d%74A2Y#vRu}13rfCaQOG?K@T$NmLUABk%oDlKK%v7os9Of)Ce9_Ess4auOiOcd>uIJ0TxD|wTxhKh(mCi&T)}jcJ_mN}`Z8=`t_V2Hkg|o{?=q0R_nO%OFZ!d=`-&F?B<uPLshuauvEq?e4EuUV5R9_P|-@J_ldGj$mL06V_f3XvE?v%mJoE>gifr{~RG2aX2&_S3_0yx=2kN4ZGzxf3<KdLKZz*uua2*XT6WLByfC>puwc?$uU@Iix51V7ldJwY84n9GraHw5E_btH%5%22zw%<{SWr34m$gewTC$)IG*2iXeLaoILQFKFAt&4IvzHx?Qz)DR4Axr3G4_J|^OWa5_#tiwszL76<$e5~^uScI9zfX=s@T5|xHV5QnNU+)()W*PR|Z$`3?XoWsHS2Wr1c)XSMx$Gv?B|6~Tk;-`!>wKMWEJAL$6uSYn+Y(p4h-(r+lU=_kSt~W=!fcNnPBPfbsx}DX(1OHUGDn<ld^asMWaB7jEj2BR*Ynut&v8~Ns#mpVjXG9<Nl6U=q3n6B@h~~h?gpyzZU9^txnCgm7IpW0()RN-?UiZT^J&_T)3j%kvmYmCe>xd^J{kKxyZmYJ_sZb!#}VG|rwVC=_u~lf#}Tf13&9)Cq+pC9(W;>VS~f6X@sM`1j`omOn?x3J=@t@BgfvxZ?9niEtVNJs9KD4LH{T&^OhM)VK8gVoL*SrjLvatpu$99|<=8@&pf#fd1(<1Q7KMAEmcswwLB>-~3nXT8Hx28{3O03s!O!Xbi!N)<D<o~ZnE55~Zy4{ntOX7M+yTVKd7GD8vOGC2_g5I!`KA(B{1W8(gk0yB+wuSk#k1@b@Gs1Ui%f!v2i|+J6l*>yfpHpIr?lP<n%i=7&0W@`>H+Bq1gtrkXE}WP)8X3>!?#z4Z$Ay+?$&c+9G>8K#bF5dYzQG9>x7-JS-bgpbZZ9RP_Q$J1`YWFWGOx5tzADrHUJr_KrN^k>pR^_4GeRj;|MhogiYXmUC&S9@r7L$7^|lS-w(quO1LtxLX+r#$q#1#Mk<KVz0#`Z5ELO(ZZU!kdK4ISLr?J7Qpv~m7#_FfVtvMZh3uGZ(;H-<HsyFRp$oG7$q^UG)@Eo1xJR?^pv=hSzXcI~@YA2&-=9sczxnc&fyIAy!Y5y$*dPI!tM#IOW!JkCbCzkv!1t42TH=BA(Zmw=CEGMtmQus$ExW(AI*2ZzGNrI9W6O?T851=;QO-840nysYbcYt-CTl+#wlZ$>m;gC*IsucvwR5vja5-~oNz9j_>^6Cz5O;H4iuQw9hg}UX-P!6TpnIv|`DB6!H``6qATXL#6KKfGx+{orH5(TM5+jN^>4A=!<XYlx(BRA|6OhGFNLOUjC_SiABi+Gz7_?|1XYTRP_2X%u(wc-&Av<yw^2FMa*1|*(HYko8$a`QpjgZwh!fZ||;D(xk({ChDQ80Td#(v=7<U0&;g_Jqche&)sxLewMkgaZO?x67&RG?tDXXqc0s6T43rR{ay{^D3-iJN^F?eg40;mC*E5BQ#LQWtdvHu+`VP8T;BU6BqR@W~APbER5;eX8^xmR}a}>-KxKys;kYEM`eNYd9&hy^v{LzEnH6T=wg2yE9Qy1%h3`m1&VPds%MmWD0f*q&9R>F;xsm>&t$^AU8N+*1v#Tz0AL!8V_Xe1VNH9!9Ulns<G?(q`F)#70CF6+os(fda2ycNPR_^ZTIh3-A%ompxbXJXun*llNS}v4TBHW$12W2mQa?M6bieYUm!35C%dk>1F*Yl18Xf>pE{N23L8nm#;0e?G|%HbWZb*F)=<OqYWO0n=&u#DwoJ|TLG^|(G;8IK#=3mqE);IlA=_^9_}lhi!ZgNaY-V3H(1056Y8j;bs?(Hl#Brx_H!=adM+w=8mP<i<hB~I&K@S)SrQ5b=Ts1>8;12PpG09A6H5Ro9!d}-wIw2LsqaJ|T^{5@1miMA-CDW+KLI?<e5EVxVS&|K%#1iq2106i>3r|1)Jl*!If&?q=^vdYOgXm2x6sN!bXPn@Oc?Wt`k5}*{KmVNTj8*;kqyJ51Ap4FG24S<qf)j#(rs}5eBm{2OkcLW%_}GmDLP}taIEN@Jnuc*mrf4VW_;et_R_f!}Y9WELc9fA$4@`5)A&N^(46jg{BhrqYYDOsr1nFEODPel-V3Zk*eL0SQ`{9F+%C?k6P$Orn$%xMB+fwrNM)c0w6rIbpC77488Xy->e!aNg@45J!T9+vjUJK^#Is(y48^k$hUn+dE#r9Z;9@vOy$7@jMZ*9rCSzF4yYatg-)o2WLoQ2u{@WAI#@J`DXQ~h9HUfk5f^fXA;W0_KPR6$r|61=0aQsyv>9Q^^%>g67|ESOcGBc>>q$D0yffT6eJ@^xij5(IkJd?VL;Z#1d*Csk@$%@Z;3K#<E}pq;$sUE5I6gM(0z@bQ5*BXCqc;vOu$?b}{qf(7ou1qnQG;Hswuw7C81dj6+IfdnS9Yl#GgJ&bDLBk*z{-~<m1Q^2`7Qd(-rK`Em^m{s35sKs<3Orc`+eDJq=51Ak2KW4Tg<Tibx=(3g2Ht^89B~=lS*7A}#zs=H`c!b;qqj<RBm3=KlJ7MMlwS696OG+r}a1UN$z>>+4gO7q4=rm*{h)_O`q90n(jg7z>k_Sy8VCZ2$iuYRd?39$4e+8t#n|hLXcS84qDlD2#^pM^#m<Wv<O&FqGtNT`g+tTAeJ4nujpaLr@#~$1#L?2e35c#+N`uN^v%ck%t6r3aTrIa8W0BEe=_cM}vvSLahQ#ECioWqLx;lsxg@Jq}hc36F>yn}NcrsQ0jEm?A9O6e|8Du3vnKA4hQ^1f77D%zD2Q!iyL49_SIH5^vfa}SK2XgNh*o}gq1#)lt6*5*p7Sq6yPx<-ik6_oAMnQ&19_{W(y^~D2r&(;l<5z`|e5In_$k|)5XWJ0|!r=QvMA-|93vrzJnc%bCT-v@6qrtm2grqDZA%)19j*1sra+i)J;#p^d0+2Sr@uCYPxpvj*DIw0)PcrgtJh*BN&?mR}6X022CEfoEZNGwkmm2_W=KEwxzQ8)~Qb3UQyp50kN$Ndv4mrwT$l0RSeK;E@^vrl{`2C;ixmdEx~;kO_QrF~dk{aMoFzjIF072S4_Eyr!jP2Jr@WoL+7js21p4};^*WZ2?zi~YQ3Q;|-YcrhREV6vu|!~U_PDQEC`ZXnLix2(qrzoue(O5uTg62jh?6a0~vB;<zU&UCq=A*v6bh&W(h<1N#oD-TZvq<Au8K@+W#kmuG8@H;yoxPx=H6j$$Q@fyRi@o>w4{2s;Pe!7aEF5<%>6AOj?e<ze{yj;TBzKWHA4p=8}QC|y#cAAr&rxQX>%8zGRB)Npc(>4c%`3#4#Y&lG1=^S!ft+<B6zEp`Ed}Z<?xr;dXkVB;S`2OTmUYG0gqHb#0w`p0WT1$NXE!;1j)p0`Ui0t!baEn`%vn7#EP+IA9u+XB>nPk2sJ637M-}5YBp>r_n<YZ1hCc2dn5TTUrlDV4F(-e*-`I*ekWL~D&_xbSgeX4Yt^x$%mw@H^d`kKPk<etWs^O?^*Pqs0iiwA=;a5fIv{=E}}W#pde<c(_1$oh#a>H%HiDz*kB^_7WC%$j;+TOJE+%ZU$1`BM--`n$~CO&`BKUYA=WFG2ovkQ0^3k)p3rk^8;_SPpTftUJhKg_EO96-tMg;hAHMX!2kg^maf>T9e?fwH{<^p~UJ#6emANf)7eq;k+Vz^jT4H@Io1$R!IWu<mkCRah+40V+i?9h00Z;uS-Z=$PxNIXO}AOmorkIg-EC(azC3v;q)@JGU3q)CZtj+db0?fD?K%wIv>l_*Ar5B%rhRA<i}tBcB)b_o6O0USj|#1r(0r`b(Oi%gdN;zt~k2Ys5^MO3_p3j$n^qHFsB4QAy8$7XN#bqQwcn<s;D?Is-Vf}RDhncp-|z-cLJW1mw*+tB!V?|5|kw$320;y5ja&T1Mm^8ccl!+Ihvw!Le~;7TO9xMar*HxA4l~ZE`ug!{^5r{NJjBfDTWYP0GatFJO#)jmUlhZ)xzURe~6BmJ`avL9Aje+#$b`aVvit)!>DDL53M=!Rsvz~phSX8$k4Bqv50>6096OthuH#fQ8R<GAe+!K#wNT7u{nGmv}%C;jygofbCuGwd{2MAh7Yb8;Qe<(z8_k%di&)BREOQ~StP&*+63HBMv;Zt96Zmq53(6>uHwUBLQYklSxhay=GyBK$f9cnJ_Ogi#@S$EXw9GyKo8J)v24qlp2?P)d@Ch~eZ0*ex2;kD)loWy-=vD0AQ_Yg<Q(?#I6^)gNBOu5k`yUSXIM2#AM{U_QWm2#tO(HwKSb!Lhygkxhy9BhUiJ88*p6_D+7ZfvcEZjvJL>X~oxre95D_24lYIP1k<UjokLxF}+S5F$7hnkL8Mqd5kwqueKFjbS{HQrKEl-^@uw(>L5eUJ2n;-rlpnsB)BR_ojvGz!;?R%}b9yKPEa?W+%iE-p3Wt_`yM2ayj(a2;o5-b%6nkv$mhh_pQ;Myax<^GtLTm6xkpuOygYQ|Pb$<$!p!x$Cra7zgTsfA{kV}S#2T7)ENB<XppIBj$@cBFhHwn0x|i7;64)dL>{HMnmnMFI^1bB;SYjIw7#iz(tnQe;jk^ycsY#iSdUU<B^0HNk>+n%6q_ony9~tA^;dlYJ|QHqTH=!-ejY0LDc%WrR>Nc2Li}jXks-9(oP~(NIL$NQ<uhbzKy{srBE@u~_R^%)4PwrBvvb%k>1>W244K%!^F#|MKTp`VdQ>Lg}Zd{V8gHirP<6Texe7e0iP4Yjj!`bDq)_E$a-$<gOi(?^8#lyi~Sx?SL&Tlpy+J8di+l)k$Vkx)7%Dn7BZ<B&8VTfj}(17(BZdt<%oin_RUQb1&_nIkoBFtOEvY!=La!Ae+jny@g`%>`sU?lL)F89nDC>VK(Y+->Tfva$El%F(I>}Wui`irDxxT+2f#OB-Y6;fD{8)P+E^{K+P`SrWbWf)hZj{xx(#$TO`IKFC}Umfv^eg0Z)3YltPyiMJhTT<jSxdqT<SaHK)rVT20HFIlN<TX%1=eZ}zzGe0wSTd}R;unuM>#9UY$y#lu|PR4Tp1V)pA>aU-C-?(n_m;rWueXO?s?jKpzSSIl9@Gi^D8&jtmfeS9C;;l&oZhpwqu%xlhJJ&;dRevu8lW^q*;7{bxuh#ZVF@Y*C4wi-CD6F!%QTp<q;&u1f}3|@}?3q;omIin3o!DTI&ZNhuG-~<lKXsrhvp|wIF3s!I*{N#GQW6vq+$9+|mI1tfrS+iu-YToNDD5e<$xQ+5>pY2&Ge|X3tHcj|d*-MzRl3CI)!Cz)51vKbz-Tf|Yvbw&QiZDE}qWA9=R$$(?kuAlDU~b+`ZP*CBfDe*D$nL0adc}YhH5|)MjzETl;8-(djxS1tM2!{fkNF8J5J0IIVyZ<0VJ&JgYuL~L<q@MA;pRZ3+TOgHI%2BF4tRk%jx{!zVafWod>!FGoMZWDRy5-m^*;OjgFj_>u3}CY1~*{FjKT1H`%MM!YER8fY4J@rGXds(CWEJ`s*Gf(2i#yJDg37ljp0~vK}Xq{Z*QnZ>yeO-uu%)nX^+v+v_c@=!4I`;^l>E3`^xoEY#O8`Cj(4QgJ7fxj1Oa2k8Dr`;jU{2-7(7gre#PGOhyIFiVQ&K2((cbqi9U_FYX-V`$@bidtk5xulFP5Uq(M+=Co9?a-%lI$sBS=ZBOXm|6W7Q)E)8Jei>$Q=Z?-A_i{l^o%yARfl-7dTT|KBj0)Zq)ozs@(Rli<#Ivsj<ZvZML{-M%3T*lky=j4;FOU<sgx<FE&vR~<(EGOoly5hdcuxHintA0CJhnAsh6y?m#H2b7Z^bshYno<Xb3eB@=Ku+_ALyuGr*y`-=4|^p!;4r+4+DH+gh4SIK6KlUR-8VPQ=njrRm(7nBKZi4lKDkcoDjvNp>(xX7Igm8PK643T5XU~)EfkfJO>K+fiXtd@0T2~^L0<OGFQ}km3=8IhbwJ>K!09K_p`~~YsPl3K#3qGDDCm&`1!{tW|}K1{W;(3NJ0a?rEh!`a7HN$tY+pJ=PBUN)kSe&mN}de%mn*Si4@>tJtOnI7G-jB8nFr^&2%T|+x4p8`oA5UVLlBsRlQ@TIbN-{46^r@j_@pwBVt)_X$|J<E@sP{@AE|lJ{lEi10#reK58*>Sz<osfFeFvDD%xxJ~?Kq$ysp;X6BH<d_*i-?9N7Xz9m2EfGxZPlA|f<w4$-?<CVgMiad+78XNTwwe3qASq2us@cEh?i(@g(E=Bbx`fV%xRjPZJY@}LC)DtBK^NA(O&G~uN4pg?yDEKh+s%2O-xEal-U<e;gZ44}Q9M1F;k{$Q#3Q~wF4JC-dO(<#=CM}ZYb9a>Ym~<FJngDlbBvYzmShZM=&??L+N9INPaUflT3mW=o_e|hF{C329{{;`1Bty-ko^5eg_^1L36W<R$>g+p7+dmffi20~}dN-e||L#wx&8_ff+J`dc{|h9OwT={cY)b_V7n<z*7Ur=2-8Tz-z#Y;XJ+F|CZ|dT<e(VQV*ea)4Ps{$;W~rvI@#EFDU-r%V>2(1=W%gJv6Q4J@g4=|Pzu3%*1(zyU@B92G!@{#tSa$w`{!41$BVR7i=&MPt-Nz8j?!}fG;S$@GIkdR8+2)wVu`OR<CEHcGU%6W2H)bl2;4?+}?A?6{t@b=BX^OPpeq*EZyts;I-^-{zA+9TebF*Ip{N58^Qvqf&u8`tksQWBU6?UPl;yxG|J0frk%Ne1*8!+Q--zhA4-xE5}hDejFYKkdi18;Dvu_A=RI!35z$C~?C^z-Kftr|IHT{jTj;l6|X7dJ`~N(p!i#v28RE9a0pbE;T_Nz)Lx&%l|0#G1FF<~)9Zd;Yh6KS5yHR~4pJZIgNQlU8M{_GWiRPR^px`&fQZLFiZKE7~8h`+Z$Zj4|Nf_N%{+gsk$7d7@UT!nfQa`pRIK%!e*gG8S}lu|2Wh=kqqY#LvJ~rd6}H>+~r5fn(YBsv(RFFydsu-9U$dkBBiOndqQ~?#;WooXEcIP%FhK$Z=Z1s)3I@pH|j1P2aVY(@u1{RYYOd4y`03;zV&uC=pz;0qYSBVr)TX48oE5J_Q}R%C{fwmPE#b+*iar|8tMyxAZ-sj4x)0=Y$R^Dr6tPJ^Zw?shQt76YqJM#cxX;TC<;8vzM*e@5lPJChTPs_Rxgdi^*ftBACp6Y?V?&(>G@G4XcI`0%4ycWxhQ!bOaez(07#dEg9Pp34zU9!|(p}um1<bH0Id"""

def _qnodes(tree):
    out = {}
    def walk(body, prefix=()):
        for ch in body:
            if isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef)):
                q = '.'.join(prefix + (ch.name,))
                out[q] = ch
                walk(ch.body, prefix + (ch.name,))
            elif isinstance(ch, ast.ClassDef):
                walk(ch.body, prefix + (ch.name,))
            else:
                kids = []
                for _, v in ast.iter_fields(ch):
                    if isinstance(v, list):
                        kids += [x for x in v if isinstance(x, ast.stmt)]
                    elif isinstance(v, ast.stmt):
                        kids.append(v)
                if kids:
                    walk(kids, prefix)
    walk(tree.body)
    return out

def apply(root):
    spec = json.loads(zlib.decompress(base64.b85decode(PAYLOAD)).decode())
    root = Path(root)
    changed = []
    for rel, fs in spec.items():
        p = root / rel
        data = p.read_bytes()
        got = hashlib.sha256(data).hexdigest()
        if got != fs['base_sha256']:
            raise RuntimeError(f'base drift for {rel}: {got}')
        txt = data.decode()
        lines = txt.splitlines()
        nodes = _qnodes(ast.parse(txt))
        reps = []
        for q in fs['qnames']:
            n = nodes[q]
            indent = ' ' * n.col_offset
            kw = 'async def' if isinstance(n, ast.AsyncFunctionDef) else 'def'
            seg = f'{indent}{kw} {n.name}(*args, **kwargs):\n{indent}    raise NotImplementedError("Brain bounded exact-symbolic contract")'
            reps.append((n.lineno, n.end_lineno, seg))
        for start, end, seg in sorted(reps, reverse=True):
            lines[start-1:end] = seg.split('\n')
        out = ('\n'.join(lines) + '\n').encode()
        got2 = hashlib.sha256(out).hexdigest()
        if got2 != fs['target_sha256']:
            raise RuntimeError(f'target mismatch for {rel}: {got2}')
        p.write_bytes(out)
        changed.append(rel)
    return changed
