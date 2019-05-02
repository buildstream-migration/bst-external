kind: flatpak_image

config:
  directory: '%{prefix}'
  exclude:
  - debug

  metadata:
    Runtime:
      name: build.bstexternal.Test
      runtime: build.bstexternal.Test/x86_64/master
      sdk: build.bstexternal.Test/x86_64/master

depends:
- filename: flatpak/flatpak-runtime-image.bst
  type: build
