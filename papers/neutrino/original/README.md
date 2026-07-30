# Original Neutrino source snapshots

These ZIP files preserve the two upstream revisions used by this catalogue.
They were created with `git archive`; upstream Git history is not embedded.

| Snapshot | Revision | SHA-256 | Purpose |
|---|---|---|---|
| `neutrino-main-4a82cd22f474.zip` | `4a82cd22f474c31ac2fecfa174d381a19bb3f469` | `0f006387c948a12440787a6eb43dfebf0ad50ada8c67e2d4b46b5001eed44284` | Main implementation imported into `artifact/` |
| `neutrino-artifact-43182f3082f5.zip` | `43182f3082f5617d8bc85cd8902af4f6fbaeeb24` | `696d23c3ebefc5e1b9871d75f2569eed693401fe998d053bbc3b644db6fa11b2` | OSDI artifact-evaluation branch |

- Canonical repository: <https://github.com/open-neutrino/neutrino>
- Main source: <https://github.com/open-neutrino/neutrino/tree/4a82cd22f474c31ac2fecfa174d381a19bb3f469>
- Artifact branch: <https://github.com/open-neutrino/neutrino/tree/43182f3082f5617d8bc85cd8902af4f6fbaeeb24>

No licence file exists in either archived tree. The artifact-branch README says
the system source uses Apache-2.0 and its probes use CC-BY-4.0, while
`setup.py` classifies the package as MIT. Because those statements conflict
and no licence text is included, redistribution terms remain unresolved.
