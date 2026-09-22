# LaTeX Print Standard

## Project-first sizing

Read the real paper/geometry/template. Do not assume IEEE column widths or US Letter if the thesis uses A4.

Prefer `\linewidth` at the insertion point because it respects local environments.

## Vector and raster

For line art, prefer:

1. TikZ/PGF source compiled with the thesis or standalone to PDF;
2. vector PDF;
3. SVG source/asset if the toolchain supports conversion reliably.

Use PNG/JPEG for screenshots, photos, heatmaps, or raster-native assets.

For raster assets, use sufficient native resolution at final physical size. Do not fake quality by changing DPI metadata or upscaling.

As a conservative publication-quality reference, IEEE recommends >300 dpi for color/grayscale raster graphics and >600 dpi for black/white line art; vector should be used whenever practical.

## Font embedding and consistency

- PDF/EPS/PS line art should have embedded fonts or outlined text when appropriate.
- Keep typefaces and sizes consistent across graphics and tables.
- Inspect `pdffonts` when available.

## Tables

- Prefer `booktabs` conventions for formal tables unless the university template requires another style.
- Avoid vertical rules and double rules by default.
- Use units in column headers.
- Align numeric values with `siunitx` when useful.
- Use `longtable`/`xltabular` instead of shrinking large tables into unreadable text.

## Figures

- Caption below figure unless template says otherwise.
- `\label` after `\caption` in ordinary LaTeX patterns.
- Avoid `[H]` everywhere; use project float conventions unless strict placement is required.
- Avoid `\resizebox{\textwidth}{!}{...}` as a first response to density problems.

## Grayscale/accessibility

- Ensure plots/diagrams still work in grayscale.
- Differentiate series with marker/line style/pattern as well as color.
- Use direct labels when useful.
- Add alt text/tagging when the thesis toolchain and submission requirements support accessible PDF.

## Archival output

If the university requires PDF/A:

- generate PDF/A from the original source/toolchain when possible rather than post-converting a broken PDF;
- embed fonts and metadata;
- validate with an available standards validator;
- do not claim PDF/A conformance solely because the filename says PDF/A.
