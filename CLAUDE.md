# oncemore: notes for Claude Code

Read `README.md` and `docs/DECISIONS.md` (newest last) first.

## The libraries (DECISIONS §105)

The disc formats are four libraries, each in its own repository and released
to PyPI: vtskit, udfkit, bdmvkit and dvdcc.

* A change to a disc format is made, tested and released in the library's
  repository; oncemore then takes the release with
  `python tools/vendor.py <library> --pypi <version>`.
* Never edit `oncemore/_vendor/`: it is a copy, replaced as a whole.
* vtskit is worked on by its own session; do not change its repository.
* oncemore itself is not published to PyPI.

## Conventions

* Python 3.11+, standard library only. No outbound network in the package.
* Tests: `python -m unittest discover -s tests -t .`; never skip or weaken one.
* Every change: README (en) and README.ja.md in step, a DECISIONS entry, and
  a test that fails without it.
* The classic authoring apps are "the classic apps"; never name a vendor.
