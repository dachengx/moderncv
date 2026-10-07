# moderncv

[![Build template](https://github.com/moderncv/moderncv/actions/workflows/build-pdf.yml/badge.svg)](https://github.com/moderncv/moderncv/actions/workflows/build-pdf.yml)
[![CTAN](https://img.shields.io/ctan/v/moderncv.svg)](https://www.ctan.org/pkg/moderncv)
[![Matrix](https://img.shields.io/matrix/moderncv:matrix.org)](https://matrix.to/#/#moderncv:matrix.org)

## A modern curriculum vitae class for LaTeX

The `moderncv` package provides a document class for typesetting applications (curricula vitae and cover letters) in various styles. `moderncv` aims to be both straightforward to use and customizable, providing five ready-made styles (classic, casual, banking, oldstyle and fancy) and allowing you to define your own by modifying colors, fonts, icons, etc.

## Getting started

### Installation
`moderncv` should already be included in your installed LaTeX distribution.
If not, you can get the tarball of the package from [CTAN](https://www.ctan.org/pkg/moderncv).
Alternatively, you can also build the package from source by cloning the its [GitHub repository](https://github.com/moderncv/moderncv) and compiling the included LaTeX files:
```
latexmk -pdf ./template.tex manual/moderncv_userguide.tex
```

### Usage
To get started on your own CV, use and modify the template file `template.tex`.
The user guide can be found in the folder `manual` and contains additional information on what the document class offers.
Take a look at it to see if this package suits your needs.

If you are using the [`academicons`](https://ctan.org/tex-archive/fonts/academicons) package in the template, you will need to use a Xe(La)TeX or Lua(La)TeX engine to render the icons. Otherwise, an alternative icon package will be used automatically.

## Development

As the main goal is to keep this package alive, it is maintained in a loosely structured team.
You can contact us in our matrix room [moderncv:matrix.org](https://matrix.to/#/#moderncv:matrix.org), feel free to join if you have questions or want to contribute.
Development takes place at [github.com/moderncv/moderncv](https://github.com/moderncv/moderncv).

## Licence

`moderncv` is licensed under the [LPPL-1.3c](https://spdx.org/licenses/LPPL-1.3c.html).

## Origin

Original author: Xavier Danaux <xdanaux@gmail.com>
<br/>
Original repository: https://github.com/xdanaux/moderncv

This repository is a fork aiming to maintain `moderncv` inside CTAN, since upstream has been dead since 2016.


## Personal CV publications

The English CV uses one maintained publication database:
`../postdoc_application/Proposals/Publication_List/bibliography.bib`.
Set `selected = {true}` on each paper that should appear in the CV and in the
selected-publications group of the standalone publication list. The same field
controls both lists. Papers within each group keep the order of the shared database.

Near the top of `english.tex`, set the two publication switches. For example,
to include Selected Publications only:

```latex
\showpublicationstrue % Show publication sections
% \showpublicationsfalse % Omit all publication sections

\fullpublicationsfalse % Selected Publications only
% \fullpublicationstrue % Also include Other Publications
```

Choose one setting for each switch. `\showpublicationsfalse` hides all publication
sections, regardless of the other switch, for applications that require a separate
publication list. With `\showpublicationstrue`, Selected Publications appears and
`\fullpublicationstrue` adds Other Publications. Full mode includes every paper in
the shared database, including preprints, and numbers each group from 1.
Contribution annotations appear only for selected papers. Both publication
headings use the same section style as the rest of the CV.

`publications.bib` and `publications-other.bib` are generated. Edit publication details, contribution roles,
annotations, distinctions, and highlight links in the shared database only.
The exporter keeps every field and the CV's `urldoi.bst` renders the metadata.

From this directory, build the English CV as usual:

```sh
latexmk --lualatex english.tex
```

The local `.latexmkrc` refreshes both bibliography files before checking whether the CV
is up to date. It also tracks the shared database and exporter during `-pvc` runs.
A missing or invalid database stops the CV build with an error.
The example documents do not require the external database.

To run from another directory, explicitly load the project configuration:

```sh
latexmk -r /path/to/moderncv/.latexmkrc -cd -lualatex /path/to/moderncv/english.tex
```

For another checkout layout, set `CV_PUBLICATIONS_SOURCE` to the shared `.bib`
path. A relative value is resolved from the moderncv directory. If necessary,
`CV_PUBLICATIONS_PYTHON` can specify the Python 3 executable; no additional Python
packages are required.

You can also refresh or check the generated file directly:

```sh
python3 scripts/sync_publications.py
python3 scripts/sync_publications.py --check
python3 scripts/sync_publications.py --selection other --output publications-other.bib
```

The exporter accepts `--source` and `--output` for explicit paths, and
`--selection selected|other` to choose the group (selected by default). `--check` never
writes files and exits with status 1 when the generated bibliography is out of date.
Normal export leaves the file untouched when its contents are already correct.
