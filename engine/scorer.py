from collections import defaultdict

PASS = "PASS"
FAIL = "FAIL"
EXCEPTION = "EXCEPTION"
MISSING = "MISSING"
EXPIRED = "EXPIRED"


def ready_clean(status):
    return status == PASS


def ready_effective(status):
    return status in (PASS, EXCEPTION)


def _weighted(verdicts, catalog, control_ids, ready_fn):
    total = 0
    ready = 0
    for cid in control_ids:
        ctrl = catalog.controls[cid]
        total += ctrl.criticality
        status = verdicts.get(cid, {}).get("status", MISSING)
        if ready_fn(status):
            ready += ctrl.criticality
    ratio = (ready / total) if total else 0.0
    return ready, total, ratio


def score(verdicts, catalog, scope=None):
    scope = scope or list(catalog.controls.keys())
    by_domain = defaultdict(list)
    for cid in scope:
        by_domain[catalog.controls[cid].domain].append(cid)

    domains = {}
    for domain, cids in by_domain.items():
        cr, tr, cr_ratio = _weighted(verdicts, catalog, cids, ready_clean)
        er, _, er_ratio = _weighted(verdicts, catalog, cids, ready_effective)
        counts = defaultdict(int)
        for cid in cids:
            counts[verdicts.get(cid, {}).get("status", MISSING)] += 1
        domains[domain] = {
            "clean_ratio": cr_ratio,
            "effective_ratio": er_ratio,
            "ready_weight": cr,
            "total_weight": tr,
            "counts": dict(counts),
        }

    overall_cr, overall_tr, overall_clean = _weighted(verdicts, catalog, scope, ready_clean)
    _, _, overall_effective = _weighted(verdicts, catalog, scope, ready_effective)

    frameworks = {"soc2": defaultdict(lambda: {"ready": 0, "total": 0, "controls": []}),
                  "iso27001": defaultdict(lambda: {"ready": 0, "total": 0, "controls": []})}
    for cid in scope:
        ctrl = catalog.controls[cid]
        status = verdicts.get(cid, {}).get("status", MISSING)
        for fw, refs in (("soc2", ctrl.soc2), ("iso27001", ctrl.iso27001)):
            for ref in refs:
                entry = frameworks[fw][ref]
                entry["total"] += 1
                entry["ready"] += 1 if ready_clean(status) else 0
                entry["controls"].append(cid)
    frameworks = {fw: {ref: dict(v) for ref, v in refs.items()} for fw, refs in frameworks.items()}

    return {
        "scope_size": len(scope),
        "overall": {
            "clean_ratio": overall_clean,
            "effective_ratio": overall_effective,
            "ready_weight": overall_cr,
            "total_weight": overall_tr,
        },
        "domains": domains,
        "frameworks": frameworks,
    }
