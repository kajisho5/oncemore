# examples/batch

A template for `oncemore batch`: one disc per session, each with the same
menu. `sessions.csv` has a row per session; `{{speaker}}`, `{{talk}}`,
`{{label}}` and `{{video}}` in `project.oncemore.json` take that row's
values, and `name` is the image's file name.

The videos are not committed; make three short ones and build:

```sh
mkdir -p examples/batch/media
for n in 01 02 03; do
  ffmpeg -f lavfi -i testsrc2=size=320x240:rate=30000/1001:duration=2 \
         -f lavfi -i sine=duration=2 -shortest examples/batch/media/session-$n.mp4
done
oncemore batch examples/batch examples/batch/sessions.csv -o batch-out
```

`batch-out` then holds `session-01.iso` to `session-03.iso`, each read back
and verified, and `manifest.json` with their sizes and SHA-256.
