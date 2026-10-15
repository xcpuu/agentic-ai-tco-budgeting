"""Illustrative three-year TCO simulation for a customer-support agent (Paper A, Section 7.2).
All inputs are assumptions chosen for illustration, not measurements. Seed fixed for reproducibility."""
import numpy as np, json, sys

def run(N=200_000, seed=20261004, tok_med0=140_000, sig_dep=0.40, sig_task_div=3.0,
        p_in=2.00, p_out=12.00, in_share=0.85, mp=(0.30,0.70,1.00),
        fail_mean=0.06, esc=(3,6,12), vol=40_000, sig_vol=0.15, cycle=(12,18)):
    rng = np.random.default_rng(seed)
    tri = lambda a,m,b: rng.triangular(a,m,b,N)
    ramp = np.array([1/3, 2/3] + [1.0]*34)
    vol_mult = rng.lognormal(0, sig_vol, N)
    vm = vol * ramp[None,:] * vol_mult[:,None]
    tk = [vm[:,12*y:12*(y+1)].sum(axis=1) for y in range(3)]
    tok_med = tok_med0 * rng.lognormal(0, sig_dep, N)
    sig_t = np.log(sig_task_div)/1.645
    tok_mean = tok_med*np.exp(sig_t**2/2)
    p0 = in_share*p_in + (1-in_share)*p_out
    m_p = tri(*mp)
    pm = [np.ones(N), m_p, m_p**2]
    inf = [tk[y]*tok_mean/1e6*p0*pm[y] for y in range(3)]
    strategic, impl = tri(12_000,18_400,30_000), tri(60_000,86_000,130_000)
    k = 94*fail_mean/0.06*0+ (1-fail_mean)/fail_mean  # beta(1,k) not used; use beta(a,b) with mean=fail_mean, a+b=100
    fr = rng.beta(100*fail_mean, 100*(1-fail_mean), N)
    ec = tri(*esc)
    rw = [tk[y]*fr*ec for y in range(3)]
    drift = (36/rng.uniform(*cycle, N))*tri(20_000,35_000,70_000)
    sup = [tri(18_000,22_000,35_000) for _ in range(3)]
    ms = tri(25_000,40_000,70_000); mr = [tri(15_000,25_000,45_000) for _ in range(3)]
    tco = strategic+impl+ms+drift
    for y in range(3): tco = tco+inf[y]+rw[y]+sup[y]+mr[y]
    return dict(tco=tco, inf=sum(inf), rw=sum(rw), drift=drift, sup=sum(sup), meas=ms+sum(mr), fixed=strategic+impl,
                inf_y=inf, tk=tk, tok_med=tok_med, tok_mean=tok_mean, p0=p0)

if __name__=="__main__":
    base = run()
    P = lambda a: np.percentile(a,[5,50,95])
    print("BASE tco", P(base['tco']).round(-3), "mean", base['tco'].mean().round(-3), "P90", np.percentile(base['tco'],90).round(-3))
    b50 = np.median(base['tco'])
    variants = {
     "Failure rate 3% / 10%": (dict(fail_mean=0.03), dict(fail_mean=0.10)),
     "Escalation cost $3 / $12 per failed ticket": (dict(esc=(1.5,3,6)), dict(esc=(6,12,24))),
     "Median tokens/ticket 70K / 280K": (dict(tok_med0=70_000), dict(tok_med0=280_000)),
     "Price capture (annual mult.) 0.5-0.9-1.0 vs 0.15-0.4-0.7": (dict(mp=(0.5,0.9,1.0)), dict(mp=(0.15,0.4,0.7))),
     "Volume 20K / 80K tickets/month": (dict(vol=20_000), dict(vol=80_000)),
     "Blended price: low-tier ($0.10/$0.40) / flagship ($5/$25)": (dict(p_in=0.10,p_out=0.40), dict(p_in=5.0,p_out=25.0)),
    }
    print("Median TCO base: %.0fK"%(b50/1e3))
    for k,(lo,hi) in variants.items():
        l = np.median(run(**lo)['tco']); h = np.median(run(**hi)['tco'])
        print(f"{k}: {l/1e3:,.0f}K / {h/1e3:,.0f}K  (swing {abs(h-l)/1e3:,.0f}K)")
    # per-ticket tail illustration
    rng = np.random.default_rng(1)
    sig_t = np.log(3.0)/1.645
    med = 140_000; p0=base['p0']
    c = rng.lognormal(np.log(med), sig_t, 1_000_000)/1e6*p0
    print("Per-ticket cost at median deployment: P50 %.2f P90 %.2f P99 %.2f mean %.2f"%(np.percentile(c,50),np.percentile(c,90),np.percentile(c,99),c.mean()))
    top1 = np.sort(c)[::-1][:10_000].sum()/c.sum()
    print("Share of spend from top 1%% of tickets: %.1f%%"%(100*top1))
