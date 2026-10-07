#!/usr/bin/env python3
"""Export the records marked selected={true} without rewriting their BibTeX.

The supported syntax is ordinary brace/parenthesis records, brace/quote values,
numbers, and string macros joined with #. String and preamble declarations are
retained in source order; comments outside records and @comment are omitted.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import os
from pathlib import Path
import re
import stat
import sys
import tempfile


class BibliographyError(ValueError):
    """An input cannot safely produce a CV bibliography."""


@dataclass(frozen=True)
class Term:
    value: str
    macro: bool = False


@dataclass(frozen=True)
class Record:
    kind: str
    raw: str
    key: str = ""
    fields: dict[str, tuple[Term, ...]] | None = None
    expression: tuple[Term, ...] = ()


class Parser:
    """Read record boundaries and field expressions, retaining the original text."""

    identifier = re.compile(r"[A-Za-z][A-Za-z0-9_:-]*")
    key_pattern = re.compile(r'[^\s,{}()=@"#%]+')

    def __init__(self, text: str):
        self.text = text
        self.pos = 0

    def fail(self, message: str) -> None:
        line = self.text.count("\n", 0, self.pos) + 1
        raise BibliographyError(f"line {line}: {message}")

    def skip(self) -> None:
        while self.pos < len(self.text):
            if self.text[self.pos].isspace():
                self.pos += 1
            elif self.text[self.pos] == "%":
                end = self.text.find("\n", self.pos)
                self.pos = len(self.text) if end < 0 else end + 1
            else:
                break

    def expect(self, char: str) -> None:
        self.skip()
        if not self.text.startswith(char, self.pos):
            self.fail(f"expected {char!r}")
        self.pos += 1

    def name(self) -> str:
        self.skip()
        match = self.identifier.match(self.text, self.pos)
        if match is None:
            self.fail("expected an identifier")
        self.pos = match.end()
        return match.group()

    def literal(self, opener: str) -> str:
        self.pos += 1
        start = self.pos
        depth = 1 if opener == "{" else 0
        while self.pos < len(self.text):
            char = self.text[self.pos]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth < 0:
                    self.fail("unbalanced brace in a quoted value")
                if opener == "{" and depth == 0:
                    result = self.text[start:self.pos]
                    self.pos += 1
                    return result
            elif char == '"' and opener == '"' and depth == 0:
                result = self.text[start:self.pos]
                self.pos += 1
                return result
            self.pos += 1
        self.fail("unterminated braced or quoted value")

    def expression(self) -> tuple[Term, ...]:
        terms = []
        while True:
            self.skip()
            if self.pos >= len(self.text):
                self.fail("expected a field value")
            char = self.text[self.pos]
            if char in '{"':
                terms.append(Term(self.literal(char)))
            else:
                match = self.key_pattern.match(self.text, self.pos)
                if match is None:
                    self.fail("expected a field value")
                value = match.group()
                self.pos = match.end()
                if value.isdecimal():
                    terms.append(Term(value))
                elif self.identifier.fullmatch(value):
                    terms.append(Term(value.casefold(), macro=True))
                else:
                    self.fail(f"invalid bare value {value!r}")
            self.skip()
            if not self.text.startswith("#", self.pos):
                return tuple(terms)
            self.pos += 1

    def close(self, closer: str) -> None:
        self.skip()
        if self.text.startswith(",", self.pos):
            self.pos += 1
        self.expect(closer)

    def comment(self, opener: str) -> None:
        # @comment bodies are prose, so quotes do not delimit field values.
        closer = "}" if opener == "{" else ")"
        depth = 1
        braces = 0
        while self.pos < len(self.text):
            char = self.text[self.pos]
            self.pos += 1
            if opener == "(" and char == "{":
                braces += 1
            elif opener == "(" and char == "}" and braces:
                braces -= 1
            elif braces == 0:
                if char == opener:
                    depth += 1
                elif char == closer:
                    depth -= 1
                    if depth == 0:
                        return
        self.fail("unterminated @comment")

    def parse(self) -> list[Record]:
        records = []
        keys = set()
        while True:
            self.skip()
            if self.pos == len(self.text):
                return records
            start = self.pos
            self.expect("@")
            kind = self.name().casefold()
            self.skip()
            if self.pos >= len(self.text) or self.text[self.pos] not in "{(":
                self.fail("expected '{' or '(' after the record type")
            opener = self.text[self.pos]
            closer = "}" if opener == "{" else ")"
            self.pos += 1
            if kind == "comment":
                self.comment(opener)
                continue
            if kind == "preamble":
                expression = self.expression()
                self.close(closer)
                records.append(Record(kind, self.text[start:self.pos], expression=expression))
                continue
            if kind == "string":
                key = self.name().casefold()
                self.expect("=")
                expression = self.expression()
                self.close(closer)
                records.append(Record(kind, self.text[start:self.pos], key, expression=expression))
                continue
            self.skip()
            match = self.key_pattern.match(self.text, self.pos)
            if match is None:
                self.fail("expected a citation key")
            key = match.group()
            self.pos = match.end()
            if key.casefold() in keys:
                self.fail(f"duplicate citation key {key!r}")
            keys.add(key.casefold())
            fields = {}
            self.expect(",")
            while True:
                self.skip()
                if self.text.startswith(closer, self.pos):
                    self.pos += 1
                    break
                field = self.name().casefold()
                if field in fields:
                    self.fail(f"duplicate field {field!r} in {key!r}")
                self.expect("=")
                fields[field] = self.expression()
                self.skip()
                if self.text.startswith(closer, self.pos):
                    self.pos += 1
                    break
                self.expect(",")
            records.append(Record(kind, self.text[start:self.pos], key, fields))


MONTHS = dict(zip(
    ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"),
    ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"),
))


def resolve(expression: tuple[Term, ...], macros: dict[str, str]) -> str:
    result = []
    for term in expression:
        if term.macro:
            if term.value not in macros:
                raise BibliographyError(f"undefined string macro {term.value!r}")
            result.append(macros[term.value])
        else:
            result.append(term.value)
    return "".join(result)


def build_output(text: str, source_reference: str) -> tuple[bytes, int]:
    records = Parser(text).parse()  # Validate all records before preparing output.
    macros = MONTHS.copy()
    output = []
    count = 0
    for record in records:
        if record.kind == "string":
            macros[record.key] = resolve(record.expression, macros)
            output.append(record.raw)
        elif record.kind == "preamble":
            output.append(record.raw)
        elif record.fields is not None and "selected" in record.fields:
            try:
                selected = resolve(record.fields["selected"], macros)
            except BibliographyError as error:
                raise BibliographyError(f"selected in {record.key!r}: {error}") from error
            if selected == "true":
                output.append(record.raw)
                count += 1
    if count == 0:
        raise BibliographyError("no entries marked selected={true}")
    header = (
        "% Generated by scripts/sync_publications.py; do not edit by hand.\n"
        f"% Source: {source_reference}\n\n"
    )
    return (header + "\n\n".join(output) + "\n").encode("utf-8"), count


def atomic_write(output: Path, contents: bytes) -> None:
    temporary = None
    try:
        descriptor, name = tempfile.mkstemp(prefix=f".{output.name}.", suffix=".tmp", dir=output.parent)
        temporary = Path(name)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(contents)
            handle.flush()
            os.fsync(handle.fileno())
        if output.exists():
            temporary.chmod(stat.S_IMODE(output.stat().st_mode))
        os.replace(temporary, output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    repository = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=repository.parent / "postdoc_application" / "Proposals" / "Publication_List" / "bibliography.bib")
    parser.add_argument("--output", type=Path, default=repository / "publications.bib")
    parser.add_argument("--check", action="store_true", help="check whether the output is current without writing it")
    args = parser.parse_args(argv)
    source = args.source.resolve()
    output = args.output.resolve()
    try:
        if source == output:
            raise BibliographyError("source and output must be different files")
        text = source.read_bytes().decode("utf-8-sig")
        reference = Path(os.path.relpath(source, output.parent)).as_posix()
        contents, count = build_output(text, reference)
        current = output.read_bytes() if output.exists() else None
        if current == contents:
            print(f"Publications are current ({count} CV entries).")
            return 0
        if args.check:
            print(f"Publications are out of date ({count} CV entries); run scripts/sync_publications.py to regenerate.", file=sys.stderr)
            return 1
        atomic_write(output, contents)
        print(f"Updated publications ({count} CV entries).")
        return 0
    except (BibliographyError, OSError, UnicodeError) as error:
        print(f"Publication sync failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
