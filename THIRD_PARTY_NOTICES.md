# Third-party references and notices

PISTE Studio is proprietary/source-visible software. The repository-level
`LICENSE` applies only to original PISTE Studio material for which the
copyright holder owns or controls the relevant rights.

Third-party software and services are **not relicensed** under the PISTE Studio
license. Their own licenses and terms continue to apply.

This notice is intended to document the main direct third-party boundaries of
the project. It is not a substitute for the license texts supplied by those
projects, and transitive dependencies may add further obligations.

## browser-use/video-use

- Project: https://github.com/browser-use/video-use
- Copyright: Copyright (c) 2026 Browser Use
- License: MIT
- Role in PISTE Studio V0.26: architectural and implementation reference for
  transcript-driven editing patterns.

The V0.26 implementation is integrated into PISTE Studio's own data model and
Storyline workflow. No Video Use repository, binary, service, or runtime
dependency is bundled as Video Use itself.

If a present or future PISTE Studio file copies or incorporates a substantial
portion of Video Use source code, the applicable MIT copyright and permission
notice must be preserved with that material.

## Direct Python dependencies declared by PISTE Studio

The project currently declares direct dependencies including:

- PyYAML
- FastAPI
- Uvicorn

Optional development, vision, and packaging dependencies include:

- pytest
- HTTPX
- Playwright
- Transformers
- PyTorch
- Pillow
- PyInstaller
- setuptools
- wheel

Each of these projects remains governed by its own license and notices.
Installing or redistributing PISTE Studio does not relicense those projects
under the PISTE Studio proprietary license.

## Desktop application dependencies

The desktop application uses Tauri v2 and related Rust/JavaScript components,
including Tauri CLI, Tauri plugins, Serde, and Serde JSON.

Those components and their transitive dependencies remain governed by their
respective licenses and required notices.

## Tesseract by Mirage

Tesseract is not bundled, modified, or redistributed by PISTE Studio. It is a
separately installed external tool. See `LICENSE_NOTE.md`.

Mirage/Tesseract terms apply separately to Tesseract itself and to any usage
that depends on it.

## FFmpeg / ffprobe

PISTE Studio can invoke FFmpeg and ffprobe when they are available on the
system or CI environment.

PISTE Studio does not relicense FFmpeg. The applicable FFmpeg license depends
on the particular build, configuration, and components used. Distribution of
an FFmpeg build must therefore be reviewed against that build's own licensing
requirements.

## ElevenLabs

PISTE Studio can optionally call the ElevenLabs speech-to-text service after
explicit user consent.

ElevenLabs is an external service and is not licensed under the PISTE Studio
repository license. Its service terms, privacy terms, pricing, and API
conditions apply separately.

## Distribution note

Before publicly redistributing a packaged build of PISTE Studio, the project
should perform a dependency-license audit for the exact build being shipped
and include any license texts, copyright notices, source-availability
statements, or other notices required by the corresponding third-party
licenses.

The package manager lockfiles and actual build output are authoritative for the
exact dependency set of a given release.
