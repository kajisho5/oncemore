# examples/basic

The same project that `oncemore init` creates. The media files are not
committed; generate them (and an identical project file) with:

```sh
oncemore init examples/basic --force
oncemore iso examples/basic -o basic.iso
```

`oncemore validate --no-media examples/basic` checks the JSON alone.
