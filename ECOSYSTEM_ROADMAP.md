# Roadmap — oncemore

Part of the [AI Video Production OS](https://github.com/kajisho5/AI-video-production-OS/blob/main/docs/ecosystem/ROADMAP.md) ecosystem: department **納品 (Delivery)**, status `active`, optional component.
Written from a read-only audit of this repository on 2026-10-30. Each step below is meant to be one pull request; tick it off by linking the PR.

## Where it stands

v1.3.0, Mac disc app: init, testdisc, validate, import-psd, simulate, build, iso, burn, scenes, transcode, preview-menu, gui, doctor, mcp. 74 test modules. Vendors bdmvkit, vtskit, udfkit, dvdcc.

## What this repository owns

`ecosystem.json` gives each job to exactly one repository. Work outside this list belongs to its owner and is handed over, not re-implemented.

| Owned job | Status | Note |
|---|---|---|
| ディスク作成アプリ(Mac) | done |  |

## Wiring

The agent names oncemore in a handoff when a plan asks for a disc (step 3, video-production-agent#109); it authors nothing itself.

## Steps

- [x] **1. Contract in the OS schema**
  - Done when: validates against the OS schema
- [x] **2. Root SKILL.md over the existing MCP/CLI** — [#146](https://github.com/kajisho5/oncemore/pull/146)
  - Done when: marketplace-ready
- [x] **3. (agent side) handoff-only SkillSpec disc_author** — names oncemore when a plan asks for a disc ([video-production-agent#109](https://github.com/kajisho5/video-production-agent/pull/109), its ADR-094: `job.disc_author=true` → a BLOCKED step whose handoff names oncemore; no adapter, nothing authored by the agent)
  - Done when: handoff test

## Boundaries

The four kits are listed separately in ecosystem.json for library use only.

---
Engine for every media operation: [ffmpeg-skill](https://github.com/kajisho5/ffmpeg-skill) (3.x, 42 tools, contract_version 2.0; treated as complete, proposals go to Velisa's ROADMAP). Orchestrator: [video-production-agent](https://github.com/kajisho5/video-production-agent).
