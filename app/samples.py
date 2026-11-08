"""Sample question library with ground truth.

Expected pages are NOT hand-typed: resolve() searches the original PDFs for anchor phrases, so the
expectations are independent of the search index. Pages are PDF page indexes (1 = first page of the file),
not the page numbers printed on the pages.
"""
import glob
import json
import logging
import os
import re

from pypdf import PdfReader

logging.getLogger("pypdf").setLevel(logging.ERROR)

HERE = os.path.dirname(os.path.abspath(__file__))
PDF_DIR = os.path.join(HERE, "..", "pdfs")
RESOLVED = os.path.join(HERE, "samples_resolved.json")

# category: exact = distinctive terms; paraphrase = no shared vocabulary; neighbor = a similar sibling document
# exists; none = not in the corpus (the app should refuse)
SAMPLES = [
    dict(id="S01", category="paraphrase", question="What are the phases of the incident response life cycle?",
         docs=["800-61r2"], anchors=[r"Containment,\s*Eradication,?\s*and\s*Recovery", r"Post-Incident Activity"],
         key_points=[r"prepar", r"detection and analysis", r"containment", r"post-incident"],
         expect="Four phases: preparation; detection and analysis; containment, eradication and recovery; post-incident activity."),
    dict(id="S02", category="paraphrase", question="Which components decide and enforce whether a session is allowed in a zero trust architecture?",
         docs=["800-207"], match="any",
         anchors=[r"policy enforcement point \(PEP\)", r"policy engine", r"policy administrator"],
         key_points=[r"policy (engine|decision)", r"enforcement point|PEP"],
         expect="The Policy Decision Point (Policy Engine plus Policy Administrator) decides; the Policy Enforcement Point enables or terminates the connection."),
    dict(id="S03", category="paraphrase", question="What are the different kinds of bias that show up in AI?",
         docs=["SP-1270"], anchors=[r"statistical and computational", r"systemic"],
         key_points=[r"systemic", r"statistical", r"human"],
         expect="Three categories: systemic, statistical and computational, and human (cognitive) bias."),
    dict(id="S04", category="exact", question="What is the minimum length required for user-chosen passwords?",
         docs=["800-63B"], anchors=[r"at least 8 characters"],
         key_points=[r"\b8\b"],
         expect="Memorized secrets chosen by the subscriber must be at least 8 characters."),
    dict(id="S05", category="paraphrase", question="How can erasing encryption keys make stored data unrecoverable?",
         docs=["800-88r1"], anchors=[r"cryptographic erase"],
         key_points=[r"cryptographic erase", r"key"],
         expect="Cryptographic Erase sanitizes encrypted media by destroying the encryption keys so the data can no longer be read."),
    dict(id="S06", category="neighbor", question="What are the seven steps of the risk management framework?",
         docs=["800-37r2"], anchors=[r"Prepare to execute", r"Categorize the system", r"Monitor the"],
         key_points=[r"prepar", r"categori", r"select", r"implement", r"assess", r"authori", r"monitor"],
         expect="Prepare, Categorize, Select, Implement, Assess, Authorize, Monitor. (Trap: 800-30 has a similar-looking 4-step process.)"),
    dict(id="S07", category="neighbor", question="What are the steps of the risk assessment process?",
         docs=["800-30r1"], anchors=[r"Prepare for (the )?(risk )?assessment", r"Communicate"],
         key_points=[r"prepar", r"conduct", r"communicat", r"maintain"],
         expect="Four steps: prepare for the assessment, conduct it, communicate the results, maintain the assessment. (Trap: 800-37 has the 7-step RMF.)"),
    dict(id="S08", category="paraphrase", question="How long can a system be down before the mission suffers?",
         docs=["800-34r1"], anchors=[r"Maximum Tolerable Downtime"],
         key_points=[r"maximum tolerable downtime|MTD"],
         expect="Maximum Tolerable Downtime (MTD): the longest a system can be unavailable before causing unacceptable mission impact, determined in the business impact analysis."),
    dict(id="S09", category="paraphrase", question="What qualities make an AI system trustworthy?",
         docs=["AI-100-1"], anchors=[r"valid and reliable"],
         key_points=[r"valid", r"safe", r"secure", r"accountable", r"explainable", r"privacy", r"fair"],
         expect="Valid and reliable; safe; secure and resilient; accountable and transparent; explainable and interpretable; privacy-enhanced; fair with harmful bias managed."),
    dict(id="S10", category="paraphrase", question="What standard protocol is used to ship log messages across a network?",
         docs=["800-92"], anchors=[r"syslog"],
         key_points=[r"syslog"],
         expect="Syslog."),
    dict(id="S11", category="exact", question="What are the essential characteristics of cloud computing?",
         docs=["800-145"], anchors=[r"On-demand self-service", r"Measured service"],
         key_points=[r"on-demand self-service", r"broad network access", r"resource pooling", r"rapid elasticity", r"measured service"],
         expect="Five: on-demand self-service, broad network access, resource pooling, rapid elasticity, measured service."),
    dict(id="S12", category="paraphrase", question="How do attackers corrupt the data used to teach a model?",
         docs=["AI-100-2e2023"], anchors=[r"poisoning attack"],
         key_points=[r"poison", r"training"],
         expect="Poisoning attacks: the adversary manipulates the training data (or model) to degrade or steer the trained model."),
    dict(id="S13", category="exact", question="What does AAL2 require?",
         docs=["800-63B", "800-63-3"], anchors=[r"AAL2"],
         key_points=[r"AAL2", r"two|multi"],
         expect="Authenticator Assurance Level 2: proof of possession and control of two distinct authentication factors."),
    dict(id="N01", category="none", question="What is a good chocolate chip cookie recipe?",
         docs=[], anchors=[], key_points=[], expect="Not in the documents. The app should say it couldn't find it."),
    dict(id="N02", category="none", question="What was Microsoft's revenue last quarter?",
         docs=[], anchors=[], key_points=[], expect="Not in the documents. The app should say it couldn't find it."),
]


def _find_pdf(sub: str):
    hits = sorted(glob.glob(os.path.join(PDF_DIR, f"*{sub}*.pdf")))
    return hits[0] if hits else None


def resolve(force: bool = False):
    """Search the original PDFs for the anchors and record the pages they appear on."""
    if os.path.exists(RESOLVED) and not force:
        return json.load(open(RESOLVED))
    cache, out = {}, []
    for s in SAMPLES:
        s = dict(s)
        pages = {}
        for sub in s["docs"]:
            path = _find_pdf(sub)
            if not path or not s["anchors"]:
                continue
            if path not in cache:
                cache[path] = [re.sub(r"\s+", " ", p.extract_text() or "") for p in PdfReader(path).pages]
            texts = cache[path]
            all_hit = [i + 1 for i, t in enumerate(texts) if all(re.search(a, t, re.I) for a in s["anchors"])]
            any_hit = [i + 1 for i, t in enumerate(texts) if any(re.search(a, t, re.I) for a in s["anchors"])]
            pages[sub] = any_hit if s.get("match") == "any" else (all_hit or any_hit)
        s["expected_pages"] = pages
        out.append(s)
    json.dump(out, open(RESOLVED, "w"), indent=1)
    return out


def load():
    return resolve()


def source_ok(sample: dict, d: dict) -> bool:
    """True if a retrieved chunk is on an expected page of an expected document."""
    exp = sample.get("expected_pages", {})
    return any(sub in d["doc"] and d["page"] in exp.get(sub, []) for sub in sample["docs"])


def check(sample: dict, result: dict) -> dict:
    """Compare an app.answer() result with the sample's expectations."""
    if sample["category"] == "none":
        return {"refused": result["refused"], "passed": result["refused"]}
    docs = result["docs"]

    def src_ok(d):
        return source_ok(sample, d)

    cited = sorted({int(n) for n in re.findall(r"\[(\d+)\]", result["text"])})
    cited_docs = [docs[i - 1] for i in cited if 0 < i <= len(docs)]
    c = {
        "refused": result["refused"],
        "top1_source": bool(docs) and src_ok(docs[0]),
        "any_retrieved": any(src_ok(d) for d in docs),
        "cited_source": any(src_ok(d) for d in cited_docs),
        "key_points": all(re.search(k, result["text"], re.I) for k in sample["key_points"]),
    }
    c["passed"] = (not c["refused"]) and c["any_retrieved"] and c["cited_source"] and c["key_points"]
    return c
