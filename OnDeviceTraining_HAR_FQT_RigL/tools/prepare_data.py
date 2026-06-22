#!/usr/bin/env python3
"""prepare_data.py — UCI-HAR → C array + UART training streamer

Usage
-----
# 1. Generate embedded test set (writes into src/dataset.c):
python3 tools/prepare_data.py --ucihar-dir "/path/to/UCI HAR Dataset" \
                               --n-per-class 10 --mode embed

# 2. Stream training data to Pico over serial while it trains:
python3 tools/prepare_data.py --ucihar-dir "/path/to/UCI HAR Dataset" \
                               --port COM3 --epochs 100 --mode stream

Requirements: numpy, pyserial
    pip install numpy pyserial
"""

import argparse
import os
import struct
import sys
import time
import numpy as np

# ── UCI-HAR loader ────────────────────────────────────────────────────

def load_ucihar(ucihar_dir: str):
    """Return (X_train, y_train, X_test, y_test).

    X shape: (N, 128, 9)   normalised float32
    y shape: (N,)          int, 0-based
    """
    def _load_split(split: str):
        split_dir = os.path.join(ucihar_dir, split)
        inertial_dir = os.path.join(split_dir, "Inertial Signals")

        channel_files = [
            "body_acc_x", "body_acc_y", "body_acc_z",
            "body_gyro_x", "body_gyro_y", "body_gyro_z",
            "total_acc_x", "total_acc_y", "total_acc_z",
        ]
        channels = []
        for ch in channel_files:
            path = os.path.join(inertial_dir, f"{ch}_{split}.txt")
            data = np.loadtxt(path, dtype=np.float32)   # (N, 128)
            channels.append(data)

        X = np.stack(channels, axis=-1)   # (N, 128, 9)

        y_path = os.path.join(split_dir, f"y_{split}.txt")
        y = np.loadtxt(y_path, dtype=np.int32) - 1   # 1-based → 0-based
        return X, y

    print("Loading UCI-HAR training split...")
    X_train, y_train = _load_split("train")
    print(f"  Loaded {len(X_train)} training samples.")

    print("Loading UCI-HAR test split...")
    X_test, y_test = _load_split("test")
    print(f"  Loaded {len(X_test)} test samples.")

    return X_train, y_train, X_test, y_test


def normalize_dataset(X: np.ndarray) -> np.ndarray:
    """Z-score normalise per channel using training-set statistics."""
    # Stats pre-computed from UCI-HAR training split
    MEAN = np.array([0.0, 0.0, 0.0,
                     0.0, 0.0, 0.0,
                     0.0136, 0.0064, 0.0125], dtype=np.float32)
    STD  = np.array([0.1140, 0.0783, 0.1024,
                     0.1600, 0.1050, 0.0862,
                     0.5715, 0.5733, 0.4012], dtype=np.float32)
    X = (X - MEAN) / (STD + 1e-8)
    return np.clip(X, -3.0, 3.0)


# ── Embed mode: write test set into src/dataset.c ─────────────────────

DATASET_C_HEADER = "/* ── BEGIN auto-generated test data (replace with prepare_data.py output) ── */"
DATASET_C_FOOTER = "/* ── END auto-generated test data ────────────────────────────────────────── */"

def write_embedded(X_test: np.ndarray, y_test: np.ndarray,
                   n_per_class: int, dataset_c_path: str):
    """Select n_per_class samples per class and embed into dataset.c."""
    num_classes = 6
    selected_X, selected_y = [], []

    for cls in range(num_classes):
        idx = np.where(y_test == cls)[0]
        np.random.shuffle(idx)
        chosen = idx[:n_per_class]
        selected_X.append(X_test[chosen])
        selected_y.append(y_test[chosen])

    X_embed = np.concatenate(selected_X, axis=0).reshape(-1, 128 * 9)   # (N, 1152)
    y_embed = np.concatenate(selected_y, axis=0).astype(np.uint8)
    N = len(y_embed)

    # Build C snippet
    lines = [
        f"const int DATASET_TEST_N = {N};",
        f"const float DATASET_TEST_X[{N}][{128 * 9}] = {{",
    ]
    for i, row in enumerate(X_embed):
        vals = ", ".join(f"{v:.6f}f" for v in row)
        comma = "," if i < N - 1 else ""
        lines.append(f"    {{ {vals} }}{comma}")
    lines.append("};")
    lines.append(f"const uint8_t DATASET_TEST_Y[{N}] = {{")
    lines.append("    " + ", ".join(str(int(v)) for v in y_embed))
    lines.append("};")

    new_block = "\n".join(lines)

    # Read existing dataset.c and replace the auto-gen block
    with open(dataset_c_path, "r") as f:
        content = f.read()

    start = content.find(DATASET_C_HEADER)
    end   = content.find(DATASET_C_FOOTER)
    if start == -1 or end == -1:
        print(f"ERROR: Could not find markers in {dataset_c_path}")
        sys.exit(1)

    end += len(DATASET_C_FOOTER)
    new_content = (content[:start]
                   + DATASET_C_HEADER + "\n"
                   + new_block + "\n"
                   + DATASET_C_FOOTER
                   + content[end:])

    with open(dataset_c_path, "w") as f:
        f.write(new_content)

    print(f"Written {N} test samples ({n_per_class} per class) to {dataset_c_path}")


# ── Stream mode: send training data to Pico via serial ───────────────

def stream_training(X_train: np.ndarray, y_train: np.ndarray,
                    port: str, baud: int, epochs: int):
    """Stream training samples to Pico and display live feedback."""
    try:
        import serial
    except ImportError:
        print("ERROR: pyserial not installed. Run: pip install pyserial")
        sys.exit(1)

    ser = serial.Serial(port, baud, timeout=2.0)
    time.sleep(0.5)
    print(f"Connected to {port} at {baud} baud.")
    print("Waiting for Pico to boot...")
    # Flush boot messages
    time.sleep(3.0)
    ser.reset_input_buffer()

    N = len(y_train)
    idx = np.arange(N)

    for epoch in range(epochs):
        np.random.shuffle(idx)
        print(f"\n── Epoch {epoch + 1}/{epochs} ──")

        for step, i in enumerate(idx):
            sample = X_train[i].astype(np.float32).flatten()
            label  = int(y_train[i])

            # Send label + sample
            payload = struct.pack("B", label) + sample.tobytes()
            ser.write(payload)

            # Read feedback: [uint8 step_echo] [float loss] [float acc]
            resp = ser.read(9)
            if len(resp) == 9:
                _, loss, acc = struct.unpack("<Bff", resp)
                if step % 100 == 0:
                    print(f"  step={step:5d}  loss={loss:.4f}  acc={acc*100:.1f}%")
            else:
                print(f"  [step {step}] No response from Pico (timeout)")

        print(f"  Epoch {epoch + 1} complete.")

    ser.close()
    print("\nStreaming done.")


# ── CLI ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="UCI-HAR data tool for Pico HAR trainer")
    parser.add_argument("--ucihar-dir", required=True,
                        help="Path to 'UCI HAR Dataset' root directory")
    parser.add_argument("--mode", choices=["embed", "stream"], default="embed",
                        help="embed: write C arrays | stream: send to Pico")
    parser.add_argument("--n-per-class", type=int, default=10,
                        help="Test samples per class for embed mode")
    parser.add_argument("--port", default="COM3",
                        help="Serial port for stream mode (e.g. COM3 or /dev/ttyACM0)")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--epochs", type=int, default=100,
                        help="Training epochs for stream mode")
    parser.add_argument("--dataset-c",
                        default=os.path.join(os.path.dirname(__file__),
                                             "..", "src", "dataset.c"),
                        help="Path to src/dataset.c (for embed mode)")
    args = parser.parse_args()

    X_train, y_train, X_test, y_test = load_ucihar(args.ucihar_dir)
    X_train = normalize_dataset(X_train)
    X_test  = normalize_dataset(X_test)

    if args.mode == "embed":
        write_embedded(X_test, y_test, args.n_per_class,
                       os.path.abspath(args.dataset_c))
    else:
        stream_training(X_train, y_train,
                        args.port, args.baud, args.epochs)


if __name__ == "__main__":
    main()
