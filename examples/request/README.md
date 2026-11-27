# A build request

`request.json` is a build request (`oncemore/build-request@1`, DECISIONS §142)
as an editing agent writes it from its plan: the day's recording as one
title, its three sessions as named chapters, a menu heading and line, and an
English subtitle track. The media it names (`media/day1.mp4`,
`media/day1.en.srt`) are not in the repository; `tests/test_request.py`
makes them.

```sh
oncemore request examples/request/request.json --json      # what it builds, and its token
oncemore iso --request examples/request/request.json --confirm <token> -o day1.iso --json
```
