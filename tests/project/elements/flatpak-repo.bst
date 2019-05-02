kind: flatpak_repo

depends:
- filename: deploy-tools/flatpak.bst
  junction: base/freedesktop-junction.bst
  type: build
- filename: flatpak/flatpak-runtime.bst
  type: build
- filename: flatpak/flatpak-application.bst
  type: build

config:
  branch: master
  arch: x86_64
  environment:
  - deploy-tools/flatpak.bst
