#!/usr/bin/env bash
set -euo pipefail

use_extracted_rust_toolchain() {
  local root="${SIFTQ_RUST_APT_ROOT:-/tmp/siftq-rust-apt/extract}"
  local cargo_bin

  for cargo_bin in "$root"/usr/lib/rust-*/bin/cargo; do
    if [ ! -x "$cargo_bin" ]; then
      continue
    fi

    local rust_bin
    local rust_home
    rust_bin="$(dirname "$cargo_bin")"
    rust_home="$(dirname "$rust_bin")"

    export PATH="$rust_bin:$root/usr/bin:$PATH"
    export LD_LIBRARY_PATH="$root/usr/lib/x86_64-linux-gnu:$rust_home/lib:${LD_LIBRARY_PATH:-}"
    export RUSTC="$rust_bin/rustc"
    return 0
  done

  return 1
}

if ! command -v cargo >/dev/null 2>&1 || ! cargo --version >/dev/null 2>&1; then
  if ! use_extracted_rust_toolchain; then
    printf 'cargo is required for task ci:rust, but no usable Cargo toolchain was found.\n' >&2
    exit 127
  fi
fi

cargo fmt --all --check
cargo clippy --locked --workspace --all-targets -- -D warnings
cargo test --locked --workspace
