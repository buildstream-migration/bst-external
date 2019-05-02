kind: autotools

depends:
- filename: base.bst
  type: build

variables:
  prefix: /app

sources:
- kind: local
  path: files/flatpak/
