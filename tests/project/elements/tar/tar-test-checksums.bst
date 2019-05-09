kind: tar_element

depends:
- filename: hello-import.bst
  type: build

config:
  filename: hello
  include-checksums:
  - sha256
  - md5
