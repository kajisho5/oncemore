# A build request

`request.json` is a build request (`oncemore/build-request@1`, DECISIONS §142)
as an editing agent writes it from its plan: the day's recording as one
title, its three sessions as named chapters, a menu heading and line, and an
English subtitle track. The media it names (`media/day1.mp4`,
`media/day1.en.srt`) are not in the repository: put a video and a SubRip
file there first, for example

```sh
mkdir -p examples/request/media
ffmpeg -f lavfi -i testsrc2=size=320x240:rate=30000/1001:duration=9 -f lavfi -i sine=duration=9 \
  -shortest examples/request/media/day1.mp4
printf '1\n00:00:00,500 --> 00:00:02,500\nOpening remarks\n' > examples/request/media/day1.en.srt
```

(`tests/test_request.py` makes the same files in a temporary folder).

```sh
oncemore request examples/request/request.json --json      # what it builds, and its token
oncemore iso --request examples/request/request.json --confirm <token> -o day1.iso --json
```
