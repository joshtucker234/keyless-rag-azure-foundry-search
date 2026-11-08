# The 20 PDFs

All are free, public-domain NIST publications. Download each one from the NIST Computer Security Resource Center
(<https://csrc.nist.gov/publications>) or the NIST Publications portal (<https://www.nist.gov/publications>), searching by the
publication number, and save it into `./pdfs` with **exactly** the file name below. The sample library and expected pages
in `app/samples.py` depend on these names and on these document versions.

| File name | Publication |
|---|---|
| `NIST-AI-100-1_AI-Risk-Management-Framework.pdf` | NIST AI 100-1, AI Risk Management Framework 1.0 |
| `NIST-AI-100-2e2023_Adversarial-Machine-Learning.pdf` | NIST AI 100-2 E2023, Adversarial Machine Learning |
| `NIST-CSWP-29_Cybersecurity-Framework-2.0.pdf` | NIST CSWP 29, Cybersecurity Framework 2.0 |
| `NIST-SP-1270_Bias-in-AI.pdf` | NIST SP 1270, Towards a Standard for Identifying and Managing Bias in AI |
| `NIST-SP-800-122_Protecting-PII.pdf` | NIST SP 800-122, Protecting the Confidentiality of PII |
| `NIST-SP-800-144_Public-Cloud-Security-Privacy.pdf` | NIST SP 800-144, Security and Privacy in Public Cloud Computing |
| `NIST-SP-800-145_Cloud-Computing-Definition.pdf` | NIST SP 800-145, The NIST Definition of Cloud Computing |
| `NIST-SP-800-190_Container-Security.pdf` | NIST SP 800-190, Application Container Security Guide |
| `NIST-SP-800-207_Zero-Trust-Architecture.pdf` | NIST SP 800-207, Zero Trust Architecture |
| `NIST-SP-800-210_Cloud-Access-Control.pdf` | NIST SP 800-210, General Access Control Guidance for Cloud Systems |
| `NIST-SP-800-218_Secure-Software-Development.pdf` | NIST SP 800-218, Secure Software Development Framework |
| `NIST-SP-800-30r1_Risk-Assessments.pdf` | NIST SP 800-30 Rev. 1, Guide for Conducting Risk Assessments |
| `NIST-SP-800-34r1_Contingency-Planning.pdf` | NIST SP 800-34 Rev. 1, Contingency Planning Guide for Federal Information Systems |
| `NIST-SP-800-37r2_Risk-Management-Framework.pdf` | NIST SP 800-37 Rev. 2, Risk Management Framework |
| `NIST-SP-800-40r4_Patch-Management.pdf` | NIST SP 800-40 Rev. 4, Guide to Enterprise Patch Management Planning |
| `NIST-SP-800-61r2_Incident-Handling.pdf` | NIST SP 800-61 Rev. 2, Computer Security Incident Handling Guide |
| `NIST-SP-800-63-3_Digital-Identity.pdf` | NIST SP 800-63-3, Digital Identity Guidelines |
| `NIST-SP-800-63B_Authentication.pdf` | NIST SP 800-63B, Authentication and Lifecycle Management |
| `NIST-SP-800-88r1_Media-Sanitization.pdf` | NIST SP 800-88 Rev. 1, Guidelines for Media Sanitization |
| `NIST-SP-800-92_Log-Management.pdf` | NIST SP 800-92, Guide to Computer Security Log Management |

Check your set with `python scripts/split_pdfs.py pdfs pdfs-split`: it should print `58 parts, 1439 pages`. A different number means
a different document version, so the expected pages in the sample library may be off by a few. Document versions are the most
common reason a scorecard disagrees with ours.

Keep the corpus about this size: Document Layout is billed per page, so a larger corpus costs proportionally more.
