"""SKILL.md (DECISIONS §138): the root skill file that AI assistants and the
AI Video Production OS marketplace load. Its frontmatter must parse as strict
YAML, and it may only name commands, options and MCP tools that exist, and
must name all of them."""

import argparse
import os
import re
import unittest

from oncemore import cli, contract
from oncemore.mcp import Server

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def skill():
    with open(os.path.join(ROOT, "SKILL.md"), encoding="utf-8") as f:
        return f.read()


def frontmatter(text):
    """The frontmatter's `key: value` lines as a dict (plain or quoted
    scalars only, which is all SKILL.md uses)."""
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if not m:
        raise AssertionError("SKILL.md does not start with a --- frontmatter block")
    fields = {}
    for line in m.group(1).split("\n"):
        key, sep, value = line.partition(": ")
        if not (sep and re.fullmatch(r"[a-z][a-z_-]*", key)):
            raise AssertionError(f"not a `key: value` line: {line!r}")
        quoted = len(value) >= 2 and value[0] == value[-1] and value[0] in "'\""
        if not quoted and (": " in value or " #" in value or value[:1] in "[]{}&*!|>%@`#'\"-?:,"):
            raise AssertionError(f"{key}: needs quoting for a strict YAML parser")
        fields[key] = value[1:-1] if quoted else value
    return fields


def subcommands():
    parser = cli.make_parser()
    action = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))
    return action.choices


class TestFrontmatter(unittest.TestCase):
    def test_name_and_description(self):
        fm = frontmatter(skill())
        self.assertEqual(set(fm), {"name", "description"})
        self.assertEqual(fm["name"], contract.SKILL_ID)
        self.assertRegex(fm["name"], r"^[a-z0-9-]{1,64}$")
        desc = fm["description"]
        self.assertTrue(20 <= len(desc) <= 1024, len(desc))
        self.assertNotRegex(desc, r"[<>]")          # rejected by skill validators
        self.assertIn("Use when", desc)

    def test_strict_yaml_rule_catches_a_bare_colon(self):
        with self.assertRaises(AssertionError):
            frontmatter("---\nname: x\ndescription: a: b\n---\n")
        self.assertEqual(frontmatter("---\nname: x\ndescription: 'a: b'\n---\n")["description"],
                         "a: b")


class TestNamesWhatExists(unittest.TestCase):
    def test_every_command_and_option_exists(self):
        """Each `oncemore <command> ...` in SKILL.md is a real subcommand and
        each --option on it is one of that subcommand's options."""
        cmds = subcommands()
        uses = re.findall(r"`oncemore ([a-z-]+)([^`]*)`", skill())
        self.assertTrue(uses)
        for name, rest in uses:
            self.assertIn(name, cmds, f"SKILL.md names `oncemore {name}`, which does not exist")
            opts = {o for a in cmds[name]._actions for o in a.option_strings}
            for opt in re.findall(r"(?<![\w-])(--?[a-z][a-z-]*)", rest):
                self.assertIn(opt, opts, f"`oncemore {name}` has no option {opt}")

    def test_every_command_is_documented(self):
        documented = set(re.findall(r"`oncemore ([a-z-]+)", skill()))
        self.assertEqual(set(subcommands()) - documented, set())
        for cmd, _ in contract.COMMANDS.values():
            self.assertIn(cmd, documented)

    def test_mcp_tools_match_the_server(self):
        text = skill()
        section = text.split("## MCP tools", 1)[1].split("\n## ", 1)[0]
        listed = set(re.findall(r"^\| `([a-z_]+)` \|", section, re.M))
        self.assertEqual(listed, set(Server(roots=[ROOT]).tools))

    def test_exit_codes_match_the_errors(self):
        from oncemore import errors
        text = skill()
        for cls in (errors.OncemoreError, errors.ProjectError, errors.MissingToolsError,
                    errors.ToolFailedError):
            self.assertIn(f"`{cls.exit_code}`", text)


if __name__ == "__main__":
    unittest.main()
