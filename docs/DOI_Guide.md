# Getting a DOI for the code and data package

A DOI is a permanent identifier for a specific, frozen version of your files. Journals and conferences accept a DOI as a stable citation target, and the DOI link keeps working even if the GitHub repository is renamed or deleted. The standard free route is GitHub plus Zenodo (run by CERN), which mints DOIs at no cost.

## Steps (about 30 minutes)

1. **Create a GitHub account and a public repository.** Name it, for example, `agentic-ai-tco-budgeting`. Upload the contents of `paperA-supplement/` (code, data, docs, README, LICENSE, CITATION.cff, .zenodo.json, requirements.txt, run_all.sh). Do not upload the encrypted HAL traces.
2. **Fill in the placeholders.** In `CITATION.cff`, replace the repository URL and set `date-released`. Add your ORCID (free at orcid.org) to `CITATION.cff` and `.zenodo.json` if you have one; it links the DOI to your name in scholarly databases.
3. **Confirm the licenses.** Code is MIT. For the data tables, confirm the terms of the Holistic Agent Leaderboard before publishing, then keep CC BY 4.0 or change it.
4. **Make sure it reproduces.** Run `bash run_all.sh` once on your machine. A package that fails to reproduce is the most common reviewer complaint.
5. **Sign in to Zenodo with GitHub.** Go to zenodo.org, choose "Log in with GitHub", then open Account > GitHub and switch the repository on.
6. **Publish a release on GitHub.** On the repository page choose Releases > Draft a new release, tag it `v1.0.0`, and publish. Zenodo detects the release, archives a snapshot and mints two DOIs: a *version DOI* for exactly this snapshot and a *concept DOI* that always points to the latest version.
7. **Cite the DOI in the paper.** Use the version DOI in the paper's data-availability statement and reference list, for example: "Code and data are available at https://doi.org/10.5281/zenodo.XXXXXXX." Zenodo shows a ready-made citation and a DOI badge for the README.
8. **Link the paper and the package.** After the paper has a DOI or arXiv number, add it in Zenodo under related identifiers ("is supplement to"). Updating metadata does not change the archived files.

## Practical points

- **A DOI freezes a version.** If you later fix a bug, publish a new release (`v1.0.1`). Zenodo issues a new version DOI under the same concept DOI.
- **Do it before submission, but check the venue's rules.** Some conferences require anonymized supplements for double-blind review. If so, submit a zip with the author fields removed for review, and mint the public DOI after acceptance. Reserve a DOI on Zenodo ahead of time if the venue wants the identifier in the camera-ready.
- **Alternatives.** Figshare and OSF also mint DOIs and accept zip uploads without GitHub. Dryad and university repositories are other options. The University of Michigan library may offer an institutional repository (Deep Blue Data); alumni access varies, so check.
- **Paper DOI is separate.** The conference or IEEE assigns the paper's own DOI at publication. You do not create that one. IEEE Xplore records can also list supplementary material, which the conference's author instructions describe.
- **Immutability.** Zenodo records cannot be deleted once published (only withdrawn by request), so review the files and metadata before clicking publish. Never upload credentials, personal data or the raw HAL files.
- **Cost.** Zenodo is free for files up to 50 GB per record.

## Suggested statement for the paper

> Code, per-task cost tables and result files that reproduce all pilot and case-study numbers are archived at https://doi.org/10.5281/zenodo.XXXXXXX (version 1.0.0). The original Holistic Agent Leaderboard traces are not redistributed; file names, run identifiers and checksums are given in the package.
