"""Machine-readable contract (`oncemore contract --json`), in the shape the AI
Video Production OS registry reads (skill_id, version, contract_version,
provides, dependencies, not_provided)."""

from . import __version__
from .tools import REQUIRED

SKILL_ID = "oncemore"
CONTRACT_VERSION = "1.0"

# Capability id -> command. clean, gui, doctor, mcp and contract are not capabilities.
COMMANDS = {
    "disc.create_project": ("init", "create a sample project"),
    "disc.test_disc": ("testdisc", "create a disc project for testing a set-top player"),
    "disc.validate": ("validate", "check project, media and size"),
    "disc.menu_from_psd": ("import-psd", "make a menu from a layered Photoshop file"),
    "disc.simulate": ("simulate", "press remote-control keys on the project (no encoding)"),
    "disc.author": ("build", "author VIDEO_TS (or a Blu-ray BDMV) into a directory"),
    "disc.image": ("iso", "build and write an ISO image"),
    "disc.burn": ("burn", "write a disc image to a blank DVD or BD"),
    "disc.chapter_suggestions": ("scenes", "find the scene changes in a video: chapter suggestions"),
    "disc.transcode": ("transcode", "encode titles now; the next build or iso reuses them"),
    "disc.preview_menu": ("preview-menu", "render a menu to PNG"),
}


def contract():
    return {
        "skill_id": SKILL_ID,
        "id": SKILL_ID,
        "version": __version__,
        "contract_version": CONTRACT_VERSION,
        "provides": [{"id": cap, "lifecycle": "STABLE", "tool_id": f"{SKILL_ID}/{cmd}"}
                     for cap, (cmd, _) in COMMANDS.items()],
        # No Skill dependencies: ffmpeg and ffprobe are run directly (see `oncemore doctor`),
        # and bdmvkit, vtskit, udfkit and dvdcc are vendored (oncemore/_vendor).
        "dependencies": [],
        "vendored": ["bdmvkit", "vtskit", "udfkit", "dvdcc"],
        "external_tools": {"required": list(REQUIRED),
                           "report": ["oncemore", "doctor", "--json"]},
        "not_provided": ["editing, grading or mixing the titles (the video production Skills)",
                         "copy protection of any kind", "network access of any kind"],
        "tools": [{"tool_id": f"{SKILL_ID}/{cmd}", "command": cmd, "description": desc}
                  for cmd, desc in COMMANDS.values()],
        "execution": {"canonical_invocation": ["oncemore", "<command>", "...", "--json"],
                      "output": "JSON Lines on stdout with --json; the last line is the result",
                      "mcp": ["oncemore", "mcp"], "network": False, "shell": False},
    }
