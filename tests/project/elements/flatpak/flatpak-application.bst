kind: flatpak_image

variables:
  prefix: /app

config:
  directory: "%{prefix}"

  metadata:
    Application:
      name: build.bstexternal.Hello
      runtime: build.bstexternal.Test/x86_64/master
      sdk: build.bstexternal.Test/x86_64/master
      command: hello

depends:
- filename: flatpak/hello.bst
  type: build
