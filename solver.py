_M='max_willingness'
_L='min_score'
_K='task_id_list'
_J='scarce'
_I='ratio'
_H='cover'
_G='gain'
_F='inf'
_E=1.
_D=False
_C=.0
_B=True
_A=None  #4
import itertools,random,time
_GROUP_COST_CACHE={}
_GROUP_COST_CACHE_LIMIT=250000
_POPCOUNT_TABLE=[bin(A).count('1')for A in range(256)]
_LOW_BIAS_ACTIVE=_D
def solve(input_text):
	h=input_text;global _GROUP_COST_CACHE,_LOW_BIAS_ACTIVE;_GROUP_COST_CACHE={};i=time.monotonic();A=i+8.7;b=h.strip().splitlines();A2=1 if b and b[0].startswith(_K)else 0;C=[];B=set()
	for(A3,S)in enumerate(b[A2:]):
		S=S.strip()
		if not S:continue
		j=S.split('\t')
		if len(j)<4:continue
		T,U,A4,A5=j[:4];T=T.strip();U=U.strip();c=tuple(A.strip()for A in T.split(',')if A.strip())
		if not c or not U:continue
		try:A6=float(A4);A7=float(A5)
		except ValueError:continue
		C.append((T,c,U,A6,A7,A3))
		for A8 in c:B.add(A8)
	if not C:return[]
	E=[];H=[A for A in C if len(A[1])==1];d=len({A[2]for A in C});L=len(B);e=sum(A[4]for A in C)/len(C);A9=sum(A[4]for A in H)/len(H)if H else e;G=d<=L;F=e<.27;J=F and not G and L==30 and d>=50 and A9<.25
	if _D and J and not _LOW_BIAS_ACTIVE:
		_LOW_BIAS_ACTIVE=_B
		try:return solve(_bias_low_input_text(h,.3))
		finally:_LOW_BIAS_ACTIVE=_D
	O=d>=len(B)*3//2 and _singles_cover_all_tasks(H,B);k=any(len(A[1])>=2 for A in C);AA=any(len(A[1])>2 for A in C);f=G and(len(C)<1500 or e<.4)
	if f:A=i+8.85
	if L<=8 and time.monotonic()<A-.35:
		l=_solve_tiny_column_search(C,B,min(A,time.monotonic()+.65))
		if l:E.append(l)
	if H:
		I=_solve_single_task_multidispatch(H,B)
		if G:g=min(A,time.monotonic()+1.2);I=_reassign_single_solution(I,H,B,g);I=_rebalance_single_solution(I,H,B,g);I=_reassign_single_solution(I,H,B,g)
		else:
			if not F:AB=min(A,time.monotonic()+5.5)if O else min(A,time.monotonic()+_E);I=_destroy_repair_single_solution(I,H,B,AB)
			I=_reassign_single_solution(I,H,B,A);I=_rebalance_single_solution(I,H,B,A);I=_reassign_single_solution(I,H,B,A)
		E.append(I)
		if O and time.monotonic()<A-1.9:
			m=_random_single_start_solution(H,B,A)
			if m:E.append(m)
		if O and k and not F and time.monotonic()<A-1.35:
			n=_solve_pair_potential_matching(C,B,min(A,time.monotonic()+1.1),lookahead=5,flexible_initial=_B)
			if n:E.append(n)
		if O and k and not F and time.monotonic()<A-1.35:
			o=_solve_pair_potential_matching(C,B,min(A,time.monotonic()+1.1),lookahead=5,flexible_initial=_D)
			if o:E.append(o)
	V=[]
	if F and time.monotonic()<A-.8:
		if J and time.monotonic()<A-1.2:
			p=_solve_low_global_column_search(C,B,min(A,time.monotonic()+.75))
			if p:E.append(p)
		AC=(.25,_E/3.,.5)if J else(_E/3.,)
		for q in AC:
			if time.monotonic()>=A-.55:break
			M=_scale_scores(C,q);V.append(M);W=[A for A in M if len(A[1])==1]
			if W:E.append(_solve_single_task_multidispatch(W,B))
			for P in(_G,_H,_I):
				if time.monotonic()<A-.35:E.append(_solve_disjoint_then_multidispatch(M,B,mode=P,deadline=A))
			if time.monotonic()<A-.45:
				r=_solve_pair_potential_matching(M,B,A,lookahead=6,flexible_initial=_B)
				if r:E.append(r)
			if J and q>=_E/3. and time.monotonic()<A-.65:
				s=_solve_low_column_search(W if W else H,B,min(A,time.monotonic()+.45))
				if s:E.append(s)
		if J and _LOW_BIAS_ACTIVE and time.monotonic()<A-1.05:
			X=_bias_scores_for_willingness(C,.3);V.insert(0,X);Y=[A for A in X if len(A[1])==1]
			if Y:E.append(_solve_single_task_multidispatch(Y,B))
			for P in(_G,_H,_I):
				if time.monotonic()<A-.35:E.append(_solve_disjoint_then_multidispatch(X,B,mode=P,deadline=A))
			if time.monotonic()<A-.45:
				t=_solve_pair_potential_matching(X,B,A,lookahead=6,flexible_initial=_B)
				if t:E.append(t)
			if Y and time.monotonic()<A-.65:
				u=_solve_low_column_search(Y,B,min(A,time.monotonic()+.45))
				if u:E.append(u)
	if not O or F or AA:
		AD=(_G,_H)if F else(_I,_G,_H)
		for P in AD:
			if time.monotonic()<A-.35:E.append(_solve_disjoint_then_multidispatch(C,B,mode=P,deadline=A))
		if time.monotonic()<A-.55:
			v=_solve_pair_potential_matching(C,B,A,lookahead=5 if F else 4,flexible_initial=F)
			if v:E.append(v)
		if time.monotonic()<A-.25:E.append(_solve_sparse_cover(C,B,A))
		if G and time.monotonic()<A-_E:
			w=_solve_scarce_k2_column_search(C,B,min(A,time.monotonic()+.65))
			if w:E.append(w)
			if G and time.monotonic()<A-_E:
				x=_solve_scarce_bundle_mcf_enum(C,B,min(A,time.monotonic()+.85))
				if x:
					if f and time.monotonic()<A-1.2:
						Q=_scarce_bundle_insertion_repair_solution(x,C,B,min(A,time.monotonic()+.3),max_windows=42,max_window_tasks=14)
						if _solution_expected_cost(Q,C,B)<_solution_expected_cost(x,C,B)-1e-09:x=_drop_unprofitable_groups(Q,C,B)
					E.append(x)
		if G and time.monotonic()<A-2.1:
			y=_solve_scarce_elite_column_recombine(C,B,E,min(A,time.monotonic()+3.))
			if y:E.append(y)
		if G and time.monotonic()<A-_E:
			Z=_solve_scarce_bundle_group_mcf_enum(C,B,min(A,time.monotonic()+.75))
			if Z:
				if time.monotonic()<A-1.35:Z=_scarce_polish_candidate(Z,C,B,min(A,time.monotonic()+1.2))
				E.append(Z)
		AE=max((_solution_covered_count(A,C)for A in E if A),default=0)
		if G and AE<len(B)-1 and time.monotonic()<A-.9:
			z=_sparse_beam_search(C,B,min(A,time.monotonic()+_E),coverage_first=_B)
			if z:E.append(z)
	E.append(_fallback_official_greedy(C))
	if f:D=_pick_hard_scarce_best(E,C,B);D=_drop_unprofitable_groups(D,C,B)
	elif G:D=_pick_scarce_best(E,C,B);D=_drop_unprofitable_groups(D,C,B)
	elif J:D=_pick_low_robust_best(E,C,B)
	else:D=min((A for A in E if A),key=lambda s:_solution_expected_cost(s,C,B))
	if time.monotonic()<A-.18:D=_local_improve_mixed_solution(D,C,B,A,include_pair_rewire=G)
	if G and time.monotonic()<A-.3:
		D=_reassign_mixed_solution(D,C,B,A);D=_drop_unprofitable_groups(D,C,B)
		if time.monotonic()<A-.18:D=_local_improve_mixed_solution(D,C,B,A,include_pair_rewire=_B);D=_drop_unprofitable_groups(D,C,B)
		if time.monotonic()<A-.85:D=_column_alns_repair_solution(D,C,B,min(A,time.monotonic()+.75),mode=_J,max_window_tasks=12,top_riders_per_task_key=8,option_limit=55,max_k=4);D=_drop_unprofitable_groups(D,C,B)
		if time.monotonic()<A-.45:
			Q=_scarce_bundle_insertion_repair_solution(D,C,B,min(A,time.monotonic()+.34),max_windows=34,max_window_tasks=14)
			if _solution_expected_cost(Q,C,B)<_solution_expected_cost(D,C,B)-1e-09:D=_drop_unprofitable_groups(Q,C,B)
		if time.monotonic()<A-.35:
			N=_pairwise_column_exchange_solution(D,C,B,min(A,time.monotonic()+.3),top_riders_per_task_key=8,max_k=4,option_limit=55,max_window_tasks=10,max_pairs=28)
			if _solution_covered_count(N,C)>=_solution_covered_count(D,C)and _solution_expected_cost(N,C,B)<_solution_expected_cost(D,C,B)-1e-09:D=N;D=_drop_unprofitable_groups(D,C,B)
		if time.monotonic()<A-.32:
			N=_triple_column_exchange_solution(D,C,B,min(A,time.monotonic()+.27),top_riders_per_task_key=8,max_k=4,option_limit=60,max_window_tasks=12,max_triples=16)
			if _solution_covered_count(N,C)>=_solution_covered_count(D,C)and _solution_expected_cost(N,C,B)<_solution_expected_cost(D,C,B)-1e-09:D=N;D=_drop_unprofitable_groups(D,C,B)
		if time.monotonic()<A-.24:
			A0=_scarce_eject_extra_to_uncovered(D,C,B,min(A,time.monotonic()+.18))
			if _solution_expected_cost(A0,C,B)<_solution_expected_cost(D,C,B)-1e-09:D=A0;D=_drop_unprofitable_groups(D,C,B)
		if time.monotonic()<A-.22:
			A1=_shift_couriers_between_groups(D,C,B,min(A,time.monotonic()+.18),max_moves=18)
			if _solution_expected_cost(A1,C,B)<_solution_expected_cost(D,C,B)-1e-09:D=_drop_unprofitable_groups(A1,C,B)
	if F and time.monotonic()<A-.34:
		K=_reassign_mixed_solution(D,C,B,min(A,time.monotonic()+.14))
		if _solution_expected_cost(K,C,B)<_solution_expected_cost(D,C,B)-1e-09:D=K
	if F and V and time.monotonic()<A-.18:
		for M in V:
			if time.monotonic()>=A-.18:break
			a=min((A for A in E if A),key=lambda s:_solution_expected_cost(s,M,B));a=_local_improve_mixed_solution(a,M,B,A,include_pair_rewire=_B)
			if _solution_expected_cost(a,C,B)<_solution_expected_cost(D,C,B)-1e-09:D=a
	if J and time.monotonic()<A-.78:D=_low_worst_window_repair_solution(D,C,B,min(A,time.monotonic()+.62))
	if F and time.monotonic()<A-.35:D=_pairwise_column_exchange_solution(D,C,B,min(A,time.monotonic()+.3),top_riders_per_task_key=8,max_k=4,option_limit=55,max_window_tasks=10,max_pairs=28)
	if F and time.monotonic()<A-.32:D=_triple_column_exchange_solution(D,C,B,min(A,time.monotonic()+.27),top_riders_per_task_key=8,max_k=4,option_limit=60,max_window_tasks=12,max_triples=16)
	if F and time.monotonic()<A-.32:D=_shift_couriers_between_groups(D,C,B,min(A,time.monotonic()+.26),max_moves=30)
	if 9<=L<=35 and not G and not F and time.monotonic()<A-.55:D=_repair_worst_window_solution(D,C,B,min(A,time.monotonic()+.75))
	if 9<=L<=35 and not G and not F and time.monotonic()<A-.75:
		D=_column_alns_repair_solution(D,C,B,min(A,time.monotonic()+.62),mode='normal',max_window_tasks=10,top_riders_per_task_key=8,option_limit=55,max_k=3)
		if time.monotonic()<A-.35:D=_pairwise_column_exchange_solution(D,C,B,min(A,time.monotonic()+.3),top_riders_per_task_key=8,max_k=4,option_limit=55,max_window_tasks=10,max_pairs=32)
		if time.monotonic()<A-.32:D=_triple_column_exchange_solution(D,C,B,min(A,time.monotonic()+.27),top_riders_per_task_key=8,max_k=4,option_limit=60,max_window_tasks=12,max_triples=16)
	if time.monotonic()<A-.22:
		K=_reassign_mixed_solution(D,C,B,min(A,time.monotonic()+.35))
		if _solution_expected_cost(K,C,B)<_solution_expected_cost(D,C,B)-1e-09:D=K
	if f and time.monotonic()<A-3.05:
		Q=_scarce_bundle_insertion_repair_solution(D,C,B,min(A,time.monotonic()+2.8),max_windows=60,max_window_tasks=14)
		if _solution_expected_cost(Q,C,B)<_solution_expected_cost(D,C,B)-1e-09:
			D=_drop_unprofitable_groups(Q,C,B)
			if time.monotonic()<A-.2:
				K=_reassign_mixed_solution(D,C,B,min(A,time.monotonic()+.18))
				if _solution_expected_cost(K,C,B)<_solution_expected_cost(D,C,B)-1e-09:D=K
	if f and time.monotonic()<A-1.35:
		R=_solve_scarce_elite_column_recombine(C,B,[D],min(A,time.monotonic()+.85))
		if R:
			R=_scarce_polish_candidate(R,C,B,min(A,time.monotonic()+.55))
			if _solution_expected_cost(R,C,B)<_solution_expected_cost(D,C,B)-1e-09:D=_drop_unprofitable_groups(R,C,B)
	if G and time.monotonic()<A-.24:D=_shift_couriers_between_groups(D,C,B,min(A,time.monotonic()+.18),max_moves=18)
	if J and time.monotonic()<A-1.35:D=_low_deep_window_repair_solution(D,C,B,min(A,time.monotonic()+1.2))
	if J and time.monotonic()<A-.95:D=_low_late_acceptance_repair_solution(D,C,B,min(A,time.monotonic()+.85))
	if J and time.monotonic()<A-.32:D=_shift_couriers_between_groups(D,C,B,min(A,time.monotonic()+.24),max_moves=30)
	if 9<=L<=35 and not G and not F and time.monotonic()<A-.85:D=_normal_worst_related_repair_solution(D,C,B,min(A,time.monotonic()+.45))
	if 9<=L<=35 and not G and not F and time.monotonic()<A-.95:D=_normal_worst_related_repair_solution(D,C,B,min(A,time.monotonic()+.75))
	return D
def _singles_cover_all_tasks(singles,all_tasks):A={A[1][0]for A in singles};return all(B in A for B in all_tasks)
def _scale_scores(candidates,factor):return[(A,B,C,D*factor,E,F)for(A,B,C,D,E,F)in candidates]
def _bias_scores_for_willingness(candidates,alpha):return[(B,C,D,E/(A+.05)**alpha,A,F)for(B,C,D,E,A,F)in candidates]
def _bias_low_input_text(input_text,alpha):
	C=input_text;B=C.strip().splitlines()
	if not B:return C
	D=1 if B[0].startswith(_K)else 0;E=list(B[:D])
	for F in B[D:]:
		A=F.split('\t')
		if len(A)>=4:
			try:G=float(A[2]);H=float(A[3]);A[2]=f"{G/(H+.05)**alpha:.10f}"
			except ValueError:pass
		E.append('\t'.join(A))
	return'\n'.join(E)+'\n'
def _solve_single_task_multidispatch(singles,all_tasks):
	H=singles;F=all_tasks;C={A:[]for A in F};I={A:1e2 for A in F};D=set()
	while _B:
		B=_A;J=_C;K=_C
		for G in H:
			S,P,Q,T,U,V=G
			if Q in D:continue
			A=P[0];R=I.get(A,1e2);L=_group_expected_cost(C.get(A,[]),1,extra=G);M=L-R
			if M<J-1e-12:J=M;K=L;B=G
		if B is _A:break
		A=B[1][0];C[A].append(B);I[A]=K;D.add(B[2])
	for A in sorted(F):
		if C.get(A):continue
		N=[B for B in H if B[1][0]==A and B[2]not in D]
		if not N:continue
		B=min(N,key=lambda c:_single_expected_cost(c));C[A].append(B);D.add(B[2])
	O=[]
	for A in sorted(C):
		E=C[A]
		if not E:continue
		E=sorted(E,key=lambda c:(c[3],-c[4],c[5]));O.append((A,[A[2]for A in E]))
	return O
def _single_expected_cost(cand):A=cand;return A[4]*A[3]+(_E-A[4])*1e2
def _group_expected_cost(rows,task_count,extra=_A):
	G=extra;C=task_count;A=rows
	if G is not _A:A=list(A)+[G]
	if not A:return 1e2*C
	A=list(A);H=C,tuple(sorted((A[5],A[3],A[4])for A in A));I=_GROUP_COST_CACHE.get(H)
	if I is not _A:return I
	J=len(A)
	if J>12:B=_group_expected_cost_dp(A,C)
	else:
		B=_C
		for L in range(1<<J):
			D=_E;K=_C;E=0
			for(M,F)in enumerate(A):
				if L>>M&1:D*=F[4];K+=F[3];E+=1
				else:D*=_E-F[4]
			if E:B+=D*(K/E)
			else:B+=D*(1e2*C)
	if len(_GROUP_COST_CACHE)<_GROUP_COST_CACHE_LIMIT:_GROUP_COST_CACHE[H]=B
	return B
def _group_expected_cost_dp(rows,task_count):
	D=rows;F=_E
	for A in D:F*=_E-A[4]
	G=F*(1e2*task_count)
	for(L,A)in enumerate(D):
		H=A[4]
		if H<=_C:continue
		B=[_E]
		for(M,N)in enumerate(D):
			if M==L:continue
			I=N[4];E=[_C]*(len(B)+1)
			for(J,C)in enumerate(B):E[J]+=C*(_E-I);E[J+1]+=C*I
			B=E
		K=_C
		for(O,C)in enumerate(B):K+=C/(O+1)
		G+=A[3]*H*K
	return G
def _solve_tiny_column_search(candidates,all_tasks,deadline):return _search_column_window(candidates,all_tasks,deadline,top_riders_per_task_key=10,max_k=4,option_limit=80)
def _solve_low_column_search(singles,all_tasks,deadline):
	A=singles
	if not A:return[]
	return _search_column_window(A,all_tasks,deadline,top_riders_per_task_key=10,max_k=3,option_limit=28)
def _solve_low_global_column_search(candidates,all_tasks,deadline):
	A=candidates
	if not A:return[]
	return _search_column_window(A,all_tasks,deadline,top_riders_per_task_key=8,max_k=4,option_limit=28)
def _solve_scarce_k2_column_search(candidates,all_tasks,deadline):
	A=candidates
	if not A:return[]
	return _search_column_window(A,all_tasks,deadline,top_riders_per_task_key=10,max_k=2,option_limit=60)
def _search_column_window(candidates,all_tasks,deadline,top_riders_per_task_key,max_k,option_limit):
	O=deadline;F=candidates;del all_tasks;F=_canonical_candidates(F);P=sorted({B for A in F for B in A[1]});Q={B:A for(A,B)in enumerate(P)};b={B:A for(A,B)in enumerate(sorted({A[2]for A in F}))};R={}
	for G in F:
		if all(A in Q for A in G[1]):R.setdefault(G[0],[]).append(G)
	H=[]
	for B in R.values():
		if time.monotonic()>O-.05:break
		B=sorted(B,key=lambda c:(_group_expected_cost([c],len(c[1])),-c[4],c[5]))[:top_riders_per_task_key]
		if not B:continue
		S=0
		for c in B[0][1]:S|=1<<Q[c]
		D=len(B[0][1])
		for d in range(1,min(max_k,len(B))+1):
			for K in itertools.combinations(B,d):
				L=0;T=_D
				for G in K:
					U=1<<b[G[2]]
					if L&U:T=_B;break
					L|=U
				if T:continue
				V=_group_expected_cost(K,D);W=V-1e2*D
				if W<-1e-09:H.append((W,V,S,L,K))
	if not H:return[]
	D=len(P);M=(1<<D)-1;I=[[]for A in range(D)]
	for A in H:
		e=A[2]
		for X in range(D):
			if e>>X&1:I[X].append(A)
	E=[];C=_C;Y=0;Z=0
	for A in sorted(H,key=lambda c:(c[0]/max(1,_popcount(c[2])),c[0])):
		if A[2]&Y or A[3]&Z:continue
		Y|=A[2];Z|=A[3];E.append(A);C+=A[0]
	if C>_C:E=[];C=_C
	for f in I:f.sort(key=lambda c:(c[0],len(c[4]),c[4][0][0],tuple(A[2]for A in c[4])))
	g=[min(_C,min((A[0]for A in A),default=_C))for A in I];J=[]
	def h(decided_task_mask,current_reduced):
		B=current_reduced;A=M&~decided_task_mask
		while A:C=A&-A;D=C.bit_length()-1;B+=g[D];A^=C
		return B
	def i(decided_task_mask,courier_mask):
		E=decided_task_mask;A=M&~E;B=_A;C=[]
		while A:
			F=A&-A;G=F.bit_length()-1;D=[A for A in I[G]if not A[2]&E and not A[3]&courier_mask]
			if B is _A or len(D)<len(C):
				B=G;C=D
				if not D:break
			A^=F
		return B,C
	def N(decided_task_mask,courier_mask,current_reduced):
		F=courier_mask;B=decided_task_mask;A=current_reduced;nonlocal E,C
		if time.monotonic()>O-.02:return
		if h(B,A)>=C-1e-09:return
		if B==M:
			if A<C-1e-09:C=A;E=list(J)
			return
		G,H=i(B,F)
		if G is _A:
			if A<C-1e-09:C=A;E=list(J)
			return
		for D in H[:option_limit]:J.append(D);N(B|D[2],F|D[3],A+D[0]);J.pop()
		N(B|1<<G,F,A)
	N(0,0,_C);a=[]
	for A in sorted(E,key=lambda c:(min(A[5]for A in c[4]),c[4][0][0],tuple(A[2]for A in c[4]))):B=sorted(A[4],key=lambda c:(c[3],-c[4],c[5]));a.append((B[0][0],[A[2]for A in B]))
	return a
def _canonical_candidates(candidates):
	B={}
	for A in candidates:B[A[0],A[2]]=A
	return sorted(B.values(),key=lambda c:c[5])
def _solve_scarce_elite_column_recombine(candidates,all_tasks,seed_solutions,deadline):
	P=deadline;O=all_tasks;G=candidates;Q=sorted(O)
	if not Q:return[]
	a={B:A for(A,B)in enumerate(Q)};b={B:A for(A,B)in enumerate(sorted({A[2]for A in G}))};R={(A[0],A[2]):A for A in G};I={}
	def S(rows,source_rank=0):
		J=source_rank;A=rows
		if not A:return
		O=A[0][0];F=A[0][1]
		if any(A[0]!=O or A[1]!=F for A in A):return
		G=[A[2]for A in A]
		if len(G)!=len(set(G)):return
		H=0
		for P in F:
			B=a.get(P)
			if B is _A:return
			H|=1<<B
		C=0
		for Q in G:
			B=b.get(Q)
			if B is _A:return
			K=1<<B
			if C&K:return
			C|=K
		L=len(F);D=_group_expected_cost(A,L);M=1e2*L-D
		if M<=1e-09:return
		N=H,C;R=M,D,H,C,tuple(A),J;E=I.get(N)
		if E is _A or D<E[1]-1e-09 or abs(D-E[1])<=1e-09 and J>E[5]:I[N]=R
	J=[]
	for D in seed_solutions:
		if not D:continue
		E=_solution_expected_cost(D,G,O)
		if E<float(_F):J.append((E,D))
	J.sort(key=lambda item:item[0])
	for(c,(T,D))in enumerate(J[:8]):
		d=_result_to_selected(D,R);e=8-c
		for A in d.values():S(tuple(A),source_rank=e)
	U={}
	for B in _canonical_candidates(G):U.setdefault(B[0],[]).append(B)
	for A in U.values():
		if time.monotonic()>P-.18:break
		K={}
		for B in A:
			L=K.get(B[2])
			if L is _A or _group_expected_cost([B],len(B[1]))<_group_expected_cost([L],len(L[1]))-1e-12:K[B[2]]=B
		A=sorted(K.values(),key=lambda c:(_group_expected_cost([c],len(c[1])),-c[4],c[5]))
		if not A:continue
		H=len(A[0][1]);f=8 if H==1 else 9;A=A[:f];g=2 if H==1 else min(3,len(A));M=[]
		for h in range(1,g+1):
			for C in itertools.combinations(A,h):
				E=_group_expected_cost(C,H);V=1e2*H-E
				if V<=1e-09:continue
				M.append((V,E,tuple(C)))
		if not M:continue
		W=[];X=set();i=lambda item:(item[0]/max(1,len(item[2])),item[0],-item[1]),lambda item:(item[0]/max(item[1],1e-09),item[0],-item[1]),lambda item:(item[0],item[0]/max(1,len(item[2])),-item[1]),lambda item:(-item[1],item[0])
		for j in i:
			for(T,T,C)in sorted(M,key=j,reverse=_B)[:3]:
				Y=tuple(A[2]for A in C)
				if Y in X:continue
				X.add(Y);W.append(C)
		for C in W[:7]:S(C,source_rank=0)
	F=list(I.values())
	if not F:return[]
	F=_scarce_prune_elite_columns(F,max_columns=1150);Z=_scarce_beam_pack_columns(F,P,beam_width=5200)
	if not Z:return[]
	N=[]
	for k in Z:A=sorted(F[k][4],key=lambda c:(c[3],-c[4],c[5]));N.append((A[0][0],[A[2]for A in A]))
	N.sort(key=lambda item:R.get((item[0],item[1][0]),('',('',),'',_C,_C,0))[1]);return N
def _scarce_prune_elite_columns(columns,max_columns):
	C=columns;A=max_columns
	if len(C)<=A:return sorted(C,key=_scarce_column_order_key,reverse=_B)
	B=[];E=set();F=lambda c:(c[5],c[0]/max(1,_popcount(c[3])),c[0],_popcount(c[2])),lambda c:(_popcount(c[2]),c[0]/max(1,_popcount(c[3])),c[0]/max(c[1],1e-09)),lambda c:(c[0],c[0]/max(c[1],1e-09),-c[1]),lambda c:(c[0]/max(1,_popcount(c[2])),c[0],-_popcount(c[3]));H=A//len(F)+25
	for I in F:
		for D in sorted(C,key=I,reverse=_B)[:H]:
			G=D[2],D[3]
			if G in E:continue
			E.add(G);B.append(D)
			if len(B)>=A:break
		if len(B)>=A:break
	return sorted(B,key=_scarce_column_order_key,reverse=_B)
def _scarce_column_order_key(column):A,B,C,D,E,F=column;G=_popcount(C);H=_popcount(D);return F,A/max(1,H),G,A/max(B,1e-09),A,-len(E)
def _scarce_beam_pack_columns(columns,deadline,beam_width):
	G=beam_width;A={(0,0):(_C,())};H=_C;F=()
	for(I,R)in enumerate(columns):
		if time.monotonic()>deadline-.05:break
		S,C,J,K,C,C=R;L=[]
		for((M,N),(T,D))in A.items():
			if M&J or N&K:continue
			O=M|J,N|K;E=T+S;B=A.get(O)
			if B is _A or E>B[0]+1e-09:
				L.append((O,(E,D+(I,))))
				if E>H+1e-09:H=E;F=D+(I,)
		for(P,Q)in L:
			B=A.get(P)
			if B is _A or Q[0]>B[0]+1e-09:A[P]=Q
		if len(A)>G*2:A=dict(sorted(A.items(),key=lambda item:(item[1][0],_popcount(item[0][0]),-_popcount(item[0][1])),reverse=_B)[:G])
	if F:return F
	C,(C,D)=max(A.items(),key=lambda item:(item[1][0],_popcount(item[0][0]),-_popcount(item[0][1])));return D
def _repair_worst_window_solution(result,candidates,all_tasks,deadline,top_riders_per_task_key=10,max_k=3,option_limit=70):
	K=deadline;E=all_tasks;B=candidates;A=result;P={(A[0],A[2]):A for A in B};F=_result_to_selected(A,P)
	if not F:return A
	G=[]
	for(Q,C)in F.items():
		if C:D=C[0][1];R=_group_expected_cost(C,len(D));G.append((R/max(1,len(D)),len(D),Q,D,C))
	if not G:return A
	S=sorted(G,reverse=_B);H=A;L=_solution_expected_cost(A,B,E);M=set()
	for(T,U)in((10,(0,3,6)),(14,(0,))):
		for V in U:
			if time.monotonic()>K-.08:return H
			I=_ranked_repair_window(S[V:],T)
			if not I:continue
			N=tuple(sorted(I))
			if N in M:continue
			M.add(N);J=_repair_task_window(F,B,E,I,min(K,time.monotonic()+.22),top_riders_per_task_key=top_riders_per_task_key,max_k=max_k,option_limit=option_limit)
			if not J:continue
			O=_solution_expected_cost(J,B,E)
			if O<L-1e-09:H=J;L=O
	return H
def _ranked_repair_window(ranked_groups,max_window_tasks):
	C=max_window_tasks;A=set()
	for(B,B,B,E,B)in ranked_groups:
		D=A|set(E)
		if len(D)>C:continue
		A=D
		if len(A)>=C:break
	return A
def _repair_task_window(selected,candidates,all_tasks,window_tasks,deadline,top_riders_per_task_key=10,max_k=3,option_limit=70):
	B=window_tasks;del all_tasks;A={}
	for(F,C)in selected.items():
		if not set(C[0][1])&B:A[F]=C
	G={B for A in A.values()for B in A[0][1]};H={B[2]for A in A.values()for B in A};D=[A for A in candidates if A[2]not in H and set(A[1])<=B and not set(A[1])&G]
	if not D:return[]
	E=_search_column_window(D,B,deadline,top_riders_per_task_key=top_riders_per_task_key,max_k=max_k,option_limit=option_limit)
	if not E:return[]
	return _format_selected(A)+E
def _column_alns_repair_solution(result,candidates,all_tasks,deadline,mode,max_window_tasks,top_riders_per_task_key,option_limit,max_k=3):
	L=deadline;G=max_window_tasks;F=all_tasks;E=result;B=candidates;M={(A[0],A[2]):A for A in B};A=_result_to_selected(E,M)
	if not A:return E
	H=E;N=_selected_repair_groups(A)
	if not N:return E
	C=sorted(N,reverse=_B);J=_task_adjacency(B);D=[]
	for S in(0,3,6):D.append(_ranked_repair_window(C[S:],G))
	for(I,I,I,T,I)in C[:6]:D.append(_related_repair_window(T,A,J,G))
	U={B for A in A.values()for B in A[0][1]}
	for V in sorted(set(F)-U):D.append(_uncovered_repair_window(V,A,J,G))
	O=random.Random(20260512+len(F)*17+len(B))
	for I in range(8):
		if not C:break
		W=C[O.randrange(min(len(C),12))];D.append(_random_repair_window(W[3],A,J,G,O))
	P=set()
	for K in D:
		if time.monotonic()>L-.08:break
		if not K:continue
		Q=tuple(sorted(K))
		if Q in P:continue
		P.add(Q);A=_result_to_selected(H,M);R=_repair_task_window(A,B,F,K,min(L,time.monotonic()+.18),top_riders_per_task_key=top_riders_per_task_key,max_k=max_k,option_limit=option_limit)
		if not R:continue
		H=_pick_repair_best(H,R,B,F,mode)
	return H
def _low_worst_window_repair_solution(result,candidates,all_tasks,deadline):
	F=deadline;E=all_tasks;C=candidates;B=result;G={(A[0],A[2]):A for A in C};H=_result_to_selected(B,G)
	if not H:return B
	I=_selected_repair_groups(H)
	if not I:return B
	M=sorted(I,reverse=_B);A=B;J=set()
	for(N,O)in((8,range(0,8)),(10,range(0,8)),(12,range(0,8))):
		for P in O:
			if time.monotonic()>F-.08:return A
			D=_ranked_repair_window(M[P:],N)
			if not D:continue
			K=tuple(sorted(D))
			if K in J:continue
			J.add(K);Q=_result_to_selected(A,G);L=_repair_task_window(Q,C,E,D,min(F,time.monotonic()+.22),top_riders_per_task_key=12,max_k=4,option_limit=90)
			if not L:continue
			A=_pick_low_robust_best([A,L],C,E)
	return A
def _low_deep_window_repair_solution(result,candidates,all_tasks,deadline):
	F=deadline;E=all_tasks;C=candidates;B=result;G={(A[0],A[2]):A for A in C};H=_result_to_selected(B,G)
	if not H:return B
	I=_selected_repair_groups(H)
	if not I:return B
	M=sorted(I,reverse=_B);A=B;J=set()
	for N in(8,10,12):
		for O in range(10):
			if time.monotonic()>F-.08:return A
			D=_ranked_repair_window(M[O:],N)
			if not D:continue
			K=tuple(sorted(D))
			if K in J:continue
			J.add(K);P=_result_to_selected(A,G);L=_repair_task_window(P,C,E,D,min(F,time.monotonic()+.2),top_riders_per_task_key=13,max_k=5,option_limit=110)
			if not L:continue
			A=_pick_low_robust_best([A,L],C,E)
	return A
def _low_late_acceptance_repair_solution(result,candidates,all_tasks,deadline):
	P=deadline;M=result;I=all_tasks;D=candidates;W={(A[0],A[2]):A for A in D};Q=_task_adjacency(D);R=random.Random(70331+len(D));N=M;S=M;E=_solution_expected_cost(N,D,I);T=E;O=[E]*10;B=0
	while time.monotonic()<P-.12:
		J=_result_to_selected(N,W);A=sorted(_selected_repair_groups(J),reverse=_B)
		if not A:break
		F=(8,10,12,14)[B%4];K=B%5
		if K==0:X=B*3%min(14,len(A));C=_ranked_repair_window(A[X:],F)
		elif K in(1,2):G=A[(B*5+K)%min(12,len(A))];C=_related_repair_window(G[3],J,Q,F)
		elif K==3:G=A[R.randrange(min(14,len(A)))];C=_random_repair_window(G[3],J,Q,F,R)
		else:
			G=A[B*2%min(10,len(A))];C=set(G[3])
			for Y in A:
				U=C|set(Y[3])
				if len(U)<=F:C=U
				if len(C)>=F:break
		if not C:B+=1;continue
		L=_repair_task_window(J,D,I,C,min(P,time.monotonic()+.12),top_riders_per_task_key=13,max_k=5,option_limit=110)
		if not L:B+=1;continue
		H=_solution_expected_cost(L,D,I);V=B%len(O)
		if H<T-1e-09:S=L;T=H
		if H<E-1e-09 or H<=O[V]+4.:N=L;E=H
		O[V]=E;B+=1
	return _pick_low_robust_best([M,S],D,I)
def _normal_worst_related_repair_solution(result,candidates,all_tasks,deadline):
	L=deadline;D=all_tasks;B=result;A=candidates;M={(A[0],A[2]):A for A in A};E=_result_to_selected(B,M)
	if not E:return B
	N=_selected_repair_groups(E)
	if not N:return B
	F=sorted(N,reverse=_B);Q=_task_adjacency(A);G=[]
	for H in(8,10,12):
		for R in range(min(8,len(F))):G.append(_ranked_repair_window(F[R:],H))
	for(I,I,I,S,I)in F[:8]:
		for H in(8,10):G.append(_related_repair_window(S,E,Q,H))
	C=B;O=set()
	for J in G:
		if time.monotonic()>L-.08:break
		if not J:continue
		P=tuple(sorted(J))
		if P in O:continue
		O.add(P);T=_result_to_selected(C,M);K=_repair_task_window(T,A,D,J,min(L,time.monotonic()+.16),top_riders_per_task_key=10,max_k=4,option_limit=80)
		if not K:continue
		if _solution_expected_cost(K,A,D)<_solution_expected_cost(C,A,D)-1e-09:C=K
	return C
def _scarce_bundle_insertion_repair_solution(result,candidates,all_tasks,deadline,max_windows,max_window_tasks,use_courier_pressure=_D):
	X=use_courier_pressure;O=all_tasks;I=deadline;H=result;G=max_window_tasks;D=candidates;Y={(A[0],A[2]):A for A in D};B=_result_to_selected(H,Y)
	if not B:return H
	l={B for A in B.values()for B in A[0][1]};P={}
	for(Z,C)in B.items():
		for J in C[0][1]:P[J]=Z
	a={}
	if X:
		for C in B.values():
			Q=set(C[0][1])
			for K in C:a[K[2]]=Q
	V={}
	for K in D:
		if len(K[1])>=2:V.setdefault(K[0],[]).append(K)
	if not V:return H
	R=[]
	for(Z,C)in V.items():
		if time.monotonic()>I-.08:break
		E=C[0][1];F=set(E);S=_best_group_from_pool(sorted(C,key=lambda c:(_group_expected_cost([c],len(E)),-c[4],c[5]))[:9],len(E),min(5,len(C)))
		if not S:continue
		b=_group_expected_cost(S,len(E));c=1e2*len(E)-b
		if c<=1e-09:continue
		m={P[A]for A in E if A in P};n=set();d=_C
		for L in m:
			T=B.get(L)
			if not T:continue
			n.update(T[0][1]);d+=_group_expected_cost(T,len(T[0][1]))
		e=len(F-l);o=b-d-1e2*e;M=set()
		if X:
			for p in S:M.update(a.get(p[2],()))
		R.append((e,-o,c/max(1,len(S)),len(E),F,M))
	if not R:return H
	q=_task_adjacency(D);R.sort(reverse=_B);U=H;f=_solution_expected_cost(U,D,O);g=set();h=0
	for(W,W,W,W,F,M)in R:
		if h>=max_windows or time.monotonic()>I-.06:break
		A=set(F)|set(M)
		for J in sorted(F):
			L=P.get(J)
			if L is not _A and L in B:A.update(B[L][0][1])
		if len(A)<G:
			for J in sorted(F):
				for i in sorted(q.get(J,())):
					Q=_selected_group_tasks_containing(B,i)or{i}
					if len(A|Q)>G:continue
					A|=Q
					if len(A)>=G:break
				if len(A)>=G:break
		if len(A)>G:r=sorted(A,key=lambda task_id:(task_id not in F,task_id not in M,task_id));A=set(r[:G])
		j=tuple(sorted(A))
		if j in g:continue
		g.add(j);h+=1;s=_result_to_selected(U,Y);N=_repair_task_window(s,D,O,A,min(I,time.monotonic()+.12),top_riders_per_task_key=9,max_k=4,option_limit=65)
		if not N:continue
		if time.monotonic()<I-.05:N=_reassign_mixed_solution(N,D,O,min(I,time.monotonic()+.05))
		k=_solution_expected_cost(N,D,O)
		if k<f-1e-09:U=N;f=k
	return U
def _pairwise_column_exchange_solution(result,candidates,all_tasks,deadline,top_riders_per_task_key,max_k,option_limit,max_window_tasks,max_pairs):
	M=max_window_tasks;H=deadline;G=all_tasks;F=result;C=candidates;N={(A[0],A[2]):A for A in C};O=_result_to_selected(F,N)
	if not O:return F
	D=[]
	for(Y,I)in O.items():
		if not I:continue
		P=set(I[0][1]);Z=_group_expected_cost(I,len(I[0][1]));D.append((Z/max(1,len(P)),Y,P))
	if len(D)<2:return F
	D.sort(reverse=_B);L=[]
	for(J,A)in enumerate(D[:10]):
		for B in D[J+1:J+12]:
			if len(A[2]|B[2])<=M:L.append((A,B))
	for Q in C:
		if len(Q[1])<2:continue
		a=set(Q[1]);R=[A for A in D[:14]if A[2]&a]
		for(J,A)in enumerate(R):
			for B in R[J+1:]:
				if len(A[2]|B[2])<=M:L.append((A,B))
	K=F;S=_solution_expected_cost(K,C,G);T=set();U=0
	for(A,B)in L:
		if U>=max_pairs or time.monotonic()>H-.04:break
		V=A[2]|B[2];W=tuple(sorted(V))
		if W in T:continue
		T.add(W);U+=1;b=_result_to_selected(K,N);E=_repair_task_window(b,C,G,V,min(H,time.monotonic()+.1),top_riders_per_task_key=top_riders_per_task_key,max_k=max_k,option_limit=option_limit)
		if not E:continue
		if time.monotonic()<H-.05:E=_reassign_mixed_solution(E,C,G,min(H,time.monotonic()+.06))
		X=_solution_expected_cost(E,C,G)
		if X<S-1e-09:K=E;S=X
	return K
def _triple_column_exchange_solution(result,candidates,all_tasks,deadline,top_riders_per_task_key,max_k,option_limit,max_window_tasks,max_triples):
	L=max_window_tasks;H=deadline;G=all_tasks;F=result;B=candidates;M={(A[0],A[2]):A for A in B};N=_result_to_selected(F,M)
	if not N:return F
	D=[]
	for(V,I)in N.items():
		if not I:continue
		O=set(I[0][1]);W=_group_expected_cost(I,len(I[0][1]));D.append((W/max(1,len(O)),V,O))
	if len(D)<3:return F
	D.sort(reverse=_B);K=[]
	for A in itertools.combinations(D[:9],3):
		C=set().union(*(A[2]for A in A))
		if len(C)<=L:K.append(A)
	for P in B:
		if len(P[1])<2:continue
		X=set(P[1]);Y=[A for A in D[:12]if A[2]&X]
		for A in itertools.combinations(Y[:6],3):
			C=set().union(*(A[2]for A in A))
			if len(C)<=L:K.append(A)
	J=F;Q=_solution_expected_cost(J,B,G);R=set();S=0
	for A in K:
		if S>=max_triples or time.monotonic()>H-.04:break
		C=set().union(*(A[2]for A in A));T=tuple(sorted(C))
		if T in R:continue
		R.add(T);S+=1;Z=_result_to_selected(J,M);E=_repair_task_window(Z,B,G,C,min(H,time.monotonic()+.11),top_riders_per_task_key=top_riders_per_task_key,max_k=max_k,option_limit=option_limit)
		if not E:continue
		if time.monotonic()<H-.05:E=_reassign_mixed_solution(E,B,G,min(H,time.monotonic()+.06))
		U=_solution_expected_cost(E,B,G)
		if U<Q-1e-09:J=E;Q=U
	return J
def _scarce_eject_extra_to_uncovered(result,candidates,all_tasks,deadline):
	I=deadline;H=candidates;G=result;R={(A[0],A[2]):A for A in H};B=_result_to_selected(G,R)
	if not B:return G
	J={}
	for K in H:J.setdefault(K[2],[]).append(K)
	while time.monotonic()<I-.04:
		S={B for A in B.values()for B in A[0][1]};L=set(all_tasks)-S
		if not L:break
		F=_A;M=_C;T=set(B)
		for(E,C)in list(B.items()):
			if time.monotonic()>I-.04:break
			if len(C)<=1:continue
			N=len(C[0][1]);U=_group_expected_cost(C,N)
			for D in C:
				O=[A for A in C if A!=D]
				if not O:continue
				V=_group_expected_cost(O,N)-U
				for A in J.get(D[2],()):
					if A[0]in T:continue
					P=set(A[1])
					if not P or not P<=L:continue
					W=_group_expected_cost([A],len(A[1]));Q=V+W-1e2*len(A[1])
					if Q<M-1e-09:M=Q;F=E,D,A
		if F is _A:break
		E,D,A=F;B[E]=[A for A in B[E]if A!=D];B[A[0]]=[A]
	return _format_selected(B)
def _shift_couriers_between_groups(result,candidates,all_tasks,deadline,max_moves):
	M=deadline;L=all_tasks;H=candidates;G=result;V={(A[0],A[2]):A for A in H};A=_result_to_selected(G,V)
	if not A:return G
	N={}
	for O in H:N.setdefault(O[2],[]).append(O)
	P=0
	while P<max_moves and time.monotonic()<M-.04:
		J=_A;Q=_C
		for(B,E)in list(A.items()):
			if time.monotonic()>M-.04:break
			if not E:continue
			K=len(E[0][1]);W=_group_expected_cost(E,K)
			for C in E:
				R=[A for A in E if A!=C];X=_group_expected_cost(R,K)if R else 1e2*K;Y=X-W
				for F in N.get(C[2],()):
					D=F[0]
					if D==B or D not in A:continue
					I=A[D]
					if any(A[2]==C[2]for A in I):continue
					S=len(I[0][1]);Z=_group_expected_cost(I,S);a=_group_expected_cost(I,S,extra=F);T=Y+a-Z
					if T<Q-1e-09:Q=T;J=B,C,D,F
		if J is _A:break
		B,C,D,F=J;A[B]=[A for A in A[B]if A!=C]
		if not A[B]:del A[B]
		A[D].append(F);P+=1
	U=_format_selected(A)
	if _solution_expected_cost(U,H,L)<_solution_expected_cost(G,H,L)-1e-09:return U
	return G
def _scarce_polish_candidate(result,candidates,all_tasks,deadline):
	D=deadline;C=all_tasks;B=candidates;A=result
	if time.monotonic()<D-.18:A=_local_improve_mixed_solution(A,B,C,D,include_pair_rewire=_B)
	if time.monotonic()<D-.3:A=_reassign_mixed_solution(A,B,C,D);A=_drop_unprofitable_groups(A,B,C)
	if time.monotonic()<D-.18:A=_local_improve_mixed_solution(A,B,C,D,include_pair_rewire=_B);A=_drop_unprofitable_groups(A,B,C)
	if time.monotonic()<D-.85:A=_column_alns_repair_solution(A,B,C,min(D,time.monotonic()+.75),mode=_J,max_window_tasks=12,top_riders_per_task_key=8,option_limit=55,max_k=4);A=_drop_unprofitable_groups(A,B,C)
	if time.monotonic()<D-.45:
		F=_scarce_bundle_insertion_repair_solution(A,B,C,min(D,time.monotonic()+.34),max_windows=34,max_window_tasks=14)
		if _solution_expected_cost(F,B,C)<_solution_expected_cost(A,B,C)-1e-09:A=_drop_unprofitable_groups(F,B,C)
	if time.monotonic()<D-.35:
		E=_pairwise_column_exchange_solution(A,B,C,min(D,time.monotonic()+.3),top_riders_per_task_key=8,max_k=4,option_limit=55,max_window_tasks=10,max_pairs=28)
		if _solution_expected_cost(E,B,C)<_solution_expected_cost(A,B,C)-1e-09:A=_drop_unprofitable_groups(E,B,C)
	if time.monotonic()<D-.32:
		E=_triple_column_exchange_solution(A,B,C,min(D,time.monotonic()+.27),top_riders_per_task_key=8,max_k=4,option_limit=60,max_window_tasks=12,max_triples=16)
		if _solution_expected_cost(E,B,C)<_solution_expected_cost(A,B,C)-1e-09:A=_drop_unprofitable_groups(E,B,C)
	if time.monotonic()<D-.24:
		G=_scarce_eject_extra_to_uncovered(A,B,C,min(D,time.monotonic()+.18))
		if _solution_expected_cost(G,B,C)<_solution_expected_cost(A,B,C)-1e-09:A=_drop_unprofitable_groups(G,B,C)
	if time.monotonic()<D-.22:
		H=_shift_couriers_between_groups(A,B,C,min(D,time.monotonic()+.18),max_moves=18)
		if _solution_expected_cost(H,B,C)<_solution_expected_cost(A,B,C)-1e-09:A=_drop_unprofitable_groups(H,B,C)
	if time.monotonic()<D-.22:
		I=_reassign_mixed_solution(A,B,C,min(D,time.monotonic()+.35))
		if _solution_expected_cost(I,B,C)<_solution_expected_cost(A,B,C)-1e-09:A=I
	return A
def _selected_repair_groups(selected):
	C=[]
	for(D,A)in selected.items():
		if A:B=A[0][1];E=_group_expected_cost(A,len(B));C.append((E/max(1,len(B)),len(B),D,B,A))
	return C
def _task_adjacency(candidates):
	C={}
	for(A,B,A,A,A,A)in candidates:
		if len(B)<2:continue
		for D in B:
			F=C.setdefault(D,set())
			for E in B:
				if E!=D:F.add(E)
	return C
def _related_repair_window(seed_tasks,selected,adjacency,max_window_tasks):
	F=seed_tasks;D=max_window_tasks;A=set(F);E=list(F)
	while E and len(A)<D:
		G=E.pop(0)
		for C in sorted(adjacency.get(G,())):
			if C in A:continue
			B=_selected_group_tasks_containing(selected,C)
			if not B:B={C}
			if len(A|B)>D:continue
			A|=B;E.extend(sorted(B-{C}))
			if len(A)>=D:break
	return A
def _uncovered_repair_window(task_id,selected,adjacency,max_window_tasks):
	H=selected;G=task_id;C=max_window_tasks;A={G};J=sorted(adjacency.get(G,()));E=[]
	for F in J:B=_selected_group_tasks_containing(H,F)or{F};E.append((len(B),F,B))
	E.sort()
	for(D,D,B)in E:
		if len(A|B)>C:continue
		A|=B
		if len(A)>=C:break
	if len(A)<C:
		I=_selected_repair_groups(H);I.sort(reverse=_B)
		for(D,D,D,K,D)in I:
			B=set(K)
			if A&B:continue
			if len(A|B)>C:continue
			A|=B
			if len(A)>=C:break
	return A
def _random_repair_window(seed_tasks,selected,adjacency,max_window_tasks,rng):
	B=max_window_tasks;A=set(seed_tasks);D=0
	while len(A)<B and D<B*3:
		D+=1;G=rng.choice(tuple(A));C=sorted(adjacency.get(G,()))
		if not C:break
		E=C[rng.randrange(len(C))];F=_selected_group_tasks_containing(selected,E)or{E}
		if len(A|F)<=B:A|=F
	return A
def _selected_group_tasks_containing(selected,task_id):
	for A in selected.values():
		if A and task_id in A[0][1]:return set(A[0][1])
	return set()
def _pick_repair_best(best,candidate,candidates,all_tasks,mode):
	D=all_tasks;C=candidates;B=candidate;A=best
	if mode==_J:return _pick_scarce_best([A,B],C,D)
	if mode=='low':return _pick_low_robust_best([A,B],C,D)
	if _solution_expected_cost(B,C,D)<_solution_expected_cost(A,C,D)-1e-09:return B
	return A
def _solve_disjoint_then_multidispatch(candidates,all_tasks,mode,deadline=_A):
	K=deadline;J=candidates;G={};E=set();F=set()
	while _B:
		if K is not _A and time.monotonic()>K-.25:break
		A=_A;L=_A
		for M in J:
			T,C,P,D,N,U=M
			if P in F:continue
			if any(A in E for A in C):continue
			Q=1e2*len(C);R=_group_expected_cost([M],len(C));B=Q-R
			if B<=1e-12:continue
			if mode==_G:H=B,len(C),B/max(D,1e-09),N,-D
			elif mode==_H:H=len(C),B/max(D,1e-09),B,N,-D
			else:H=B/max(D,1e-09),len(C),B,N,-D
			if L is _A or H>L:L=H;A=M
		if A is _A:break
		G[A[0]]=[A];F.add(A[2])
		for I in A[1]:E.add(I)
	for I in sorted(all_tasks):
		if I in E:continue
		O=[A for A in J if I in A[1]and A[2]not in F and not any(A in E for A in A[1])]
		if not O:continue
		A=min(O,key=lambda c:_group_expected_cost([c],len(c[1])));G[A[0]]=[A];F.add(A[2])
		for S in A[1]:E.add(S)
	_add_extra_dispatches(G,J,F,K);return _format_selected(G)
def _add_extra_dispatches(selected,candidates,used_couriers,deadline=_A):
	H=deadline;G=used_couriers;F=selected;I={}
	for A in candidates:I.setdefault(A[0],[]).append(A)
	C=_B
	while C:
		if H is not _A and time.monotonic()>H-.2:break
		C=_D;D=_A;J=_C;N=_C
		for(B,E)in F.items():
			K=len(E[0][1]);O=_group_expected_cost(E,K)
			for A in I.get(B,[]):
				if A[2]in G:continue
				L=_group_expected_cost(E,K,extra=A);M=L-O
				if M<J-1e-12:J=M;N=L;D=B,A
		if D is not _A:B,A=D;F[B].append(A);G.add(A[2]);C=_B
def _solve_pair_potential_matching(candidates,all_tasks,deadline,lookahead=4,flexible_initial=_D):
	M=deadline;L=all_tasks;K=candidates;N={};O=[]
	for G in K:
		N.setdefault(G[0],[]).append(G)
		if len(G[1])==1:O.append(G)
	H=[]
	for(J,P)in N.items():
		if time.monotonic()>M-.45:break
		A=P[0][1]
		if len(A)<2:continue
		V=max(lookahead,min(8,len(A)+2));E,Q=_best_group_rows(P,len(A),V)
		if not E:continue
		R=1e2*len(A)-Q
		if R<=1e-12:continue
		H.append((R,-Q,J,A,E))
	if not H:return[]
	H.sort(reverse=_B);I={};F=set();B=set()
	for(W,W,J,A,E)in H:
		if any(A in F for A in A):continue
		if flexible_initial:
			C=_A
			for S in E:
				if S[2]not in B:C=S;break
			if C is _A:continue
		else:
			C=E[0]
			if C[2]in B:continue
		I[J]=[C];B.add(C[2])
		for D in A:F.add(D)
		if len(F)>=len(L):break
	for D in sorted(L):
		if D in F:continue
		T=[A for A in O if A[1][0]==D and A[2]not in B]
		if not T:continue
		U=min(T,key=lambda c:_group_expected_cost([c],1));I[D]=[U];B.add(U[2]);F.add(D)
	_add_extra_dispatches(I,K,B,M);return _format_selected(I)
def _best_group_rows(rows,task_count,limit):
	E=task_count;A=[];F=set();C=1e2*E
	while len(A)<limit:
		B=_A;G=_C;H=_C
		for D in rows:
			if D[2]in F:continue
			I=_group_expected_cost(A,E,extra=D);J=I-C
			if J<G-1e-12:B=D;G=J;H=I
		if B is _A:break
		A.append(B);F.add(B[2]);C=H
	return A,C
def _format_selected(selected):
	A=selected;B=[]
	for C in sorted(A,key=lambda k:A[k][0][1]):D=sorted(A[C],key=lambda c:(c[3],-c[4],c[5]));B.append((C,[A[2]for A in D]))
	return B
def _result_to_selected(result,row_map):
	B={}
	for(C,E)in result:
		A=[]
		for F in E:
			D=row_map.get((C,F))
			if D is not _A:A.append(D)
		if A:B[C]=A
	return B
def _destroy_repair_single_solution(result,singles,all_tasks,deadline):
	J=singles;I=result;A=all_tasks;R={(A[0],A[2]):A for A in J};K=_result_to_selected(I,R)
	if not K:return I
	B=K;E=random.Random(123);F=0;S=900 if len(A)>=35 else 350;T=100 if len(A)>=35 else 60;G=0
	while F<S and G<T and time.monotonic()<deadline-.05:
		F+=1;C=[]
		for(L,D)in B.items():
			U=_group_expected_cost(D,1)
			for H in D:M=[A for A in D if A!=H];V=_group_expected_cost(M,1)if M else 1e2;C.append((V-U,H[5],H))
		if not C:break
		C.sort(key=lambda x:(x[0],x[1]));N=[B for(A,A,B)in C[:min(40,len(C))]];W=E.choice([2,3,4,5,6,8]);X=set(E.sample(N,min(W,len(N))));O={}
		for(L,D)in B.items():
			P=[A for A in D if A not in X]
			if P:O[L]=P
		Y=E.choice([_C,.1,.2,.35]);Q=_greedy_repair_single(O,J,A,random.Random(F),Y)
		if _selected_cost(Q,A)<_selected_cost(B,A)-1e-09:B=Q;G=0
		else:G+=1
	return _format_selected(B)
def _greedy_repair_single(selected,singles,all_tasks,rng,noise):
	E=noise;A=selected;A={A:list(B)for(A,B)in A.items()};I={B[2]for A in A.values()for B in A};F={A:_group_expected_cost(B,1)for(A,B)in A.items()}
	for G in all_tasks:
		if G not in A:A[G]=[];F[G]=1e2
	while _B:
		C=[]
		for B in singles:
			J,R,M,N,O,P=B
			if M in I:continue
			Q=F.get(J,1e2);D=_group_expected_cost(A.get(J,[]),1,extra=B);H=Q-D
			if H<=1e-12:continue
			K=H
			if E:K*=rng.uniform(_E-E,_E+E)
			C.append((K,H,O,-N,-P,B,D))
		if not C:break
		C.sort(reverse=_B);L=C[rng.randrange(min(3,len(C)))];B=L[5];D=L[6];A.setdefault(B[0],[]).append(B);F[B[0]]=D;I.add(B[2])
	return{B:A for(B,A)in A.items()if A}
def _random_single_start_solution(singles,all_tasks,deadline):
	E=deadline;C=all_tasks;B=singles
	if time.monotonic()>E-1.8:return[]
	D=min(E,time.monotonic()+1.8);F=_greedy_repair_single({},B,C,random.Random(18),.5);A=_format_selected(F);A=_reassign_single_solution(A,B,C,D);A=_rebalance_single_solution(A,B,C,D);A=_reassign_single_solution(A,B,C,D);return A
def _selected_cost(selected,all_tasks):
	C=0;A=_C
	for B in selected.values():
		if not B:continue
		D=len(B[0][1]);C+=D;A+=_group_expected_cost(B,D)
	A+=1e2*(len(all_tasks)-C);return A
def _local_improve_mixed_solution(result,candidates,all_tasks,deadline,include_pair_rewire=_D):
	K=candidates;J=result;D=deadline;A=all_tasks;P={(A[0],A[2]):A for A in K};B=_result_to_selected(J,P)
	if not B:return J
	L={};M={};H={}
	for E in K:
		L.setdefault(E[0],[]).append(E)
		if len(E[1])==1:M.setdefault(E[1][0],[]).append(E)
		elif len(E[1])>=2:H.setdefault(tuple(sorted(E[1])),[]).append(E)
	Q=any(len(A)>2 for A in H);F=_selected_cost(B,A);N=0
	while N<2 and time.monotonic()<D-.12:
		N+=1;I=_D;G=_improve_same_key_groups(B,L,A,D)
		if G:
			C=_selected_cost(B,A)
			if C<F-1e-09:F=C;I=_B
		if time.monotonic()<D-.12:
			G=_improve_bundle_splits(B,M,A,D)
			if G:
				C=_selected_cost(B,A)
				if C<F-1e-09:F=C;I=_B
		if time.monotonic()<D-.12:
			if Q:G=_improve_covered_bundle_merges(B,H,A,D)
			else:G=_improve_single_pair_merges(B,H,A,D)
			if G:
				C=_selected_cost(B,A)
				if C<F-1e-09:F=C;I=_B
		if include_pair_rewire and time.monotonic()<D-.12:
			G=_improve_pair_rewires(B,H,A,D)
			if G:
				C=_selected_cost(B,A)
				if C<F-1e-09:F=C;I=_B
		if not I:break
	O=_format_selected(B)
	if _solution_expected_cost(O,K,A)<_solution_expected_cost(J,K,A)-1e-09:return O
	return J
def _improve_same_key_groups(selected,by_key,all_tasks,deadline):
	B=selected;F=_D
	for C in list(B):
		if time.monotonic()>deadline-.12:break
		A=B.get(C)
		if not A:continue
		G=_selected_couriers_except(B,{C});E=[A for A in by_key.get(C,[])if A[2]not in G]
		if not E:continue
		H=min(len(E),max(1,len(A)+2),7);D=_best_group_from_pool(E,len(A[0][1]),H)
		if not D:continue
		I=_group_expected_cost(A,len(A[0][1]));J=_group_expected_cost(D,len(D[0][1]))
		if J<I-1e-09:B[C]=D;F=_B
	return F
def _improve_bundle_splits(selected,singles_by_task,all_tasks,deadline):
	A=selected;F=_D
	for D in list(A):
		if time.monotonic()>deadline-.12:break
		B=A.get(D)
		if not B or len(B[0][1])<2:continue
		C=B[0][1]
		if any(B in A for B in C):continue
		G=_selected_couriers_except(A,{D});E=_best_multi_split_groups(C,singles_by_task,G,max_rows=min(len(B)+len(C),max(7,len(C)*2)))
		if E is _A:continue
		H=_group_expected_cost(B,len(C));I=sum(_group_expected_cost(A,1)for A in E.values())
		if I<H-1e-09:
			del A[D]
			for(J,K)in E.items():A[J]=K
			F=_B
	return F
def _improve_single_pair_merges(selected,bundles_by_tasks,all_tasks,deadline):
	H=deadline;A=selected;I=_D;J=[B for(B,A)in A.items()if A and len(A[0][1])==1]
	for(L,B)in enumerate(J):
		if time.monotonic()>H-.12:break
		if B not in A:continue
		for C in J[L+1:]:
			if time.monotonic()>H-.12:break
			if C not in A:continue
			E=A[B];F=A[C];M=tuple(sorted((E[0][1][0],F[0][1][0])));K=bundles_by_tasks.get(M)
			if not K:continue
			N=_selected_couriers_except(A,{B,C});G=[A for A in K if A[2]not in N]
			if not G:continue
			O=min(len(G),len(E)+len(F)+2,7);D=_best_group_from_pool(G,2,O)
			if not D:continue
			P=_group_expected_cost(E,1)+_group_expected_cost(F,1);Q=_group_expected_cost(D,2)
			if Q<P-1e-09:del A[B];del A[C];A[D[0][0]]=D;I=_B;break
	return I
def _improve_covered_bundle_merges(selected,bundles_by_tasks,all_tasks,deadline):
	J=deadline;D=selected;K=_D;S=sorted(bundles_by_tasks.items(),key=lambda item:(-len(item[0]),item[0]))
	while time.monotonic()<J-.12:
		G=_A;L=_C;M={}
		for(T,A)in D.items():
			if not A:continue
			for H in A[0][1]:M[H]=T
		for(E,U)in S:
			if time.monotonic()>J-.12:break
			if len(E)<2:continue
			B=set();N=_D
			for H in E:
				C=M.get(H)
				if C is _A:N=_B;break
				B.add(C)
			if N or len(B)==1:continue
			O=set();P=_C;Q=0
			for C in B:
				A=D.get(C)
				if not A:continue
				O.update(A[0][1]);P+=_group_expected_cost(A,len(A[0][1]));Q+=len(A)
			if O!=set(E):continue
			V=_selected_couriers_except(D,B);I=[A for A in U if A[2]not in V]
			if not I:continue
			W=min(len(I),max(1,Q+2),max(7,len(E)+3));F=_best_group_from_pool(I,len(E),W)
			if not F:continue
			X=_group_expected_cost(F,len(E));R=X-P
			if R<L-1e-09:L=R;G=B,F
		if G is _A:break
		B,F=G
		for C in B:
			if C in D:del D[C]
		D[F[0][0]]=F;K=_B
	return K
def _improve_pair_rewires(selected,bundles_by_tasks,all_tasks,deadline):
	O=bundles_by_tasks;G=deadline;A=selected;F=[B for(B,A)in A.items()if A and len(A[0][1])==2]
	if len(F)<2:return _D
	P=_D
	while time.monotonic()<G-.12:
		H=_A;Q=_C;F=[B for(B,A)in A.items()if A and len(A[0][1])==2]
		for(V,B)in enumerate(F):
			if time.monotonic()>G-.12:break
			if B not in A:continue
			I=A[B];J,K=I[0][1]
			for C in F[V+1:]:
				if time.monotonic()>G-.12:break
				if C not in A:continue
				L=A[C];M,N=L[0][1]
				if len({J,K,M,N})<4:continue
				W=_group_expected_cost(I,2)+_group_expected_cost(L,2);R=_selected_couriers_except(A,{B,C})
				for(X,Y)in(((J,M),(K,N)),((J,N),(K,M))):
					Z=tuple(sorted(X));a=tuple(sorted(Y));S=[A for A in O.get(Z,[])if A[2]not in R]
					if not S:continue
					D=_best_group_from_pool(S,2,min(len(I)+1,6))
					if not D:continue
					b={A[2]for A in D};T=[A for A in O.get(a,[])if A[2]not in R and A[2]not in b]
					if not T:continue
					E=_best_group_from_pool(T,2,min(len(L)+1,6))
					if not E:continue
					c=_group_expected_cost(D,2)+_group_expected_cost(E,2);U=c-W
					if U<Q-1e-09:Q=U;H=B,C,D,E
		if H is _A:break
		B,C,D,E=H
		if B in A:del A[B]
		if C in A:del A[C]
		A[D[0][0]]=D;A[E[0][0]]=E;P=_B
	return P
def _selected_couriers_except(selected,excluded_keys):return{C[2]for(A,B)in selected.items()if A not in excluded_keys for C in B}
def _best_group_from_pool(pool,task_count,limit):
	D=task_count;A=[];E=set();F=1e2*D
	while len(A)<limit:
		B=_A;G=_C;H=_C
		for C in pool:
			if C[2]in E:continue
			I=_group_expected_cost(A,D,extra=C);J=I-F
			if J<H-1e-12:B=C;G=I;H=J
		if B is _A:break
		A.append(B);E.add(B[2]);F=G
	return A
def _best_multi_split_groups(task_ids,singles_by_task,outside_couriers,max_rows):
	C=task_ids;A={A:[]for A in C};G={A:1e2 for A in C};H=set(outside_couriers);I=[]
	for B in C:I.extend(singles_by_task.get(B,[]))
	while sum(len(A)for A in A.values())<max_rows:
		D=_A;F=_A;J=_C;K=_C
		for E in I:
			B=E[1][0]
			if E[2]in H:continue
			L=_group_expected_cost(A[B],1,extra=E);M=L-G[B]
			if M<K-1e-12:D=E;F=B;J=L;K=M
		if D is _A:break
		A[F].append(D);G[F]=J;H.add(D[2])
	if any(not A[B]for B in C):return
	return A
class _MinCostFlow:
	def __init__(A,n):A.graph=[[]for A in range(n)]
	def add_edge(A,start,end,capacity,cost):C=end;B=start;D=[C,capacity,cost,len(A.graph[C])];E=[B,0,-cost,len(A.graph[B])];A.graph[B].append(D);A.graph[C].append(E)
	def min_cost_flow(C,source,sink,amount):
		D=source;J=0;E=len(C.graph)
		while J<amount:
			F=[float(_F)]*E;G=[_D]*E;H=[-1]*E;M=[-1]*E;F[D]=_C;K=[D];G[D]=_B;L=0
			while L<len(K):
				A=K[L];L+=1;G[A]=_D
				for(O,I)in enumerate(C.graph[A]):
					B,P,Q,S=I
					if P<=0:continue
					N=F[A]+Q
					if N+1e-12<F[B]:
						F[B]=N;H[B]=A;M[B]=O
						if not G[B]:K.append(B);G[B]=_B
			if H[sink]==-1:break
			A=sink
			while A!=D:I=C.graph[H[A]][M[A]];R=C.graph[A][I[3]];I[1]-=1;R[1]+=1;A=H[A]
			J+=1
		return J
def _reassign_single_solution(result,singles,all_tasks,deadline):
	C=all_tasks;B=result;D={(A[0],A[2]):A for A in singles};A=_result_to_selected(B,D)
	if not A:return B
	E=_selected_cost(A,C)
	for H in range(3):
		if time.monotonic()>deadline-.15:break
		F=_reassign_selected_once(A,D);G=_selected_cost(F,C)
		if G<E-1e-09:A=F;E=G
		else:break
	return _format_selected(A)
def _rebalance_single_solution(result,singles,all_tasks,deadline):
	K=all_tasks;J=singles;I=result;O={(A[0],A[2]):A for A in J};P={(A[1][0],A[2]):A for A in J};A=_result_to_selected(I,O)
	if not A:return I
	for Q in K:A.setdefault(Q,[])
	L=0;R=min(12,len(K))
	while L<R and time.monotonic()<deadline-.2:
		G=_A;M=_C
		for(B,F)in A.items():
			if len(F)<=1:continue
			S=_group_expected_cost(F,1)
			for C in F:
				T=C[2];U=[A for A in F if A!=C];V=_group_expected_cost(U,1)-S
				for(D,H)in A.items():
					if D==B:continue
					E=P.get((D,T))
					if E is _A:continue
					W=_group_expected_cost(H,1)if H else 1e2;X=_group_expected_cost(H,1,extra=E);N=V+X-W
					if N<M-1e-12:M=N;G=B,D,C,E
		if G is _A:break
		B,D,C,E=G;A[B]=[A for A in A[B]if A!=C];A[D].append(E);L+=1
	return _format_selected({B:A for(B,A)in A.items()if A})
def _reassign_mixed_solution(result,candidates,all_tasks,deadline):
	C=all_tasks;B=result;D={(A[0],A[2]):A for A in candidates};A=_result_to_selected(B,D)
	if not A:return B
	E=_selected_cost(A,C)
	for H in range(2):
		if time.monotonic()>deadline-.22:break
		F=_reassign_mixed_selected_once(A,D);G=_selected_cost(F,C)
		if G<E-1e-09:A=F;E=G
		else:break
	return _format_selected(A)
def _reassign_mixed_selected_once(selected,row_map):
	A=selected;F=sorted({B[2]for A in A.values()for B in A});B=[]
	for C in sorted(A):
		I=A[C];J=len(I[0][1])
		for(U,Y)in enumerate(I):G=[B for(A,B)in enumerate(I)if A!=U];B.append((C,J,G))
	if not F or not B:return A
	S=0;K=1;L=K+len(F);M=L+len(B);D=_MinCostFlow(M+1);T={}
	for(N,O)in enumerate(F):D.add_edge(S,K+N,1,_C)
	for H in range(len(B)):D.add_edge(L+H,M,1,_C)
	for(N,O)in enumerate(F):
		P=K+N
		for(H,(C,J,G))in enumerate(B):
			if any(A[2]==O for A in G):continue
			E=row_map.get((C,O))
			if E is _A:continue
			V=_group_expected_cost(G+[E],J);Q=len(D.graph[P]);D.add_edge(P,L+H,1,V);T[P,Q]=H,E
	if D.min_cost_flow(S,M,len(B))<len(B):return A
	R={A:[]for A in A}
	for((W,Q),(X,E))in T.items():
		if D.graph[W][Q][1]==0:C=B[X][0];R[C].append(E)
	if any(len(R.get(A,[]))!=len(B)for(A,B)in A.items()):return A
	return R
def _reassign_selected_once(selected,row_map):
	A=selected;F=sorted({B[2]for A in A.values()for B in A});B=[]
	for C in sorted(A):
		Q=A[C]
		for(T,X)in enumerate(Q):G=[B for(A,B)in enumerate(Q)if A!=T];B.append((C,G))
	if not F or not B:return A
	R=0;I=1;J=I+len(F);K=J+len(B);D=_MinCostFlow(K+1);S={}
	for(L,M)in enumerate(F):D.add_edge(R,I+L,1,_C)
	for H in range(len(B)):D.add_edge(J+H,K,1,_C)
	for(L,M)in enumerate(F):
		N=I+L
		for(H,(C,G))in enumerate(B):
			if any(A[2]==M for A in G):continue
			E=row_map.get((C,M))
			if E is _A:continue
			U=_group_expected_cost(G+[E],1);O=len(D.graph[N]);D.add_edge(N,J+H,1,U);S[N,O]=H,E
	if D.min_cost_flow(R,K,len(B))<len(B):return A
	P={A:[]for A in A}
	for((V,O),(W,E))in S.items():
		if D.graph[V][O][1]==0:C=B[W][0];P[C].append(E)
	if any(len(P.get(A,[]))!=len(B)for(A,B)in A.items()):return A
	return P
def _solve_scarce_bundle_mcf_enum(candidates,all_tasks,deadline):
	N=deadline;H=all_tasks;G=candidates;I=sorted(H);R={B:A for(A,B)in enumerate(I)};J={};C=[]
	for D in _canonical_candidates(G):
		b,E,K,c,d,e=D
		if len(E)==1:J.setdefault(E[0],[]).append(D);continue
		A=0
		for S in E:
			if S not in R:A=0;break
			A|=1<<R[S]
		if not A:continue
		F=_group_expected_cost([D],len(E));T=1e2*len(E)-F
		if T<=1e-09:continue
		C.append((T,F,A,K,D))
	if not C:return[]
	C.sort(key=lambda item:(_popcount(item[2]),item[0]/max(item[1],1e-09),item[0],-item[1],-item[4][5]),reverse=_B);C=C[:120];O=[(0,frozenset(),())];U=list(O);L=_complete_scarce_bundles_with_mcf((),J,I);V=_solution_expected_cost(L,G,H)if L else float(_F);a=min(len({A[2]for A in G}),len(H)//2+2)
	for W in range(a):
		if time.monotonic()>N-.28:break
		B=[]
		for(A,M,P)in O:
			for(W,W,X,K,D)in C:
				if A&X or K in M:continue
				B.append((A|X,M|{K},P+(D,)))
				if len(B)>=1800:break
			if len(B)>=1800 or time.monotonic()>N-.28:break
		if not B:break
		B=_prune_scarce_bundle_states(B,I,J,max_states=180);U.extend(B);O=B
	Y=set()
	for(A,M,P)in U:
		if time.monotonic()>N-.05:break
		Z=A,tuple(sorted(M))
		if Z in Y:continue
		Y.add(Z);Q=_complete_scarce_bundles_with_mcf(P,J,I)
		if not Q:continue
		F=_solution_expected_cost(Q,G,H)
		if F<V-1e-09:L=Q;V=F
	return L
def _solve_scarce_bundle_group_mcf_enum(candidates,all_tasks,deadline):
	M=candidates;H=deadline;G=all_tasks;I=sorted(G);U={B:A for(A,B)in enumerate(I)};J={};V={}
	for E in _canonical_candidates(M):
		if len(E[1])==1:J.setdefault(E[1][0],[]).append(E)
		else:V.setdefault(E[0],[]).append(E)
	D=[]
	for A in V.values():
		if time.monotonic()>H-.2:break
		C=0;W=_B
		for X in A[0][1]:
			if X not in U:W=_D;break
			C|=1<<U[X]
		if not W:continue
		N=len(A[0][1]);A=sorted(A,key=lambda c:(_group_expected_cost([c],N),-c[4],c[5]))[:7];O=[]
		for g in range(1,min(3,len(A))+1):
			for P in itertools.combinations(A,g):
				Q=tuple(sorted(A[2]for A in P))
				if len(Q)!=len(set(Q)):continue
				F=_group_expected_cost(P,N);Y=1e2*N-F
				if Y<=1e-09:continue
				O.append((Y,F,C,frozenset(Q),tuple(P)))
		O.sort(key=lambda item:(item[0]/max(item[1],1e-09),item[0],-item[1]),reverse=_B);D.extend(O[:3])
	if not D:return[]
	D.sort(key=lambda item:(_popcount(item[2]),item[0]/max(1,len(item[3])),item[0]/max(item[1],1e-09),item[0]),reverse=_B);D=D[:90];R=[(0,frozenset(),())];Z=list(R);K=_complete_scarce_bundle_groups_with_mcf((),J,I);a=_solution_expected_cost(K,M,G)if K else float(_F);h=min(len(G)//2+2,18)
	for b in range(h):
		if time.monotonic()>H-.22:break
		B=[]
		for(C,L,S)in R:
			for(b,b,c,d,A)in D:
				if C&c or L&d:continue
				B.append((C|c,L|d,S+(A,)))
				if len(B)>=1300:break
			if len(B)>=1300 or time.monotonic()>H-.22:break
		if not B:break
		B=_prune_scarce_bundle_group_states(B,I,J,max_states=120);Z.extend(B);R=B
	e=set()
	for(C,L,S)in Z:
		if time.monotonic()>H-.05:break
		f=C,tuple(sorted(L))
		if f in e:continue
		e.add(f);T=_complete_scarce_bundle_groups_with_mcf(S,J,I)
		if not T:continue
		F=_solution_expected_cost(T,M,G)
		if F<a-1e-09:K=T;a=F
	return K
def _prune_scarce_bundle_group_states(states,task_list,singles_by_task,max_states):
	B=task_list;A=states;G={B:A for(A,B)in enumerate(B)}
	def C(state):
		C,D,H=state;I=sum(_group_expected_cost(A,len(A[0][1]))for A in H);A=_C
		for E in B:
			if C>>G[E]&1:continue
			F=[A for A in singles_by_task.get(E,[])if A[2]not in D]
			if F:A+=min(_group_expected_cost([A],1)for A in F)
			else:A+=1e2
		return I+A,-_popcount(C),len(D)
	A.sort(key=C);return A[:max_states]
def _complete_scarce_bundle_groups_with_mcf(bundle_groups,singles_by_task,task_list):
	N=singles_by_task;H=bundle_groups;S={B for A in H for B in A[0][1]};O={B[2]for A in H for B in A};B=[A for A in task_list if A not in S];D=[(A[0][0],[A[2]for A in A])for A in H]
	if not B:return D
	I=sorted({A[2]for B in B for A in N.get(B,[])if A[2]not in O});P=0;E=1;J=E+len(B);F=J+len(I);C=_MinCostFlow(F+1);Q={}
	for G in range(len(B)):C.add_edge(P,E+G,1,_C);C.add_edge(E+G,F,1,1e2)
	for T in range(len(I)):C.add_edge(J+T,F,1,_C)
	U={B:A for(A,B)in enumerate(I)}
	for(G,V)in enumerate(B):
		K=E+G;L={}
		for A in N.get(V,[]):
			if A[2]in O:continue
			R=L.get(A[2])
			if R is _A or _group_expected_cost([A],1)<_group_expected_cost([R],1)-1e-12:L[A[2]]=A
		for(W,A)in L.items():X=J+U[W];M=len(C.graph[K]);C.add_edge(K,X,1,_group_expected_cost([A],1));Q[K,M]=A
	if C.min_cost_flow(P,F,len(B))<len(B):return D
	for((Y,M),A)in Q.items():
		if C.graph[Y][M][1]==0:D.append((A[0],[A[2]]))
	return D
def _prune_scarce_bundle_states(states,task_list,singles_by_task,max_states):
	B=task_list;A=states;H={B:A for(A,B)in enumerate(B)}
	def C(state):
		C,D,E=state;I=sum(_group_expected_cost([A],len(A[1]))for A in E);A=_C
		for F in B:
			if C>>H[F]&1:continue
			G=[A for A in singles_by_task.get(F,[])if A[2]not in D]
			if G:A+=min(_group_expected_cost([A],1)for A in G)
			else:A+=1e2
		return I+A,-_popcount(C),len(D),tuple(A[0]for A in E)
	A.sort(key=C);return A[:max_states]
def _complete_scarce_bundles_with_mcf(bundle_rows,singles_by_task,task_list):
	N=singles_by_task;H=bundle_rows;S={B for A in H for B in A[1]};O={A[2]for A in H};B=[A for A in task_list if A not in S];D=[(A[0],[A[2]])for A in H]
	if not B:return D
	I=sorted({A[2]for B in B for A in N.get(B,[])if A[2]not in O});P=0;E=1;J=E+len(B);F=J+len(I);C=_MinCostFlow(F+1);Q={}
	for G in range(len(B)):C.add_edge(P,E+G,1,_C);C.add_edge(E+G,F,1,1e2)
	for T in range(len(I)):C.add_edge(J+T,F,1,_C)
	U={B:A for(A,B)in enumerate(I)}
	for(G,V)in enumerate(B):
		K=E+G;L={}
		for A in N.get(V,[]):
			if A[2]in O:continue
			R=L.get(A[2])
			if R is _A or _group_expected_cost([A],1)<_group_expected_cost([R],1)-1e-12:L[A[2]]=A
		for(W,A)in L.items():X=J+U[W];M=len(C.graph[K]);C.add_edge(K,X,1,_group_expected_cost([A],1));Q[K,M]=A
	if C.min_cost_flow(P,F,len(B))<len(B):return D
	for((Y,M),A)in Q.items():
		if C.graph[Y][M][1]==0:D.append((A[0],[A[2]]))
	return D
def _solve_sparse_cover(candidates,all_tasks,deadline):
	D=deadline;B=all_tasks;A=candidates;C=[]
	for G in(_H,_G,_I):
		if time.monotonic()>D-.25:break
		F=_sparse_greedy(A,G)
		if not C or _simple_result_score(F,A,B)<_simple_result_score(C,A,B):C=F
	H=len(B)<=60 and len(A)<=60000 and len({A[2]for A in A})<=80 and time.monotonic()<D-_E
	if H:
		E=_sparse_beam_search(A,B,D)
		if E and _simple_result_score(E,A,B)<_simple_result_score(C,A,B):C=E
	return C
def _sparse_beam_search(candidates,all_tasks,deadline,coverage_first=_D):
	N=coverage_first;M=candidates;X=sorted(all_tasks);O={B:A for(A,B)in enumerate(X)};H={}
	for A in M:
		B=0;P=_B
		for Q in A[1]:
			if Q not in O:P=_D;break
			B|=1<<O[Q]
		if not P:continue
		F=_group_expected_cost([A],len(A[1]));C=1e2*len(A[1])-F
		if C<=1e-12:continue
		Y=B,C,F,A;H.setdefault(A[2],[]).append(Y)
	if not H:return[]
	R=len(M)<=10000 and len(H)<=25;Z=45 if R else 28;I=[]
	for(a,J)in H.items():
		K={}
		for(B,C,F,A)in J:
			G=K.get(B)
			if G is _A or F<G[2]-1e-12:K[B]=B,C,F,A
		b=sorted(K.values(),key=lambda r:(_popcount(r[0]),r[1],-r[2]),reverse=_B)[:Z];I.append((a,b))
	I.sort(key=lambda item:max((A[1]for A in item[1]),default=_C),reverse=_B);D={0:(_C,())};L=12000 if R else 900 if len(I)<=30 else 520
	for(c,J)in I:
		if time.monotonic()>deadline-.25:break
		E=dict(D)
		for(B,(C,d))in D.items():
			for(S,e,c,A)in J:
				if B&S:continue
				T=B|S;U=C+e;G=E.get(T)
				if G is _A or U>G[0]+1e-12:E[T]=U,d+(A,)
		if len(E)>L:
			if N:V=sorted(E.items(),key=lambda item:(_popcount(item[0]),item[1][0]),reverse=_B)[:L]
			else:V=sorted(E.items(),key=lambda item:(item[1][0],_popcount(item[0])),reverse=_B)[:L]
			D=dict(V)
		else:D=E
	if N:f,(g,W)=max(D.items(),key=lambda item:(_popcount(item[0]),item[1][0]))
	else:f,(g,W)=max(D.items(),key=lambda item:(item[1][0],_popcount(item[0])))
	return[(A[0],[A[2]])for A in W]
def _popcount(value):
	A=value;B=0
	while A:B+=_POPCOUNT_TABLE[A&255];A>>=8
	return B
def _sparse_greedy(candidates,mode):
	J=set();K=set();L=[]
	while _B:
		B=_A;F=_A
		for G in candidates:
			P,H,M,C,I,Q=G
			if M in K:continue
			N=[A for A in H if A not in J]
			if len(N)!=len(H):continue
			D=len(H);A=1e2*D-_group_expected_cost([G],D)
			if A<=1e-12:continue
			if mode==_H:E=D,A/max(C,1e-09),A,I,-C
			elif mode==_G:E=A,D,A/max(C,1e-09),I,-C
			else:E=A/max(C,1e-09),D,A,I,-C
			if F is _A or E>F:F=E;B=G
		if B is _A:break
		L.append((B[0],[B[2]]));K.add(B[2])
		for O in B[1]:J.add(O)
	return L
def _simple_result_score(result,candidates,all_tasks):return _solution_expected_cost(result,candidates,all_tasks)
def _pick_low_robust_best(solutions,candidates,all_tasks):
	B=all_tasks;A=candidates;D=[A for A in solutions if A]
	if not D:return[]
	E=min(D,key=lambda s:_solution_expected_cost(s,A,B));C=_solution_expected_cost(E,A,B)
	def G(solution):E=solution;D=_solution_expected_cost(E,A,B);F=_solution_expected_cost_by_model(E,A,B,_L);G=_solution_expected_cost_by_model(E,A,B,_M);H=.45*D+.45*F+.1*G;I=max(D-C,F-C,G-C);return H+.15*max(_C,I),max(D,F,G),D
	F=min(D,key=G);H=_solution_expected_cost(F,A,B)
	if H<=C+25.:return F
	return E
def _pick_hard_scarce_best(solutions,candidates,all_tasks):
	C=all_tasks;B=candidates;A=[A for A in solutions if A]
	if not A:return[]
	D=sorted(A,key=lambda s:_solution_expected_cost(s,B,C))[:4];E=[]
	for A in D:
		E.append(A);F=_drop_riskiest_groups(A,B,1)
		if F:E.append(F)
		G=_drop_riskiest_groups(A,B,2)
		if G:E.append(G)
	return min(E,key=lambda s:(_hard_scarce_shadow_cost(s,B,C),_solution_expected_cost(s,B,C)))
def _pick_scarce_best(solutions,candidates,all_tasks):
	A=[A for A in solutions if A]
	if not A:return[]
	return min(A,key=lambda s:_solution_expected_cost(s,candidates,all_tasks))
def _drop_riskiest_groups(result,candidates,drop_groups):
	E=drop_groups;D=candidates;C=result
	if E<=0 or len(C)<=E:return C
	F={(A[0],A[2]):A for A in D};B=[]
	for(G,H)in enumerate(C):
		J,I=H;A=[F.get((J,A))for A in I];A=[A for A in A if A is not _A]
		if not A:continue
		K=len(A[0][1]);L=_group_expected_cost(A,K);B.append((L-1e2*K,L/max(1,K),G))
	M={A for(B,C,A)in sorted(B,reverse=_B)[:E]};return[B for(A,B)in enumerate(C)if A not in M]
def _hard_scarce_shadow_cost(result,candidates,all_tasks):
	I=all_tasks;H=candidates;G=result;K={(A[0],A[2]):A for A in H};B=set();E=set();C=_C;L=0;M=0;N=0
	for(J,O)in G:
		A=[]
		for D in O:
			F=K.get((J,D))
			if F is _A or D in E:return float(_F)
			E.add(D);A.append(F)
		if not A:return float(_F)
		for P in A[0][1]:
			if P in B:return float(_F)
			B.add(P)
		C+=_group_expected_cost(A,len(A[0][1]));L+=max(_C,len(A)-2);M+=len(A);N+=len(A[0][1])>=2
	return C+60.*(len(I)-len(B))+14.*L+N+M/5.
def _drop_unprofitable_groups(result,candidates,all_tasks):
	E=all_tasks;C=candidates;B=result;I={(A[0],A[2]):A for A in C};D=[]
	for(F,G)in B:
		A=[I.get((F,A))for A in G];A=[A for A in A if A is not _A]
		if not A:continue
		H=len(A[0][1])
		if _group_expected_cost(A,H)<1e2*H-1e-09:D.append((F,list(G)))
	if _solution_expected_cost(D,C,E)<_solution_expected_cost(B,C,E)-1e-09:return D
	return B
def _solution_covered_count(result,candidates):
	G={(A[0],A[2]):A for A in candidates};A=set();D=set()
	for(H,I)in result:
		B=[]
		for C in I:
			E=G.get((H,C))
			if E is _A or C in D:return-1
			D.add(C);B.append(E)
		if not B:return-1
		for F in B[0][1]:
			if F in A:return-1
			A.add(F)
	return len(A)
def _group_expected_cost_by_model(rows,task_count,model):
	F=task_count;B=model;A=rows
	if B=='avg_subset':return _group_expected_cost(A,F)
	C=_E;D=_C
	if B==_L:G=sorted(A,key=lambda c:(c[3],-c[4],c[5]))
	elif B==_M:G=sorted(A,key=lambda c:(-c[4],c[3],c[5]))
	else:raise ValueError('unknown cost model')
	for E in G:D+=C*E[4]*E[3];C*=_E-E[4]
	D+=C*1e2*F;return D
def _solution_expected_cost_by_model(result,candidates,all_tasks,model):
	H={(A[0],A[2]):A for A in candidates};B=set();E=set();C=_C
	for(I,J)in result:
		A=[]
		for D in J:
			F=H.get((I,D))
			if F is _A or D in E:return float(_F)
			E.add(D);A.append(F)
		if not A:return float(_F)
		for G in A[0][1]:
			if G in B:return float(_F)
			B.add(G)
		C+=_group_expected_cost_by_model(A,len(A[0][1]),model)
	C+=1e2*(len(all_tasks)-len(B));return C
def _solution_expected_cost(result,candidates,all_tasks):
	H={(A[0],A[2]):A for A in candidates};B=set();E=set();C=_C
	for(I,J)in result:
		A=[]
		for D in J:
			F=H.get((I,D))
			if F is _A or D in E:return float(_F)
			E.add(D);A.append(F)
		if not A:return float(_F)
		for G in A[0][1]:
			if G in B:return float(_F)
			B.add(G)
		C+=_group_expected_cost(A,len(A[0][1]))
	C+=1e2*(len(all_tasks)-len(B));return C
def _fallback_official_greedy(candidates):
	F=sorted(candidates,key=lambda c:c[3]);B=set();C=set();D=[]
	for(G,E,A,I,J,K)in F:
		if A in B:continue
		if any(A in C for A in E):continue
		B.add(A)
		for H in E:C.add(H)
		D.append((G,[A]))
	return D
